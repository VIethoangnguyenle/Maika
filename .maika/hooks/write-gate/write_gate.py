"""Runtime write gate for Maika decision-point evidence.

Command-hook contract:
- stdin: JSON payload from the agent runtime hook.
- Claude Code: exit 0 allows; exit 2 blocks with stderr reason.
- Codex: stdout JSON with hookSpecificOutput.permissionDecision allow|deny.
- Antigravity: stdout JSON with decision allow|deny.
"""
import argparse
import fnmatch
import importlib.util
import json
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

import yaml


_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
_DYNAMIC = re.compile(r"[\$`*?]")
_REDIRECT_RE = re.compile(r"(?<!>)>>?\|?\s*([^\s|&;<>()]+)")
_SEGMENT_RE = re.compile(r"[\n;]|\|\||&&|(?<!>)\|")
_DEVNULL = {"/dev/null", "/dev/stdout", "/dev/stderr"}
_DOC_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}
_SHELL_TOOLS = {"bash", "shell", "local_shell", "run_command", "run_terminal_cmd"}


@dataclass
class Decision:
    ok: bool
    reason: str = ""


def _load_gate_check(project_root: Path, framework_root: str):
    candidates = [
        project_root / framework_root / "tools" / "gate-check" / "gates.py",
        Path(__file__).resolve().parents[2] / "tools" / "gate-check" / "gates.py",
    ]
    for mod in candidates:
        if mod.exists():
            spec = importlib.util.spec_from_file_location("gates", mod)
            gates = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gates)
            return gates
    raise FileNotFoundError(f"Cannot locate gate-check/gates.py under {framework_root}")


def _path_from_value(value):
    if isinstance(value, str) and value.strip():
        return Path(value.strip())
    return None


def _policy_path(project_root: Path, target_path: Path) -> Path:
    if not target_path.is_absolute():
        return target_path
    try:
        return target_path.resolve().relative_to(project_root.resolve())
    except (OSError, ValueError):
        return target_path


def _paths_from_patch_command(command: str):
    return [Path(match.strip()) for match in _PATCH_FILE_RE.findall(command or "")]


def _is_dynamic(token: str) -> bool:
    return bool(_DYNAMIC.search(token)) or "$(" in token


def _t3_targets(verb: str, args: list) -> list:
    """Return write targets for a known write command, or [None] if the verb
    writes but no concrete target is parseable."""
    nonflag = [a for a in args if not a.startswith("-")]
    if verb == "tee":
        return nonflag or [None]
    if verb == "sed":
        if any(a == "-i" or a.startswith("-i") for a in args):
            return nonflag[1:] if len(nonflag) > 1 else [None]
        return []
    if verb in ("cp", "mv", "install"):
        return [nonflag[-1]] if nonflag else [None]
    if verb == "dd":
        return [a[3:] for a in args if a.startswith("of=")]
    if verb == "git":
        if args[:1] == ["apply"]:
            return [None]
        if args[:1] == ["checkout"] and "--" in args:
            return args[args.index("--") + 1:] or [None]
        if args[:1] == ["restore"]:
            return [a for a in args[1:] if not a.startswith("-")] or [None]
        return []
    if verb == "prettier":
        return (nonflag or [None]) if "--write" in args else []
    if verb == "gofmt":
        return (nonflag or [None]) if "-w" in args else []
    if verb == "black":
        return nonflag or [None]
    if verb == "ruff":
        if "--fix" in args or "format" in args:
            return [a for a in nonflag if a not in ("format", "check")] or [None]
        return []
    return []


def parse_shell_writes(command: str):
    """Heuristically extract concrete write targets from a shell command.

    Returns (paths, unresolved):
    - paths: list[Path] of concrete write targets (deduped, order-preserving).
    - unresolved: True if a recognized write verb had a dynamic/unparseable path.
    """
    command = command or ""
    raw_paths = []
    unresolved = False

    raw_paths.extend(_paths_from_patch_command(command))

    for seg in _SEGMENT_RE.split(command):
        seg = seg.strip()
        if not seg:
            continue
        for match in _REDIRECT_RE.finditer(seg):
            target = match.group(1)
            if target in _DEVNULL:
                continue
            if _is_dynamic(target):
                unresolved = True
            else:
                raw_paths.append(Path(target))
        try:
            tokens = shlex.split(seg)
        except ValueError:
            tokens = seg.split()
        if not tokens:
            continue
        verb = Path(tokens[0]).name
        for target in _t3_targets(verb, tokens[1:]):
            if target is None or _is_dynamic(target):
                unresolved = True
            else:
                raw_paths.append(Path(target))

    seen, paths = set(), []
    for p in raw_paths:
        key = p.as_posix()
        if key not in seen:
            seen.add(key)
            paths.append(p)
    return paths, unresolved


def _git_ignored(project_root: Path, path: Path) -> bool:
    """True if `path` is git-ignored under project_root. Not-a-git-repo, missing
    git, or any error degrades to False (treat as a gated, non-ignored path)."""
    try:
        result = subprocess.run(
            ["git", "check-ignore", "-q", path.as_posix()],
            cwd=str(project_root),
            capture_output=True,
        )
    except (FileNotFoundError, OSError):
        return False
    return result.returncode == 0


def _tool_name(payload: dict) -> str:
    return payload.get("tool_name") or (payload.get("toolCall") or {}).get("name") or ""


def _is_shell_tool(name: str) -> bool:
    return name.lower() in _SHELL_TOOLS


def _command_text(payload: dict) -> str:
    tool_input = payload.get("tool_input") or {}
    tool_args = (payload.get("toolCall") or {}).get("args") or {}
    return tool_input.get("command") or tool_args.get("CommandLine") or tool_args.get("command") or ""


def _warn(message: str) -> None:
    print(message, file=sys.stderr)


def extract_target_paths(payload: dict):
    tool_input = payload.get("tool_input") or {}
    tool_call = payload.get("toolCall") or {}
    tool_args = tool_call.get("args") or {}

    direct = (
        _path_from_value(tool_input.get("file_path"))
        or _path_from_value(tool_input.get("path"))
        or _path_from_value(tool_input.get("TargetFile"))
        or _path_from_value(tool_args.get("file_path"))
        or _path_from_value(tool_args.get("path"))
        or _path_from_value(tool_args.get("FilePath"))
        or _path_from_value(tool_args.get("TargetFile"))
    )
    if direct:
        return [direct]

    command = tool_input.get("command") or tool_args.get("CommandLine") or ""
    return _paths_from_patch_command(command)


def _is_framework_artifact(path: Path, framework_root: str) -> bool:
    parts = path.as_posix()
    return (
        parts.startswith(f"{framework_root}/")
        or parts.startswith("openspec/")
        or parts.startswith("docs/superpowers/specs/")
        or parts.startswith("docs/superpowers/plans/")
    )


def _is_documentation(path: Path) -> bool:
    """Documentation/understanding artifacts are not application code, so they
    are exempt from the knowledge-before-code gate (a .md file can never be a
    runnable code write that the gate exists to order)."""
    return path.suffix.lower() in _DOC_SUFFIXES


def _load_all_rule_ids(index_path: Path):
    if not index_path.exists():
        return None, True
    data = yaml.safe_load(index_path.read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    return {entry["id"] for entry in entries if entry.get("id")}, len(entries) == 0


_SECTION_RE = r"##\s+{name}[ \t]*\n(.*?)(?=\n##\s|\Z)"


def _section_text(text: str, name: str) -> str:
    pattern = re.compile(_SECTION_RE.format(name=re.escape(name)), re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def _allowed_file_patterns(context_text: str) -> list[str]:
    allowed = _section_text(context_text, "Allowed Files")
    patterns = []
    for line in allowed.splitlines():
        item = line.strip()
        if not item:
            continue
        if item.startswith("-"):
            item = item[1:].strip()
        item = item.strip("`'\"")
        if item:
            patterns.append(item)
    return patterns


def _context_allows_target(context_text: str, policy_path: Path) -> bool:
    target = policy_path.as_posix()
    for pattern in _allowed_file_patterns(context_text):
        normalized = Path(pattern).as_posix()
        if normalized == target or fnmatch.fnmatch(target, normalized):
            return True
    return False


def _implementation_context_candidates(project_root: Path, framework_root: str):
    active = project_root / framework_root / "knowledge" / "active"
    candidates = []
    direct = active / "IMPLEMENTATION_CONTEXT.md"
    if direct.exists():
        candidates.append(direct)
    candidates.extend(sorted(active.glob("TASK_HANDOFF.*.md")))
    return candidates


def _validate_implementation_context(project_root: Path, policy_path: Path, framework_root: str, gates) -> Decision:
    candidates = _implementation_context_candidates(project_root, framework_root)
    if not candidates:
        return Decision(False, f"Missing valid implementation context before code write: {policy_path}")
    invalid_reasons = []
    target_mismatches = []
    for candidate in candidates:
        rel = candidate.relative_to(project_root)
        text = candidate.read_text(encoding="utf-8")
        result = gates.validate_implementation_context(text)
        if not result.ok:
            invalid_reasons.append(f"{rel}: {result.reason}")
            continue
        if _context_allows_target(text, policy_path):
            return Decision(True)
        target_mismatches.append(rel.as_posix())
    if target_mismatches:
        return Decision(
            False,
            "Implementation context does not allow code write target "
            f"{policy_path}; checked: {', '.join(target_mismatches)}",
        )
    return Decision(False, "Invalid implementation context before code write: " + "; ".join(invalid_reasons))


def evaluate_write(project_root: Path, target_path: Path, framework_root: str = ".maika") -> Decision:
    if not target_path.as_posix():
        return Decision(False, "Unable to identify target path for write-gate payload")
    policy_path = _policy_path(project_root, target_path)
    if _is_framework_artifact(policy_path, framework_root):
        return Decision(True)
    if _is_documentation(policy_path):
        return Decision(True)

    checkpoint = project_root / framework_root / "knowledge" / "active" / "KNOWLEDGE_CHECKPOINT.md"
    if not checkpoint.exists():
        return Decision(False, f"Missing {checkpoint.relative_to(project_root)} before code write: {target_path}")

    gates = _load_gate_check(project_root, framework_root)
    index_path = project_root / framework_root / "knowledge" / "long-term" / "knowledge-index.yaml"
    valid_rule_ids, index_empty = _load_all_rule_ids(index_path)
    result = gates.validate_knowledge_checkpoint(
        checkpoint.read_text(encoding="utf-8"),
        valid_rule_ids=valid_rule_ids,
        allow_no_knowledge=index_empty,
    )
    if not result.ok:
        return Decision(False, f"Invalid KNOWLEDGE_CHECKPOINT before code write: {result.reason}")

    transparency = project_root / framework_root / "knowledge" / "active" / "AGENT_TRANSPARENCY.md"
    if not transparency.exists():
        return Decision(False, f"Missing {transparency.relative_to(project_root)} apply evidence before code write: {target_path}")
    apply_result = gates.validate_apply_gate(transparency.read_text(encoding="utf-8"))
    if not apply_result.ok:
        return Decision(False, f"{apply_result.reason} before code write: {target_path}")
    context_result = _validate_implementation_context(project_root, policy_path, framework_root, gates)
    if not context_result.ok:
        return context_result
    return Decision(True)


def _print_runtime_decision(runtime: str, decision: Decision) -> int:
    if decision.ok:
        if runtime == "codex":
            print(json.dumps({
                "hookSpecificOutput": {
                    "hookEventName": "PreToolUse",
                    "permissionDecision": "allow",
                }
            }))
        elif runtime == "antigravity":
            print(json.dumps({"decision": "allow"}))
        return 0

    if runtime == "codex":
        print(json.dumps({
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": decision.reason,
            }
        }))
        return 0
    if runtime == "antigravity":
        print(json.dumps({"decision": "deny", "reason": decision.reason}))
        return 0
    print(decision.reason, file=sys.stderr)
    return 2


def main(argv=None, stdin_text=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--framework-root", default=".maika")
    parser.add_argument("--runtime", choices=["claude", "codex", "antigravity"], default="claude")
    args = parser.parse_args(argv)
    raw = stdin_text if stdin_text is not None else sys.stdin.read()
    payload = json.loads(raw or "{}")
    root = Path.cwd()

    if _is_shell_tool(_tool_name(payload)):
        targets, unresolved = parse_shell_writes(_command_text(payload))
        targets = [t for t in targets if not _git_ignored(root, t)]
        if not targets:
            if unresolved:
                _warn("write-gate: shell write with unresolved path — allowed (heuristic).")
            decision = Decision(True)
        else:
            decisions = [
                evaluate_write(root, target, framework_root=args.framework_root)
                for target in targets
            ]
            decision = next((item for item in decisions if not item.ok), Decision(True))
    else:
        targets = extract_target_paths(payload)
        if not targets:
            decision = Decision(False, "Unable to identify target path for write-gate payload")
        else:
            decisions = [
                evaluate_write(root, target, framework_root=args.framework_root)
                for target in targets
            ]
            decision = next((item for item in decisions if not item.ok), Decision(True))

    return _print_runtime_decision(args.runtime, decision)


if __name__ == "__main__":
    sys.exit(main())
