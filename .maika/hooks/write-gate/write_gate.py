"""Runtime write gate for Maika decision-point evidence.

Command-hook contract:
- stdin: JSON payload from the agent runtime hook.
- Claude Code: exit 0 allows; exit 2 blocks with stderr reason.
- Codex: stdout JSON with hookSpecificOutput.permissionDecision allow|deny.
- Antigravity: stdout JSON with decision allow|deny.
"""
import argparse
import fnmatch
import hashlib
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
_READ_ONLY_VERBS = {
    "awk", "basename", "cat", "cmp", "cut", "diff", "dirname", "du", "echo", "env",
    "find", "git", "grep", "head", "jq", "ls", "pwd", "readlink", "rg",
    "printf", "sha256sum", "sort", "stat", "tail", "test", "tr", "tree", "uniq",
    "wc", "which", "yq",
}
_INTERPRETER_VERBS = {
    "python", "python2", "python3", "py", "node", "nodejs", "ruby", "perl",
    "php", "deno", "sh", "bash", "dash", "zsh", "fish",
}
_MUTATING_TASK_MARKERS = {
    "spotless:apply", "spotlessapply", "format", "format:write", "lint:fix",
    "--fix", "fix", "apply",
}
_SESSION_GATE_MESSAGE = (
    "[SESSION-GATE] Pha 1/2 đã chạy trong session này — context có nguy cơ đã tràn/compact. "
    "Mở session mới rồi chạy maika task apply --id <ticket>. "
    "User có thể override tường minh: ghi knowledge/active/SESSION_OVERRIDE.md theo template "
    "(sẽ được log vào Violation Log)."
)


@dataclass
class Decision:
    ok: bool
    reason: str = ""


# --- Secret scanner (inlined so this hook stays a single self-contained file
#     the host copies as one unit). High-precision, no PII/entropy. ------------


@dataclass(frozen=True)
class SecretRule:
    id: str
    label: str
    pattern: re.Pattern
    secret_group: int = 0


@dataclass(frozen=True)
class SecretMatch:
    rule_id: str
    label: str
    line: int
    masked_preview: str


_SECRET_RULES = [
    SecretRule("private-key", "PEM private key",
               re.compile(r"-----BEGIN (?:[A-Z0-9]+ )?PRIVATE KEY-----")),
    SecretRule("aws-access-key", "AWS access key id",
               re.compile(r"AKIA[0-9A-Z]{16}")),
    SecretRule("gcp-sa-key", "GCP service-account private key",
               re.compile(r'"private_key"\s*:\s*"-----BEGIN')),
    SecretRule("jwt", "JSON Web Token",
               re.compile(r"eyJ[A-Za-z0-9_-]{6,}\.eyJ[A-Za-z0-9_-]{6,}\.[A-Za-z0-9_-]{6,}")),
    SecretRule("github-token", "GitHub token",
               re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}")),
    SecretRule("slack-token", "Slack token",
               re.compile(r"xox[baprs]-[A-Za-z0-9-]{10,}")),
    SecretRule("stripe-live", "Stripe live secret key",
               re.compile(r"sk_live_[A-Za-z0-9]{16,}")),
    SecretRule("generic-assignment", "Secret-like quoted assignment",
               re.compile(r"(?i)(?:api[_-]?key|secret|token|password)\s*[:=]\s*['\"]([^'\"]{16,})['\"]"),
               secret_group=1),
]


def _mask_secret(value: str) -> str:
    """Reveal only first-4 + last-2; hide the middle. Short values fully hidden."""
    if not value or len(value) <= 6:
        return "****"
    return f"{value[:4]}****{value[-2:]}"


def _secret_scan(content: str, rules=None):
    """Side-effect-free scan. Returns SecretMatch list whose masked_preview
    never contains the raw secret."""
    if not content:
        return []
    rules = _SECRET_RULES if rules is None else rules
    matches = []
    for rule in rules:
        for m in rule.pattern.finditer(content):
            try:
                secret, start = m.group(rule.secret_group), m.start(rule.secret_group)
            except IndexError:
                secret, start = m.group(0), m.start(0)
            if not secret:
                continue
            line = content.count("\n", 0, start) + 1
            matches.append(SecretMatch(rule.id, rule.label, line, _mask_secret(secret)))
    return matches


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
        return [a[3:] for a in args if a.startswith("of=")] or [None]
    if verb in {"touch", "rm", "rmdir", "mkdir", "chmod", "chown", "ln"}:
        return nonflag or [None]
    if verb == "truncate":
        # Size values may be positional after flags; the final non-flag token is
        # the only safe concrete target we can infer.
        return [nonflag[-1]] if nonflag else [None]
    if verb in _INTERPRETER_VERBS:
        # Inline code and scripts are arbitrary filesystem programs.  Version/help
        # probes are the only interpreter invocations proven read-only here.
        if any(a in {"--version", "-V", "--help", "-h"} for a in args):
            return []
        return [None]
    if verb in {"unzip", "7z"}:
        return [None]
    if verb == "tar":
        extracts = any(
            a in {"-x", "--extract", "--get"} or
            (a.startswith("-") and not a.startswith("--") and "x" in a[1:])
            for a in args
        )
        return [None] if extracts else []
    if verb == "git":
        if args[:1] == ["apply"]:
            return [None]
        if args[:1] == ["checkout"] and "--" in args:
            return args[args.index("--") + 1:] or [None]
        if args[:1] == ["restore"]:
            return [a for a in args[1:] if not a.startswith("-")] or [None]
        if args[:1] and args[0] in {"reset", "clean", "revert", "stash", "merge", "rebase"}:
            return [None]
        return [] if args[:1] and args[0] in {
            "status", "diff", "show", "log", "rev-parse", "branch", "ls-files",
            "check-ignore", "remote", "tag",
        } else [None]
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
    if verb in {"mvn", "mvnw", "gradle", "gradlew", "npm", "pnpm", "yarn", "npx"}:
        lowered = {a.lower() for a in args}
        if lowered & _MUTATING_TASK_MARKERS or any(
            marker in a.lower() for marker in _MUTATING_TASK_MARKERS for a in args
        ):
            return [None]
        # Build/test plugins can execute arbitrary project code.  They must use
        # Maika's structured verification executor rather than generic shell when
        # a scoped execution is active.
        return [None]
    if verb in _READ_ONLY_VERBS:
        return []
    # An unknown executable may mutate the workspace; never infer read-only from
    # the absence of a parsed target.
    return [None]


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
        or parts.startswith("docs/superpowers/specs/")
        or parts.startswith("docs/superpowers/plans/")
    )


def _framework_role_allows(rel: str, framework_root: str, ws: Path, task: dict,
                           project_root: Path) -> bool:
    role = task.get("role") or "application-implementer"
    ws_rel = ws.relative_to(project_root).as_posix()
    result_rel = task.get("result_path")
    if role == "application-implementer":
        return bool(result_rel and rel == f"{ws_rel}/{result_rel}")
    if role == "planner":
        return rel == f"{ws_rel}/IMPLEMENTATION_PLAN.md"
    if role in {"reviewer", "skill-evolution-reviewer"}:
        return rel.startswith(f"{ws_rel}/reviews/")
    if role == "knowledge-curator":
        return rel.startswith((f"{framework_root}/knowledge/", f"{framework_root}/archive/"))
    if role == "skill-evolution-curator":
        return rel.startswith(f"{framework_root}/knowledge/skill-evolution/candidates/")
    if role == "skill-evolution-implementer":
        candidate_id = task.get("candidate_id")
        if not candidate_id:
            return False
        candidate_path = project_root / framework_root / "knowledge" / "skill-evolution" / "candidates" / f"{candidate_id}.yaml"
        try:
            candidate = yaml.safe_load(candidate_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return False
        target_skill = candidate.get("target_skill")
        if not target_skill or task.get("target_skill") != target_skill:
            return False
        if rel.startswith(f"{framework_root}/skills/{target_skill}/"):
            return True
        return rel in set(task.get("approved_reference_paths") or [])
    if role == "orchestrator":
        return rel == f"{ws_rel}/STATE.yaml" or rel.startswith(f"{ws_rel}/generated/")
    return False


def _is_documentation(path: Path) -> bool:
    """Documentation/understanding artifacts are not application code, so they
    are exempt from the knowledge-before-code gate (a .md file can never be a
    runnable code write that the gate exists to order)."""
    retired_spec_root = "".join(("open", "spec")) + "/"
    if path.as_posix().startswith(retired_spec_root):
        return False
    return path.suffix.lower() in _DOC_SUFFIXES


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _is_same_or_child(path: str, parent: str) -> bool:
    return path == parent or path.startswith(parent.rstrip("/") + "/")


def _canonical_hash(value) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _lightweight_active_task(ws: Path):
    contract_path = ws / "generated" / "LIGHTWEIGHT_EXECUTION.yaml"
    task_path = ws / "TASK.yaml"
    if not contract_path.exists() and not task_path.exists():
        return None
    try:
        contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        task = yaml.safe_load(task_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return ("deny", "không đọc được lightweight execution contract")
    if contract.get("version") != 1 or contract.get("status") != "active":
        return ("deny", "lightweight execution contract không active")
    if contract.get("state") != "EXECUTING" or contract.get("task_class") not in {"trivial", "small"}:
        return ("deny", "lightweight execution contract không hợp lệ")
    task_hash = "sha256:" + hashlib.sha256(task_path.read_bytes()).hexdigest()
    if contract.get("task_hash") != task_hash:
        return ("deny", "LIGHTWEIGHT_EXECUTION task hash mismatch")
    scope = contract.get("scope") or {}
    if contract.get("scope_hash") != _canonical_hash(scope):
        return ("deny", "LIGHTWEIGHT_EXECUTION scope hash mismatch")
    task_files = (task.get("scope") or {}).get("files") or {}
    task_scope = {key: sorted(set(task_files.get(key) or [])) for key in ("create", "modify", "delete", "test")}
    if scope != task_scope:
        return ("deny", "LIGHTWEIGHT_EXECUTION scope không khớp TASK.yaml")
    if contract.get("change_id") != (task.get("change_id") or ws.name):
        return ("deny", "LIGHTWEIGHT_EXECUTION change_id mismatch")
    if contract.get("role") != "application-implementer":
        return ("deny", "LIGHTWEIGHT_EXECUTION role không hợp lệ")
    if contract.get("task_class") == "small":
        evidence_path = ws / "EVIDENCE.yaml"
        if not evidence_path.is_file():
            return ("deny", "LIGHTWEIGHT_EXECUTION thiếu EVIDENCE.yaml")
        evidence_hash = "sha256:" + hashlib.sha256(evidence_path.read_bytes()).hexdigest()
        if contract.get("evidence_hash") != evidence_hash:
            return ("deny", "LIGHTWEIGHT_EXECUTION evidence hash mismatch")
    try:
        expires = datetime.fromisoformat((contract.get("runtime") or {})["lease_expires_at"])
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    except (KeyError, TypeError, ValueError):
        return ("deny", "LIGHTWEIGHT_EXECUTION lease không hợp lệ")
    if expires <= datetime.now(timezone.utc):
        return ("deny", "LIGHTWEIGHT_EXECUTION lease đã hết hạn")
    files = {key: list(scope.get(key) or []) for key in ("create", "modify", "delete", "test")}
    if not any(files.values()):
        return ("deny", "LIGHTWEIGHT_EXECUTION scope rỗng")
    return (ws, {
        "id": contract.get("execution_id") or "LIGHTWEIGHT",
        "role": contract.get("role") or "application-implementer",
        "files": files,
        "result_path": "RESULT.yaml" if contract.get("task_class") == "small" else None,
        "contract_type": "lightweight",
    })


def resolve_active_execution(project_root: Path, framework_root: str):
    framework_path = project_root / framework_root
    config_path = _execution_config_path(framework_path)
    try:
        config = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return ("deny", "missing or invalid profiles/execution-mode.yaml")
    if (config or {}).get("workflow_engine") != "vnext":
        return ("deny", "workflow_engine must be vnext")

    active_contracts = []
    inactive_contracts = []
    for contract_path in sorted((framework_path / "changes").glob(
        "*/generated/ACTIVE_EXECUTION.yaml"
    )):
        try:
            contract = yaml.safe_load(contract_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return ("deny", f"ACTIVE_EXECUTION contract không đọc được: {contract_path}")
        if contract.get("status") in {"completed", "failed", "expired"}:
            inactive_contracts.append(contract_path)
            continue
        required = {
            "execution_id", "change_id", "role", "workflow_state", "status",
            "allowed_outputs", "allowed_source_scope", "owner_token",
            "started_at", "lease_expires_at", "prompt_hash",
        }
        if contract.get("version") != 1 or required - set(contract):
            return ("deny", f"ACTIVE_EXECUTION contract thiếu field bắt buộc: {contract_path}")
        ws = contract_path.parent.parent
        if contract.get("change_id") != ws.name or contract.get("status") != "active":
            return ("deny", f"ACTIVE_EXECUTION identity/status không hợp lệ: {contract_path}")
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(contract.get("prompt_hash") or "")):
            return ("deny", f"ACTIVE_EXECUTION prompt_hash không hợp lệ: {contract_path}")
        if not isinstance(contract.get("allowed_outputs"), list) or not isinstance(
                contract.get("allowed_source_scope"), list):
            return ("deny", f"ACTIVE_EXECUTION scope không hợp lệ: {contract_path}")
        try:
            expires = datetime.fromisoformat(str(contract.get("lease_expires_at")))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            return ("deny", f"ACTIVE_EXECUTION lease không hợp lệ: {contract_path}")
        if expires <= datetime.now(timezone.utc):
            return ("deny", f"ACTIVE_EXECUTION lease đã hết hạn: {contract_path}")
        active_contracts.append((ws, contract))
    if len(active_contracts) > 1:
        return ("deny", "có nhiều ACTIVE_EXECUTION contract")
    if active_contracts:
        ws, contract = active_contracts[0]
        outputs = [
            (ws.relative_to(project_root) / Path(path)).as_posix()
            for path in contract.get("allowed_outputs") or []
        ]
        source = list(contract.get("allowed_source_scope") or [])
        return (ws, {
            "id": contract.get("task_id") or contract.get("execution_id"),
            "execution_id": contract.get("execution_id"),
            "role": contract.get("role"),
            "files": {"create": source, "modify": source, "delete": source, "test": []},
            "allowed_outputs": outputs,
            "contract_type": "unified_execution",
        })
    if inactive_contracts:
        return ("deny", "ACTIVE_EXECUTION hiện tại không còn active")

    executing = []
    for state_path in sorted((framework_path / "changes").glob("*/STATE.yaml")):
        try:
            state = yaml.safe_load(state_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        if state.get("state") == "EXECUTING":
            executing.append(state_path.parent)
    if not executing:
        return ("deny", "no vNext EXECUTING change")
    if len(executing) != 1:
        return ("deny", "có nhiều change EXECUTING")

    ws = executing[0]
    lightweight = _lightweight_active_task(ws)
    if lightweight is not None:
        return lightweight
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


def _vnext_active_task(project_root: Path, framework_root: str):
    """Compatibility alias for callers while the unified contract name rolls out."""
    return resolve_active_execution(project_root, framework_root)


def evaluate_write(project_root: Path, target_path: Path, framework_root: str = ".maika",
                   session_identity=None) -> Decision:
    if not target_path.as_posix():
        return Decision(False, "Unable to identify target path for write-gate payload")
    policy_path = _policy_path(project_root, target_path)
    rel = policy_path.as_posix()
    bootstrap_outputs = {
        f"{framework_root}/runtime/BOOTSTRAP_ENV_REPORT.yaml",
        f"{framework_root}/runtime/AGENT_BOOTSTRAP_ACK.yaml",
        # Legacy targets (compatibility window §23.3, removed in PR 16):
        f"{framework_root}/knowledge/active/BOOTSTRAP_REPORT.yaml",
        f"{framework_root}/knowledge/active/AGENT_TRANSPARENCY.md",
    }
    if rel in bootstrap_outputs:
        return Decision(True)
    is_framework = _is_framework_artifact(policy_path, framework_root)
    if _is_documentation(policy_path) and not is_framework:
        return Decision(True)

    session_result = check_session_gate(project_root, framework_root, session_identity)
    if not session_result.ok:
        return session_result

    vnext = _vnext_active_task(project_root, framework_root)
    if vnext[0] == "deny":
        return Decision(False, f"vNext write gate: {vnext[1]}")
    ws, task = vnext
    allowed = set()
    for key in ("create", "modify", "delete", "test"):
        allowed.update((task.get("files") or {}).get(key, []) or [])
    rel = policy_path.relative_to(project_root).as_posix() if policy_path.is_absolute() else rel
    if is_framework:
        ws_rel = ws.relative_to(project_root).as_posix()
        result_rel = task.get("result_path")
        declared = (rel in allowed or rel in set(task.get("allowed_outputs") or [])
                    or (result_rel and rel == f"{ws_rel}/{result_rel}"))
        if not declared:
            return Decision(False, f"role {task.get('role') or 'application-implementer'} không khai báo target {rel}")
        if task.get("contract_type") == "unified_execution":
            return Decision(True)
        if _framework_role_allows(rel, framework_root, ws, task, project_root):
            return Decision(True)
        return Decision(False, f"role {task.get('role') or 'application-implementer'} không có quyền ghi {rel}")
    ws_rel = ws.relative_to(project_root).as_posix()
    result_rel = task.get("result_path")
    if rel in allowed or (result_rel and rel == f"{ws_rel}/{result_rel}"):
        return Decision(True)
    return Decision(False, f"vNext brief-scope: {rel} ngoài files khai báo của {task['id']}")


# --- Secret-gate (P0): mechanical secret protection for Maika-owned artifacts ---
# High-precision, write-side only. Scans content headed for a framework artifact;
# blocks on a hit and records a masked degradation entry (never the raw secret).
# Design: docs/superpowers/specs/2026-07-20-secret-gate-design.md


def _content_text(payload: dict) -> str:
    """Text being introduced by this write (Write content / Edit new_string /
    shell command). Non-string fields are ignored."""
    tool_input = payload.get("tool_input") or {}
    tool_args = (payload.get("toolCall") or {}).get("args") or {}
    fields = (
        tool_input.get("content"), tool_input.get("new_string"),
        tool_input.get("new_str"), tool_input.get("CodeEdit"),
        tool_input.get("command"),
        tool_args.get("content"), tool_args.get("new_string"),
        tool_args.get("CodeEdit"), tool_args.get("CommandLine"),
        tool_args.get("command"),
    )
    return "\n".join(v for v in fields if isinstance(v, str) and v)


def load_secret_config(framework_path: Path) -> dict:
    """Load profiles/secret-gate.yaml (local override wins). Missing → enabled
    defaults; malformed → enabled defaults (fail toward protection)."""
    profiles = framework_path / "profiles"
    for name in ("secret-gate.local.yaml", "secret-gate.yaml"):
        path = profiles / name
        if not path.exists():
            continue
        try:
            data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            return {"enabled": True, "on_error": "block", "_malformed": True}
        if isinstance(data, dict):
            return data
    return {"enabled": True, "on_error": "block"}


def _secret_rules_from_config(config: dict):
    """Filter DEFAULT_RULES by config['rules'][id].enabled; None → all defaults."""
    rule_cfg = config.get("rules") or {}
    if not rule_cfg:
        return None
    return [r for r in _SECRET_RULES
            if (rule_cfg.get(r.id) or {}).get("enabled", True)]


def _secret_allowlisted(rel: str, match, allowlist) -> bool:
    for entry in allowlist or []:
        glob = entry.get("path_glob")
        rule_ids = entry.get("rule_ids")
        if not glob and not rule_ids:
            continue  # an empty entry must not allowlist everything
        if glob and not fnmatch.fnmatch(rel, glob):
            continue
        if rule_ids and match.rule_id not in rule_ids:
            continue
        return True
    return False


def _write_secret_record(project_root: Path, framework_root: str, rel: str,
                         matches, runtime: str) -> Path:
    """Append masked degradation entries. Best-effort; never persists raw secret."""
    record_path = project_root / framework_root / "logs" / "secret-gate.jsonl"
    ts = datetime.now(timezone.utc).isoformat()
    try:
        record_path.parent.mkdir(parents=True, exist_ok=True)
        with record_path.open("a", encoding="utf-8") as f:
            for m in matches:
                f.write(json.dumps({
                    "ts": ts, "gate": "secret-gate", "severity": "high",
                    "action": "blocked", "runtime": runtime,
                    "rule_id": m.rule_id, "label": m.label,
                    "artifact": rel, "line": m.line,
                    "masked_preview": m.masked_preview,
                }, ensure_ascii=False) + "\n")
    except OSError:
        pass
    return record_path


def evaluate_secret_gate(project_root: Path, targets, payload: dict,
                         framework_root: str = ".maika", config=None,
                         runtime: str = "claude"):
    """Return a blocking Decision if the write introduces a secret into a
    Maika-owned artifact; otherwise None (allow)."""
    framework_path = project_root / framework_root
    if config is None:
        config = load_secret_config(framework_path)
    if not config.get("enabled", True):
        return None

    scoped = []
    for target in targets or []:
        policy = _policy_path(project_root, target)
        if _is_framework_artifact(policy, framework_root):
            scoped.append(policy.as_posix())
    if not scoped:
        return None

    content = _content_text(payload)
    if not content:
        return None

    try:
        matches = _secret_scan(content, _secret_rules_from_config(config))
    except Exception:  # a scanner bug must never silently leak a secret
        if (config.get("on_error") or "block") == "allow":
            _warn("write-gate: secret-gate scanner error — on_error=allow, permitting write")
            return None
        return Decision(False, "[R-Guard-3] secret-gate: scanner error (fail-closed); write blocked")
    if not matches:
        return None

    allowlist = config.get("allowlist") or []
    for rel in scoped:
        live = [m for m in matches if not _secret_allowlisted(rel, m, allowlist)]
        if not live:
            continue
        record_path = _write_secret_record(project_root, framework_root, rel, live, runtime)
        try:
            record_rel = record_path.relative_to(project_root).as_posix()
        except ValueError:
            record_rel = record_path.as_posix()
        detail = ", ".join(f"{m.rule_id}@L{m.line} (masked: {m.masked_preview})" for m in live)
        return Decision(
            False,
            f"[R-Guard-3] secret-gate: blocked write to {rel} — "
            f"{len(live)} match(es): {detail}; record: {record_rel}",
        )
    return None


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
        if not targets:
            if unresolved:
                command = _command_text(payload)
                active = _vnext_active_task(root, args.framework_root)
                framework_hint = args.framework_root in command
                if active[0] != "deny" or framework_hint:
                    decision = Decision(False, "write-gate: unresolved dynamic write fails closed")
                else:
                    decision = Decision(
                        False,
                        "write-gate: unresolved possible write requires an active scoped execution",
                    )
            else:
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

    if decision.ok:
        secret_decision = evaluate_secret_gate(
            root, targets, payload, framework_root=args.framework_root,
            runtime=args.runtime,
        )
        if secret_decision is not None:
            decision = secret_decision

    return _print_runtime_decision(args.runtime, decision)


if __name__ == "__main__":
    sys.exit(main())
