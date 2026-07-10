"""Safety primitives shared by adaptive and full Maika workflows."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import re
import shlex
import shutil
import signal
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


DEFAULT_ALLOWED_EXECUTABLES = {
    "./gradlew", "gradlew", "mvn", "pytest", "python", "python3", "npm", "pnpm",
    "go", "cargo", "git",
}
CONFIRMATION_EXECUTABLES = {"docker", "kubectl", "terraform", "flyway", "liquibase"}
DENIED_TOKENS = ("rm -rf", "sudo", "| sh", "| bash", "mkfs", ":(){", "> /dev/")
VERDICTS = {"APPROVED", "CHANGES_REQUESTED", "REJECTED"}
AUTHORITY_ORDER = {"trivial": 0, "small": 1, "standard": 2, "architectural": 3}


class CommandDenied(ValueError):
    pass


class HumanConfirmationRequired(CommandDenied):
    pass


class WorkspaceBusy(RuntimeError):
    pass


class ReviewInvalid(ValueError):
    pass


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


def validate_command(command: dict | str, allowed_executables=None, human_confirmed: bool = False) -> dict:
    spec = normalize_command(command)
    executable = spec["executable"]
    allowed = set(allowed_executables or DEFAULT_ALLOWED_EXECUTABLES)
    identity = executable if executable in allowed else Path(executable).name
    allowed_identities = allowed | {Path(item).name for item in allowed}
    if identity not in allowed_identities:
        raise CommandDenied(f"executable is not allowlisted: {executable}")
    rendered = " ".join([executable, *spec["args"]]).lower()
    if any(token in rendered for token in DENIED_TOKENS):
        raise CommandDenied(f"dangerous command denied: {rendered}")
    if Path(executable).name in CONFIRMATION_EXECUTABLES and not human_confirmed:
        raise HumanConfirmationRequired(f"human confirmation required for {executable}")
    return spec


def execute_command(command: dict | str, working_directory: Path, *, allowed_executables=None,
                    human_confirmed=False, timeout=600, output_cap=2000) -> dict:
    spec = validate_command(command, allowed_executables, human_confirmed)
    if spec["executable"] == "python" and shutil.which("python") is None:
        spec["executable"] = sys.executable
    argv = [spec["executable"], *spec["args"]]
    started = _now()
    try:
        process = subprocess.Popen(
            argv, cwd=str(Path(working_directory).resolve()), stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT, text=True, shell=False, start_new_session=True,
        )
        try:
            output, _ = process.communicate(timeout=timeout)
            exit_code = process.returncode
        except subprocess.TimeoutExpired:
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


class WorkspaceLock:
    def __init__(self, path: Path, task_id: str, recover_orphans: bool = True):
        self.path = Path(path)
        self.task_id = task_id
        self.recover_orphans = recover_orphans
        self.acquired = False
        self.recovered_orphan = False

    def _orphaned(self) -> bool:
        try:
            data = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
            if data.get("host") != socket.gethostname():
                return False
            pid = int(data.get("pid"))
            os.kill(pid, 0)
            return False
        except ProcessLookupError:
            return True
        except (OSError, TypeError, ValueError, yaml.YAMLError):
            return False

    def acquire(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = yaml.safe_dump({
            "version": 1, "pid": os.getpid(), "host": socket.gethostname(),
            "started_at": _now(), "task_id": self.task_id,
        }, sort_keys=False)
        for attempt in range(2):
            try:
                fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w", encoding="utf-8") as handle:
                    handle.write(payload)
                self.acquired = True
                return self
            except FileExistsError:
                if attempt == 0 and self.recover_orphans and self._orphaned():
                    self.path.unlink(missing_ok=True)
                    self.recovered_orphan = True
                    continue
                raise WorkspaceBusy(f"workspace is locked: {self.path}")

    def release(self):
        if self.acquired:
            self.path.unlink(missing_ok=True)
            self.acquired = False

    def __enter__(self):
        return self.acquire()

    def __exit__(self, *_):
        self.release()


def parse_review(text: str, review_type: str, reviewed_commit: str | None = None,
                 reviewed_plan_hash: str | None = None) -> dict:
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


def load_knowledge_slice(index_path: Path, store: Path, task_type: str, artifact_type: str,
                         categories: list[str], affected_paths: list[str]) -> dict:
    index = yaml.safe_load(Path(index_path).read_text(encoding="utf-8")) or {}
    category_set = set(categories)
    selected = []
    for ref in index.get("entries") or []:
        category_match = not category_set or ref.get("type") in category_set
        patterns = ref.get("affected_paths") or []
        path_match = not affected_paths or not patterns or any(
            fnmatch.fnmatch(path, pattern) for path in affected_paths for pattern in patterns
        )
        if category_match and path_match:
            selected.append(ref)
    entries = []
    for ref in selected:
        item = yaml.safe_load((Path(store) / ref["file"]).read_text(encoding="utf-8")) or {}
        if item.get("status") == "active":
            entries.append(item)
    return {
        "version": 1, "task_type": task_type, "artifact_type": artifact_type,
        "categories": categories, "relevant_ids": [item.get("id") for item in entries],
        "entries": entries,
    }


def can_reuse_evidence(item: dict, repo_root: Path, task_class: str) -> tuple[bool, str]:
    if item.get("status") != "active" or item.get("superseded_by"):
        return False, "claim is inactive or superseded"
    required = AUTHORITY_ORDER.get(task_class, 2)
    actual = AUTHORITY_ORDER.get(item.get("authority", "trivial"), 0)
    if actual < required:
        return False, "authority is insufficient"
    paths = item.get("affected_paths") or []
    if len(paths) != 1:
        return False, "evidence requires one digest-bound path"
    path = Path(repo_root) / paths[0]
    if not path.is_file():
        return False, "source path is missing"
    digest = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != item.get("source_digest"):
        return False, "source digest changed"
    return True, "reusable"


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
