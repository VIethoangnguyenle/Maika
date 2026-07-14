"""Safety primitives shared by adaptive and full Maika workflows."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import os
import re
import secrets
import shlex
import shutil
import signal
import socket
import subprocess
import sys
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import yaml


DEFAULT_ALLOWED_EXECUTABLES = {
    "./gradlew", "gradlew", "mvn", "pytest", "python", "python3", "npm", "pnpm",
    "go", "cargo", "git",
}
CONFIRMATION_EXECUTABLES = {"docker", "kubectl", "terraform", "flyway", "liquibase"}
DENIED_TOKENS = ("rm -rf", "sudo", "| sh", "| bash", "mkfs", ":(){", "> /dev/")
# Interpreters that can execute arbitrary inline code. Running them with an
# inline-code flag turns a "verification command" into arbitrary code execution
# (plan §2.2: `python -c "import shutil; shutil.rmtree('src')"`), so it is denied.
_INTERPRETERS = {"python", "python2", "python3", "node", "nodejs", "ruby",
                 "perl", "bash", "sh", "zsh", "php", "deno"}
_INLINE_CODE_FLAGS = {"-c", "-e", "--eval", "--command", "-"}


def _executable_stem(executable: str) -> str:
    name = Path(executable).name
    low = name.lower()
    for ext in (".exe", ".bat", ".cmd", ".com"):
        if low.endswith(ext):
            return name[: -len(ext)]
    return name
VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "REJECTED"}
AUTHORITY_ORDER = {"trivial": 0, "small": 1, "standard": 2, "architectural": 3}
DEFAULT_VERIFICATION_PROFILES = {
    "python-version": {"executable": "python", "fixed_args": ["--version"], "allowed_parameters": {}, "category": "test"},
    "pytest-paths": {"executable": "pytest", "fixed_args": [], "allowed_parameters": {
        "paths": {"type": "path-list", "must_be_inside_repo": True},
        "tests": {"flag": "-k", "type": "string", "pattern": r"^[A-Za-z0-9_ .:-]+$"},
    }, "category": "test"},
    "gradle-test": {"executable": "./gradlew", "fixed_args": ["test"], "allowed_parameters": {
        "tests": {"flag": "--tests", "type": "list", "pattern": r"^[A-Za-z0-9_.$*:-]+$"},
    }, "category": "test"},
    "gradle-build": {"executable": "./gradlew", "fixed_args": ["build", "--no-daemon"],
                     "allowed_parameters": {}, "category": "build"},
    "maika-ci": {"executable": "python", "fixed_args": ["scripts/run_ci.py"],
                 "allowed_parameters": {}, "category": "test", "trusted_repo_paths": ["scripts/run_ci.py"]},
}


class CommandDenied(ValueError):
    pass


class HumanConfirmationRequired(CommandDenied):
    pass


class WorkspaceBusy(RuntimeError):
    pass


class ReviewInvalid(ValueError):
    pass


def load_verification_profiles(path: Path | None = None) -> dict:
    if path is None or not Path(path).exists():
        return {"version": 1, "profiles": DEFAULT_VERIFICATION_PROFILES}
    doc = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    if doc.get("version") != 1 or not isinstance(doc.get("profiles"), dict):
        raise CommandDenied("invalid verification profile registry")
    return doc


def compile_verification_command(proposal: dict, profile_registry: dict, repo_root: Path) -> dict:
    """Compile agent-selected parameters through a trusted command profile."""
    if not isinstance(proposal, dict) or not isinstance(proposal.get("profile"), str):
        raise CommandDenied("verification command requires a trusted profile")
    profile_name = proposal["profile"]
    profile = (profile_registry.get("profiles") or {}).get(profile_name)
    if not isinstance(profile, dict):
        raise CommandDenied(f"unknown verification profile: {profile_name}")
    parameters = proposal.get("parameters") or {}
    allowed_parameters = profile.get("allowed_parameters") or {}
    unknown = set(parameters) - set(allowed_parameters)
    if unknown:
        raise CommandDenied(f"unsupported parameters for {profile_name}: {sorted(unknown)}")
    args = list(profile.get("fixed_args") or [])
    repo_root = Path(repo_root).resolve()
    for name, value in parameters.items():
        rule = allowed_parameters[name]
        values = value if isinstance(value, list) else [value]
        if rule.get("type") in {"list", "path-list"} and not isinstance(value, list):
            raise CommandDenied(f"parameter {name} must be a list")
        if rule.get("type") == "string" and not isinstance(value, str):
            raise CommandDenied(f"parameter {name} must be a string")
        for item in values:
            if not isinstance(item, str) or not item:
                raise CommandDenied(f"parameter {name} contains an invalid value")
            if any(token in item for token in (";", "&&", "||", "\n", "\r", "\0")):
                raise CommandDenied(f"command separator denied in parameter {name}")
            pattern = rule.get("pattern")
            if pattern and not re.fullmatch(pattern, item):
                raise CommandDenied(f"parameter {name} does not match its profile pattern")
            if rule.get("type") == "path-list":
                candidate = (repo_root / item).resolve()
                try:
                    candidate.relative_to(repo_root)
                except ValueError as exc:
                    raise CommandDenied(f"verification path escapes repo: {item}") from exc
            if rule.get("flag"):
                args.append(str(rule["flag"]))
            args.append(item)
    executable = profile.get("executable")
    if not isinstance(executable, str):
        raise CommandDenied(f"profile {profile_name} has no executable")
    if executable == Path(executable).name:
        resolved = shutil.which(executable)
        if resolved:
            resolved_path = Path(resolved).resolve()
            try:
                resolved_path.relative_to(repo_root)
            except ValueError:
                pass
            else:
                raise CommandDenied(f"profile executable resolves inside repo: {executable}")
        elif executable != "python":
            raise CommandDenied(f"profile executable is unavailable: {executable}")
    for trusted_path in profile.get("trusted_repo_paths") or []:
        target = (repo_root / trusted_path).resolve()
        try:
            target.relative_to(repo_root)
        except ValueError as exc:
            raise CommandDenied(f"trusted profile path escapes repo: {trusted_path}") from exc
        if not target.is_file():
            raise CommandDenied(f"trusted profile path is missing: {trusted_path}")
    return {"version": 1, "profile": profile_name, "executable": executable, "args": args,
            "category": profile.get("category", "other")}


def verification_command_hash(command: dict) -> str:
    payload = json.dumps({"executable": command.get("executable"), "args": command.get("args") or []},
                         sort_keys=True, separators=(",", ":"))
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def trusted_approval_matches(path: Path, change_id: str, command: dict) -> bool:
    try:
        approval = yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return False
    return (
        approval.get("version") == 1
        and approval.get("source") == "cli-user-action"
        and approval.get("change_id") == change_id
        and approval.get("command_hash") == verification_command_hash(command)
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_command(command: dict | str) -> dict:
    if isinstance(command, str):
        parts = shlex.split(command)
        if not parts:
            raise CommandDenied("empty command")
        return {"version": 1, "executable": parts[0], "args": parts[1:], "category": "other"}
    if not isinstance(command, dict):
        raise CommandDenied("command must be a structured mapping")
    if command.get("version", 1) != 1:
        raise CommandDenied("unsupported command schema version")
    executable = command.get("executable")
    args = command.get("args", [])
    if not isinstance(executable, str) or not executable or not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
        raise CommandDenied("command requires executable and string args")
    return {**command, "version": 1, "args": list(args), "category": command.get("category", "other")}


def validate_command(command: dict | str, allowed_executables=None, human_confirmed: bool = False,
                     confirmation_executables=None) -> dict:
    spec = normalize_command(command)
    executable = spec["executable"]
    allowed = set(DEFAULT_ALLOWED_EXECUTABLES if allowed_executables is None else allowed_executables)
    confirmations = set(CONFIRMATION_EXECUTABLES if confirmation_executables is None else confirmation_executables)
    allowed_identities = allowed | {Path(item).name for item in allowed}
    name = Path(executable).name
    stem = _executable_stem(executable)
    is_path_form = executable != name  # contains a directory separator / is a path
    if executable in allowed:
        pass  # explicit allowlist entry (bare name, ./gradlew, or a trusted full path)
    elif is_path_form:
        # A path whose basename merely matches ("/tmp/python") is a fake-executable
        # bypass: the trusted interpreter must be named as a bare command (resolved
        # from PATH) or allowlisted verbatim.
        raise CommandDenied(f"path-form executable must be allowlisted verbatim: {executable}")
    elif not ({name, stem} & allowed_identities):
        # Only real executable extensions (.exe/.bat/...) are stripped, so a
        # "python.py" file cannot masquerade as the "python" interpreter.
        raise CommandDenied(f"executable is not allowlisted: {executable}")
    if (stem in _INTERPRETERS or name in _INTERPRETERS) and \
            any(arg in _INLINE_CODE_FLAGS for arg in spec["args"]):
        raise CommandDenied(f"inline interpreter code is not allowed: {executable} {spec['args'][:1]}")
    rendered = " ".join([executable, *spec["args"]]).lower()
    if any(token in rendered for token in DENIED_TOKENS):
        raise CommandDenied(f"dangerous command denied: {rendered}")
    if (name in confirmations or stem in confirmations) and not human_confirmed:
        raise HumanConfirmationRequired(f"human confirmation required for {executable}")
    return spec


def execute_command(command: dict | str, working_directory: Path, *, allowed_executables=None,
                    human_confirmed=False, confirmation_executables=None,
                    timeout=600, output_cap=2000) -> dict:
    spec = validate_command(command, allowed_executables, human_confirmed, confirmation_executables)
    if spec["executable"] == "python" and shutil.which("python") is None:
        spec["executable"] = sys.executable
    argv = [spec["executable"], *spec["args"]]
    started = _now()
    try:
        process = subprocess.Popen(
            argv, cwd=str(Path(working_directory).resolve()), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, shell=False,
            start_new_session=(os.name != "nt"),
            creationflags=(subprocess.CREATE_NEW_PROCESS_GROUP if os.name == "nt" else 0),
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
            if os.name == "nt":  # pragma: no cover - Windows CI
                process.kill()
            else:
                os.killpg(process.pid, signal.SIGKILL)
            output, _ = process.communicate()
            output = (output or "") + f"\ncommand timeout after {timeout}s"
            exit_code = 124
    except OSError as exc:
        output, exit_code = f"command error: {exc}", 127
    observed = (output or "")[-output_cap:]
    return {
        "version": 1, "executable": spec["executable"], "args": spec["args"],
        "command": shlex.join(argv), "category": spec["category"],
        "observed_output": observed, "exit_code": exit_code,
        "timestamp": started, "shell": False,
        "interpretation": "pass" if exit_code == 0 else "fail",
    }


def _process_alive(pid: int) -> bool:
    """Return True iff a process with ``pid`` currently exists.

    Cross-platform and non-destructive: on POSIX this is the classic
    ``os.kill(pid, 0)`` probe, but on Windows ``os.kill`` with a non-CTRL signal
    calls ``TerminateProcess`` — so there we query the process handle directly
    and never signal it.
    """
    if pid <= 0:
        return False
    if os.name == "nt":  # pragma: no cover - exercised only on Windows CI
        import ctypes

        PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
        STILL_ACTIVE = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not handle:
            return False
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(code)):
                return False
            return code.value == STILL_ACTIVE
        finally:
            kernel32.CloseHandle(handle)
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # exists but owned by another user
    except OSError:
        return False
    return True


class WorkspaceLock:
    def __init__(self, path: Path, task_id: str, recover_orphans: bool = True,
                 lease_seconds: int = 900):
        self.path = Path(path)
        self.task_id = task_id
        self.recover_orphans = recover_orphans
        self.lease_seconds = lease_seconds
        self.acquired = False
        self.recovered_orphan = False
        self.owner_token = secrets.token_hex(16)
        self.generation = 1
        self._heartbeat_stop = threading.Event()
        self._heartbeat_thread = None

    def _read_lock(self) -> dict:
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8"))
        except (OSError, yaml.YAMLError) as exc:
            raise WorkspaceBusy(f"cannot read workspace lock {self.path}: {exc}") from exc
        if not isinstance(data, dict) or data.get("version") not in {1, 2}:
            raise WorkspaceBusy(f"malformed workspace lock: {self.path}")
        return data

    @staticmethod
    def _owner_token(data: dict) -> str:
        return str(data.get("owner_token") or (data.get("lease") or {}).get("owner_token") or "")

    def _orphaned(self) -> bool:
        data = self._read_lock()
        # A live process on this host owns the lock even if its heartbeat was
        # delayed.  Wall-clock expiry alone must not permit concurrent takeover.
        if data.get("host") == socket.gethostname():
            try:
                pid = int(data.get("pid"))
            except (TypeError, ValueError):
                raise WorkspaceBusy(f"workspace lock has invalid pid: {self.path}")
            if _process_alive(pid):
                return False
            return True
        lease = data.get("lease") or {}
        try:
            expires = datetime.fromisoformat(str(lease.get("expires_at")))
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=timezone.utc)
            if expires <= datetime.now(timezone.utc):
                return True
        except (TypeError, ValueError):
            pass
        return False

    def _payload(self, now: datetime) -> dict:
        return {
            "version": 2,
            "owner_token": self.owner_token,
            "generation": self.generation,
            "pid": os.getpid(),
            "host": socket.gethostname(),
            "started_at": now.isoformat(),
            "task_id": self.task_id,
            "lease": {
                "owner": f"{socket.gethostname()}:{os.getpid()}",
                "owner_token": self.owner_token,
                "generation": self.generation,
                "acquired_at": now.isoformat(),
                "expires_at": (now + timedelta(seconds=self.lease_seconds)).isoformat(),
                "heartbeat_at": now.isoformat(),
            },
        }

    def _start_heartbeat(self) -> None:
        interval = max(0.1, min(30.0, self.lease_seconds / 3))

        def run() -> None:
            while not self._heartbeat_stop.wait(interval):
                try:
                    self.heartbeat()
                except (OSError, WorkspaceBusy, yaml.YAMLError):
                    self._audit("heartbeat_lost_ownership")
                    return

        self._heartbeat_stop.clear()
        self._heartbeat_thread = threading.Thread(
            target=run, name=f"maika-lock-{self.task_id}", daemon=True,
        )
        self._heartbeat_thread.start()

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        now = datetime.now(timezone.utc)
        if self.path.exists():
            try:
                existing = self._read_lock()
                self.generation = int(existing.get("generation") or
                                      (existing.get("lease") or {}).get("generation") or 0) + 1
            except (TypeError, ValueError):
                raise WorkspaceBusy(f"workspace lock has invalid generation: {self.path}")
        payload = yaml.safe_dump(self._payload(now), sort_keys=False)
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                self.acquired = True
                self._start_heartbeat()
                return self
            except FileExistsError:
                if attempt == 0 and self.recover_orphans and self._orphaned():
                    self._audit("recovered_expired_or_orphaned")
                    self.path.unlink(missing_ok=True)
                    self.recovered_orphan = True
                    continue
                raise WorkspaceBusy(f"workspace is locked: {self.path}")

    def _audit(self, action: str) -> None:
        audit = self.path.parent / "LOCK_AUDIT.jsonl"
        record = {"version": 1, "action": action, "task_id": self.task_id,
                  "actor": f"{socket.gethostname()}:{os.getpid()}", "at": _now()}
        with audit.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")

    def heartbeat(self) -> None:
        if not self.acquired:
            raise WorkspaceBusy("cannot heartbeat an unowned lock")
        data = self._read_lock()
        if self._owner_token(data) != self.owner_token or int(data.get("generation") or 0) != self.generation:
            self.acquired = False
            raise WorkspaceBusy("cannot heartbeat lock owned by another execution")
        now = datetime.now(timezone.utc)
        data["lease"] = {**(data.get("lease") or {}), "heartbeat_at": now.isoformat(),
                         "expires_at": (now + timedelta(seconds=self.lease_seconds)).isoformat()}
        temp = self.path.with_name(f".{self.path.name}.{self.owner_token}.tmp")
        temp.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
        current = self._read_lock()
        if self._owner_token(current) != self.owner_token or int(current.get("generation") or 0) != self.generation:
            temp.unlink(missing_ok=True)
            self.acquired = False
            raise WorkspaceBusy("lost workspace lock before heartbeat commit")
        os.replace(temp, self.path)

    @classmethod
    def force_unlock(cls, path: Path, task_id: str) -> bool:
        lock = cls(path, task_id, recover_orphans=False)
        if not lock.path.exists():
            return False
        lock._audit("force_unlock")
        lock.path.unlink()
        return True

    def release(self):
        self._heartbeat_stop.set()
        if self._heartbeat_thread is not None and self._heartbeat_thread is not threading.current_thread():
            self._heartbeat_thread.join(timeout=1)
        if not self.acquired:
            return
        try:
            data = self._read_lock()
        except WorkspaceBusy:
            self.acquired = False
            return
        if self._owner_token(data) == self.owner_token and int(data.get("generation") or 0) == self.generation:
            self.path.unlink(missing_ok=True)
        else:
            self._audit("release_skipped_not_owner")
        self.acquired = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()


def parse_review(text: str, review_type: str, reviewed_commit: str | None = None,
                 reviewed_plan_hash: str | None = None) -> dict:
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.startswith("---\n") or "\n---\n" not in text[4:]:
        raise ReviewInvalid("review requires YAML front matter")
    front, body = text[4:].split("\n---\n", 1)
    if len(re.findall(r"(?mi)^verdict\s*:", front)) != 1:
        raise ReviewInvalid("multiple verdict fields")
    try:
        data = yaml.safe_load(front) or {}
    except yaml.YAMLError as exc:
        raise ReviewInvalid(f"malformed review YAML: {exc}") from exc
    if data.get("schema_version") != 1 or data.get("review_type") != review_type:
        raise ReviewInvalid("unsupported schema or review type")
    if data.get("verdict") not in VERDICTS:
        raise ReviewInvalid("unsupported verdict")
    if reviewed_commit is not None and data.get("reviewed_commit") != reviewed_commit:
        raise ReviewInvalid("reviewed commit mismatch")
    if reviewed_plan_hash is not None and data.get("reviewed_plan_hash") != reviewed_plan_hash:
        raise ReviewInvalid("reviewed plan hash mismatch")
    return {**data, "body": body}


def _knowledge_source_path(item: dict) -> str | None:
    source = item.get("source")
    if item.get("source_path"):
        return str(item["source_path"])
    if isinstance(source, dict):
        for key in ("file", "path"):
            if source.get(key):
                return str(source[key])
    paths = item.get("affected_paths") or []
    if len(paths) == 1 and not any(char in paths[0] for char in "*?["):
        return str(paths[0])
    return None


def can_reuse_evidence(item: dict, repo_root: Path, task_class: str) -> tuple[bool, str]:
    if item.get("status") != "active" or item.get("superseded_by"):
        return False, "claim is inactive or superseded"
    if task_class == "trivial":
        return True, "reusable"
    required = AUTHORITY_ORDER.get(task_class, 2)
    actual = AUTHORITY_ORDER.get(item.get("authority", "trivial"), 0)
    if actual < required:
        return False, "authority is insufficient"
    source_path = _knowledge_source_path(item)
    if not source_path:
        return False, "evidence requires a digest-bound source path"
    path = Path(repo_root) / source_path
    if not path.is_file():
        return False, "source path is missing"
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item.get("source_digest"):
        return False, "source digest changed"
    if task_class == "architectural" and not (
        item.get("revalidated_at") or (isinstance(item.get("freshness"), dict)
                                       and item["freshness"].get("revalidated_at"))
    ):
        return False, "architectural evidence requires explicit revalidation"
    return True, "reusable"


def select_knowledge_slice(index_path: Path, store: Path, repo_root: Path, task_type: str,
                           artifact_type: str, categories: list[str], affected_paths: list[str],
                           task_class: str = "standard", search_terms: set[str] | None = None,
                           max_items: int | None = None, store_name: str | None = None) -> dict:
    """Canonical knowledge retrieval, freshness validation, ranking and trimming."""
    index = yaml.safe_load(Path(index_path).read_text(encoding="utf-8")) or {}
    category_set = set(categories)
    terms = {str(term).lower() for term in (search_terms or set())}
    refs = []
    retrieved = 0
    rejected_scope = 0
    for ref in index.get("entries") or []:
        if store_name and ref.get("store") != store_name:
            continue
        if ref.get("status", "active") != "active" or ref.get("superseded_by"):
            continue
        if category_set and ref.get("type") not in category_set:
            continue
        applies = {str(value).lower() for value in ref.get("applies_to") or []}
        haystack = " ".join([str(ref.get("id", "")), str(ref.get("title", "")), *applies]).lower()
        if terms and not any(term in haystack for term in terms):
            continue
        retrieved += 1
        patterns = ref.get("affected_paths") or []
        if affected_paths and patterns and not any(
            fnmatch.fnmatch(path, pattern) for path in affected_paths for pattern in patterns
        ):
            rejected_scope += 1
            continue
        refs.append(ref)

    metrics = {"retrieved": retrieved, "eligible": 0, "reused": 0,
               "rejected_stale": 0, "rejected_authority": 0, "rejected_scope": rejected_scope,
               "revalidated": 0, "newly_created": 0, "evidence_omitted": 0}
    eligible = []
    for ref in refs:
        rel = ref.get("path") or ref.get("file")
        try:
            item = yaml.safe_load((Path(store) / rel).read_text(encoding="utf-8")) or {}
        except (OSError, TypeError, yaml.YAMLError):
            metrics["rejected_stale"] += 1
            continue
        reusable, reason = can_reuse_evidence(item, repo_root, task_class)
        if not reusable:
            key = "rejected_authority" if "authority" in reason else "rejected_stale"
            metrics[key] += 1
            continue
        normalized = {
            **item,
            "source": item.get("source") or {},
            "source_digest": item.get("source_digest"),
            "source_commit": item.get("source_commit"),
            "authority": item.get("authority", "trivial"),
            "freshness": item.get("freshness", "verified"),
            "reuse_decision": "reused",
        }
        eligible.append(normalized)
        if task_class == "architectural":
            metrics["revalidated"] += 1
    eligible.sort(key=lambda item: (-AUTHORITY_ORDER.get(item.get("authority", "trivial"), 0),
                                    str(item.get("id") or "")))
    metrics["eligible"] = len(eligible)
    if max_items is not None and len(eligible) > max_items:
        metrics["evidence_omitted"] = len(eligible) - max_items
        eligible = eligible[:max_items]
    metrics["reused"] = len(eligible)
    return {
        "version": 1, "task_type": task_type, "artifact_type": artifact_type,
        "categories": categories, "relevant_ids": [item.get("id") for item in eligible],
        "entries": eligible, "evidence_metrics": metrics,
    }


def load_knowledge_slice(index_path: Path, store: Path, task_type: str, artifact_type: str,
                         categories: list[str], affected_paths: list[str]) -> dict:
    """Compatibility wrapper; production code uses select_knowledge_slice."""
    return select_knowledge_slice(index_path, store, store, task_type, artifact_type,
                                  categories, affected_paths, task_class="trivial")


LEARNING_SIGNALS = (
    "human_corrections", "repeated_failures", "unexpected_blast_radius",
    "reusable_review_findings", "observed_convention_count", "measurable_token_reduction",
)


def should_create_learning_candidate(metrics: dict) -> bool:
    return any(float(metrics.get(signal) or 0) > 0 for signal in LEARNING_SIGNALS)


def skill_evaluation(skill: str, candidate_version: str, evaluation_tasks: list[str],
                     before_metrics: dict, after_metrics: dict, verdict: str) -> dict:
    return {"version": 1, "skill_evaluation": {
        "skill": skill, "candidate_version": candidate_version,
        "evaluation_tasks": evaluation_tasks, "before_metrics": before_metrics,
        "after_metrics": after_metrics, "verdict": verdict,
        "rollback_version": "previous",
    }}
