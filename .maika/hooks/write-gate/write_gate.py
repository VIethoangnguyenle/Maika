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
import os
import re
import shlex
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import yaml


_PATCH_FILE_RE = re.compile(r"^\*\*\* (?:Add|Update|Delete) File: (.+)$", re.MULTILINE)
_DYNAMIC = re.compile(r"[\$`*?]")
_REDIRECT_RE = re.compile(r"(?<!>)>>?\|?\s*([^\s|&;<>()]+)")
_SEGMENT_RE = re.compile(r"[\n;]|\|\||&&|(?<!>)\|")
_DEVNULL = {"/dev/null", "/dev/stdout", "/dev/stderr"}
_DOC_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}
_SHELL_TOOLS = {"bash", "shell", "local_shell", "run_command", "run_terminal_cmd"}
_SESSION_PHASES = ("phase-1-done", "phase-2-done")
_PHASE_STATE_RE = re.compile(r"phase_state:\s*([A-Za-z0-9-]+)")
_SHELL_COMMS = {"sh", "bash", "dash", "zsh", "fish", "python", "python3", "py"}
_SESSION_GATE_MESSAGE = (
    "[SESSION-GATE] Pha 1/2 đã chạy trong session này — context có nguy cơ đã tràn/compact. "
    "Dispatch node qua worker (procedures/executor.md + TASK_HANDOFF, xem "
    "profiles/execution-mode.yaml) hoặc mở session mới rồi chạy /task apply <ticket>. "
    "User có thể override tường minh: ghi knowledge/active/SESSION_OVERRIDE.md theo template "
    "(sẽ được log vào Violation Log)."
)


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


def _execution_config_path(framework_path: Path) -> Path:
    profiles = framework_path / "profiles"
    local = profiles / "execution-mode.local.yaml"
    if local.exists():
        return local
    return profiles / "execution-mode.yaml"


def _path_from_value(value):
    if isinstance(value, str) and value.strip():
        return Path(value.strip())
    return None


def _project_root_from_cwd(cwd: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            check=True,
        )
    except (FileNotFoundError, OSError, subprocess.CalledProcessError):
        return cwd
    root = result.stdout.strip()
    return Path(root) if root else cwd


def _runtime_target(cwd: Path, target_path: Path) -> Path:
    return target_path if target_path.is_absolute() else (cwd / target_path).resolve()


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


def _proc_stat(proc_root: Path, pid: int):
    """Parse /proc/<pid>/stat → (comm, ppid, starttime). None nếu không đọc được."""
    try:
        stat = (proc_root / str(pid) / "stat").read_text(encoding="utf-8")
        comm = stat.split("(", 1)[1].rsplit(")", 1)[0]
        rest = stat.rsplit(")", 1)[1].split()
        return comm, int(rest[1]), rest[19]
    except (OSError, IndexError, ValueError):
        return None


def _process_identity(proc_root: Path = Path("/proc")):
    """Tổ tiên đầu tiên không phải shell/python = process của agent runtime.

    Ổn định qua compaction (cùng process), đổi khi restart session (process mới).
    Trả về "pid:<pid>:<starttime>" hoặc None (vd Windows không có /proc → degrade)."""
    pid = os.getppid()
    for _ in range(16):
        info = _proc_stat(proc_root, pid)
        if info is None:
            return None
        comm, ppid, starttime = info
        if comm.lower() not in _SHELL_COMMS:
            return f"pid:{pid}:{starttime}"
        if ppid <= 1:
            return None
        pid = ppid
    return None


def _session_identity(payload: dict, proc_root: Path = Path("/proc")):
    """Định danh session hiện tại: ưu tiên id từ hook payload; fallback POSIX
    process-identity; không có → None (SESSION-GATE degrade về cho-qua)."""
    sid = (
        payload.get("session_id")
        or payload.get("sessionId")
        or payload.get("conversation_id")
        or payload.get("conversationId")
    )
    if sid:
        return f"sid:{sid}"
    return _process_identity(proc_root=proc_root)


def _session_state_path(project_root: Path, framework_root: str) -> Path:
    return project_root / framework_root / "knowledge" / "active" / ".session_state.json"


def record_session_state(project_root: Path, framework_root: str, session_identity) -> None:
    """Ghi session identity tại LẦN ĐẦU quan sát phase_state ∈ _SESSION_PHASES.

    Sidecar nằm trong knowledge/active/ nên được knowledge-curator reset cùng task —
    state cũ không bao giờ chặn nhầm task sau."""
    if not session_identity:
        return
    transparency = project_root / framework_root / "knowledge" / "active" / "AGENT_TRANSPARENCY.md"
    if not transparency.exists():
        return
    try:
        match = _PHASE_STATE_RE.search(transparency.read_text(encoding="utf-8"))
    except OSError:
        return
    if not match:
        return
    phase = match.group(1).lower()
    if phase not in _SESSION_PHASES:
        return
    state_path = _session_state_path(project_root, framework_root)
    state = {}
    if state_path.exists():
        try:
            state = json.loads(state_path.read_text(encoding="utf-8")) or {}
        except (OSError, json.JSONDecodeError):
            state = {}
    phases = state.setdefault("phases", {})
    if phase in phases:
        return
    phases[phase] = {
        "session_identity": session_identity,
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    try:
        state_path.parent.mkdir(parents=True, exist_ok=True)
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError:
        pass


def _log_session_violation(project_root: Path, framework_root: str, session_identity: str) -> None:
    transparency = project_root / framework_root / "knowledge" / "active" / "AGENT_TRANSPARENCY.md"
    marker = f"[VIOLATION][SESSION-GATE] override dùng cho session {session_identity}"
    try:
        text = transparency.read_text(encoding="utf-8") if transparency.exists() else ""
        if marker in text:
            return
        stamp = datetime.now(timezone.utc).isoformat()
        with transparency.open("a", encoding="utf-8") as f:
            f.write(f"\n{marker} lúc {stamp}\n")
    except OSError:
        pass


def check_session_gate(project_root: Path, framework_root: str, session_identity) -> Decision:
    """Lưới an toàn context-overflow: chặn code write inline trong session đã
    hoàn thành Pha 1/2. Không có identity/state → cho qua (degrade, không tệ hơn hiện trạng)."""
    if not session_identity:
        return Decision(True)
    state_path = _session_state_path(project_root, framework_root)
    if not state_path.exists():
        return Decision(True)
    try:
        state = json.loads(state_path.read_text(encoding="utf-8")) or {}
    except (OSError, json.JSONDecodeError):
        return Decision(True)
    phases = state.get("phases", {})
    same_session = any(
        phases.get(phase, {}).get("session_identity") == session_identity
        for phase in _SESSION_PHASES
    )
    if not same_session:
        return Decision(True)
    override = project_root / framework_root / "knowledge" / "active" / "SESSION_OVERRIDE.md"
    if override.exists():
        try:
            body = override.read_text(encoding="utf-8")
        except OSError:
            body = ""
        if re.search(r"^ticket:\s*\S+", body, re.MULTILINE) and re.search(
            r"^user-confirm:\s*\S+", body, re.MULTILINE
        ):
            _log_session_violation(project_root, framework_root, session_identity)
            _warn("write-gate: [SESSION-GATE] override active — violation đã log vào AGENT_TRANSPARENCY.")
            return Decision(True)
        return Decision(False, "SESSION_OVERRIDE.md thiếu ticket:/user-confirm: — " + _SESSION_GATE_MESSAGE)
    return Decision(False, _SESSION_GATE_MESSAGE)


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
    queue = active / "microloop" / "TASK_QUEUE.md"
    if queue.exists():
        data = yaml.safe_load(queue.read_text(encoding="utf-8")) or {}
        for task in data.get("tasks") or []:
            if task.get("status") != "in_progress":
                continue
            handoff = task.get("handoff_path")
            if handoff:
                path = Path(handoff)
                if not path.is_absolute():
                    path = project_root / path
            elif task.get("id"):
                path = active / f"TASK_HANDOFF.{task['id']}.md"
            else:
                continue
            if path.exists():
                candidates.append(path)
        return candidates
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


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _vnext_active_task(project_root: Path, framework_root: str):
    framework_path = project_root / framework_root
    config_path = _execution_config_path(framework_path)
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return None
    if (config or {}).get("workflow_engine", "legacy") != "vnext":
        return None

    executing = []
    for state_path in sorted((framework_path / "changes").glob("*/STATE.yaml")):
        try:
            state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if state.get("state") == "EXECUTING":
            executing.append(state_path.parent)
    if not executing:
        return None
    if len(executing) != 1:
        return ("deny", "có nhiều change EXECUTING")

    ws = executing[0]
    gen = ws / "generated"
    try:
        validation = _read_json(gen / "PLAN_VALIDATION.json")
    except (OSError, json.JSONDecodeError):
        return ("deny", "không đọc được generated/PLAN_VALIDATION.json")
    if validation.get("verdict") != "APPROVED":
        return ("deny", "generated/PLAN_VALIDATION.json verdict != APPROVED")

    try:
        manifest = _read_json(gen / "PLAN_MANIFEST.json")
        queue = _read_json(gen / "TASK_QUEUE.json")
    except (OSError, json.JSONDecodeError):
        return ("deny", "không đọc được generated/PLAN_MANIFEST.json hoặc TASK_QUEUE.json")
    if queue.get("plan_sha256") != manifest.get("plan_sha256"):
        return ("deny", "TASK_QUEUE.json.plan_sha256 != PLAN_MANIFEST.json.plan_sha256")

    in_progress = [task for task in queue.get("tasks") or [] if task.get("status") == "in_progress"]
    if len(in_progress) != 1:
        return ("deny", "không có đúng một task in_progress")
    return (ws, in_progress[0])


def evaluate_write(project_root: Path, target_path: Path, framework_root: str = ".maika",
                   session_identity=None) -> Decision:
    if not target_path.as_posix():
        return Decision(False, "Unable to identify target path for write-gate payload")
    policy_path = _policy_path(project_root, target_path)
    if _is_framework_artifact(policy_path, framework_root):
        return Decision(True)
    if _is_documentation(policy_path):
        return Decision(True)

    session_result = check_session_gate(project_root, framework_root, session_identity)
    if not session_result.ok:
        return session_result

    # vNext mode THAY THẾ legacy phase-gating có chủ đích (v2 §21): khi một change
    # EXECUTING dưới workflow_engine=vnext, KNOWLEDGE_CHECKPOINT/apply-gate legacy
    # không áp dụng (vnext có gate riêng: plan approval + brief-scope + result contract).
    vnext = _vnext_active_task(project_root, framework_root)
    if vnext is not None:
        if vnext[0] == "deny":
            return Decision(False, f"vNext EXECUTING nhưng trạng thái hỏng: {vnext[1]}")
        ws, task = vnext
        allowed = set()
        for key in ("create", "modify", "test"):
            allowed.update((task.get("files") or {}).get(key, []) or [])
        rel = policy_path.relative_to(project_root).as_posix() if policy_path.is_absolute() else policy_path.as_posix()
        if rel in allowed or rel.startswith(str(ws.relative_to(project_root))):
            return Decision(True)
        return Decision(False, f"vNext brief-scope: {rel} ngoài files khai báo của {task['id']}")

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
    cwd = Path.cwd()
    root = _project_root_from_cwd(cwd)
    session_identity = _session_identity(payload)
    record_session_state(root, args.framework_root, session_identity)

    if _is_shell_tool(_tool_name(payload)):
        targets, unresolved = parse_shell_writes(_command_text(payload))
        targets = [_runtime_target(cwd, t) for t in targets]
        targets = [t for t in targets if not _git_ignored(root, _policy_path(root, t))]
        if not targets:
            if unresolved:
                _warn("write-gate: shell write with unresolved path — allowed (heuristic).")
            decision = Decision(True)
        else:
            decisions = [
                evaluate_write(root, target, framework_root=args.framework_root,
                               session_identity=session_identity)
                for target in targets
            ]
            decision = next((item for item in decisions if not item.ok), Decision(True))
    else:
        targets = extract_target_paths(payload)
        if not targets:
            decision = Decision(False, "Unable to identify target path for write-gate payload")
        else:
            targets = [_runtime_target(cwd, t) for t in targets]
            decisions = [
                evaluate_write(root, target, framework_root=args.framework_root,
                               session_identity=session_identity)
                for target in targets
            ]
            decision = next((item for item in decisions if not item.ok), Decision(True))

    return _print_runtime_decision(args.runtime, decision)


if __name__ == "__main__":
    sys.exit(main())
