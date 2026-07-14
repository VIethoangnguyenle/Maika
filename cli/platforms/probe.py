"""Typed advertise → detect → verify pipeline for host adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shlex
import shutil
import subprocess
import sys
from typing import Callable, Mapping, Optional

import yaml

from cli.config.platforms import adapter_descriptor
from cli.platforms import get_platform
from cli.runtime.platform_profile import load_platform_runtime_profile, profile_fingerprint, profile_path
from cli.runtime.worker_resolver import FRESH_PROCESS, WorkerProfile, run_worker_smoke_test
from cli.runtime.binary_identity import binary_identity, identities_match
from cli.install.json_merge import MAIKA_WRITE_GATE_ID

# Directory that contains the ``cli`` package — put on PYTHONPATH for the hook
# smoke subprocess so ``python -m cli.maika`` resolves in dev and wheel installs.
_PKG_PARENT = Path(__file__).resolve().parents[2]
_VERSION_RE = re.compile(r"(\d+)\.(\d+)(?:\.(\d+))?")


def parse_version(text: Optional[str]) -> Optional[tuple]:
    """Extract a dotted numeric version from CLI ``--version`` output, or None."""
    if not text:
        return None
    match = _VERSION_RE.search(text)
    if not match:
        return None
    return tuple(int(part) if part is not None else 0 for part in match.groups())


@dataclass(frozen=True)
class BinaryProbe:
    name: Optional[str]
    found: bool
    path: Optional[str]
    version: Optional[str]
    version_supported: bool


@dataclass(frozen=True)
class PlatformProbeResult:
    platform: str
    binary: BinaryProbe
    authentication: str
    capabilities: Mapping[str, str]
    verification: Mapping[str, str]
    support_tier: int


def detect_binary(name: Optional[str], timeout: int = 5) -> BinaryProbe:
    path = shutil.which(name) if name else None
    if not path:
        return BinaryProbe(name, False, None, None, False)
    try:
        proc = subprocess.run(
            [path, "--version"], shell=False, capture_output=True, text=True,
            timeout=timeout, check=False,
        )
        raw = (proc.stdout or proc.stderr or "").strip()
        # A clean exit is necessary but not sufficient: require a parseable
        # version so `--version` printing anything on exit 0 is not mistaken for
        # a supported version. Adapter-declared floors can tighten this once a
        # real minimum is known.
        supported = proc.returncode == 0 and parse_version(raw) is not None
        return BinaryProbe(name, True, path, raw or None, supported)
    except (OSError, subprocess.TimeoutExpired):
        return BinaryProbe(name, True, path, None, False)


def _verify_entrypoint(project_root: Path, platform_key: str) -> str:
    path = project_root / adapter_descriptor(platform_key)["entrypoint"]
    return "verified" if path.is_file() and path.stat().st_size > 0 else "unavailable"


_HOOK_RUNTIME = {"claude-code": "claude", "codex": "codex", "antigravity": "antigravity"}
# stderr fragments that mean the CLI short-circuited before actually evaluating.
_HOOK_SHORT_CIRCUIT = (
    "not a Maika project", "malformed Maika config", "canonical project evaluator missing",
)


def _verify_hook(project_root: Path, platform_key: str) -> str:
    relative = adapter_descriptor(platform_key)["hook_config"]
    if relative is None:
        return "unsupported"
    path = project_root / relative
    if not path.is_file():
        return "unavailable"
    try:
        doc = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return "degraded"
    if not isinstance(doc.get("hooks"), dict):
        return "degraded"
    if not (project_root / ".maika/hooks/write-gate/write_gate.py").is_file():
        return "unavailable"
    managed = []

    def collect(value):
        if isinstance(value, dict):
            if value.get("id") == MAIKA_WRITE_GATE_ID:
                managed.append(value)
            for child in value.values():
                collect(child)
        elif isinstance(value, list):
            for child in value:
                collect(child)

    collect(doc["hooks"])
    if len(managed) != 1 or not isinstance(managed[0].get("command"), str):
        return "degraded"
    command = managed[0]["command"]
    if any(token in command for token in (";", "&&", "||", "|", "`", "$(")):
        return "degraded"
    try:
        argv = shlex.split(command, posix=os.name != "nt")
    except ValueError:
        return "degraded"
    runtime = _HOOK_RUNTIME.get(platform_key, "claude")
    expected = ["hook", "write-gate", "--runtime", runtime, "--platform", platform_key]
    if len(argv) < 2 or argv[1:] != expected:
        return "degraded"
    executable = shutil.which(argv[0])
    if not executable:
        return "degraded"
    argv[0] = str(Path(executable).resolve())
    payload = json.dumps({"tool_name": "Write", "tool_input": {"file_path": "README.md"}})
    env = {**os.environ, "MAIKA_HOOK_SMOKE": "1", "PYTHONPATH": os.pathsep.join(
        part for part in (str(_PKG_PARENT), os.environ.get("PYTHONPATH", "")) if part)}
    try:
        proc = subprocess.run(
            argv,
            cwd=str(project_root), input=payload, capture_output=True, text=True,
            timeout=30, check=False, env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "degraded"
    if any(fragment in (proc.stderr or "") for fragment in _HOOK_SHORT_CIRCUIT):
        return "degraded"  # the pipeline did not actually evaluate the payload
    if proc.returncode != 0:
        return "degraded"
    if runtime == "claude":
        return "verified"
    try:
        output = json.loads((proc.stdout or "").strip())
    except json.JSONDecodeError:
        return "degraded"
    if runtime == "codex":
        decision = ((output.get("hookSpecificOutput") or {}).get("permissionDecision"))
    else:
        decision = output.get("decision")
    return "verified" if decision == "allow" else "degraded"


def support_tier(verification: Mapping[str, str], *, adapter_enabled: bool = True) -> int:
    if not adapter_enabled:
        return 0
    if verification.get("entrypoint") != "verified":
        return 0
    if verification.get("hook") != "verified" or verification.get("worker") != "verified":
        return 1
    if verification.get("mcp") == "verified":
        return 3
    return 2


def probe_platform(
    platform_key: str,
    project_root: Optional[Path] = None,
    *,
    verify: bool = False,
    smoke_runner: Optional[Callable] = None,
) -> PlatformProbeResult:
    platform = get_platform(platform_key)
    binary = detect_binary(platform.worker_binary)
    capabilities = {
        name: ("detected" if advertised and binary.found and name == "fresh_session" else
               "advertised" if advertised else "unavailable")
        for name, advertised in platform.capabilities.items()
    }
    capabilities.update({
        "binary": "detected" if binary.found else "unavailable",
        "fresh_process": ("detected" if binary.found and binary.version_supported
                          else "degraded" if binary.found else "unavailable"),
        "native_subagent": ("advertised" if platform.capabilities.get("subagent")
                            else "unsupported"),
        "mcp": "advertised",
        "authentication": "unknown" if binary.found else "unavailable",
    })
    verification = {"entrypoint": "not-run", "hook": "not-run",
                    "worker": "not-run", "mcp": "not-run"}
    if project_root is not None:
        root = Path(project_root)
        verification["entrypoint"] = _verify_entrypoint(root, platform_key)
        if verify:
            verification["hook"] = _verify_hook(root, platform_key)
        else:
            hook_rel = adapter_descriptor(platform_key)["hook_config"]
            verification["hook"] = (
                "unsupported" if hook_rel is None else
                "detected" if (root / hook_rel).is_file() else "unavailable"
            )
    if verify and project_root is not None:
        root = Path(project_root)
        worker_state = "unavailable"
        if binary.found and binary.version_supported and platform.worker_binary:
            stored = load_platform_runtime_profile(root, platform_key)
            candidate = WorkerProfile(
                platform_key, FRESH_PROCESS, str(Path(binary.path).resolve()), stored.worker.args,
                stored.worker.timeout_seconds, False, "capability verification probe",
            )
            prompt = root / ".maika/runtime/worker-smoke-prompt.txt"
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text(
                "Read the project entrypoint without writing files and print exactly "
                "MAIKA_WORKER_SMOKE_OK. Do not create or modify files.\n",
                encoding="utf-8",
            )
            try:
                if smoke_runner is not None:
                    result = smoke_runner(candidate, prompt)
                else:
                    result = run_worker_smoke_test(candidate, prompt, project_root=root)
                worker_state = result.get("state", "degraded")
            finally:
                prompt.unlink(missing_ok=True)
        verification["worker"] = "verified" if worker_state == "verified" else worker_state
        if platform.capabilities.get("fresh_session"):
            capabilities["fresh_session"] = (
                "verified" if worker_state == "verified" else
                "degraded" if binary.found else "advertised"
            )
        capabilities["fresh_process"] = (
            "verified" if worker_state == "verified" else
            "degraded" if binary.found else "unavailable"
        )
        if platform.capabilities.get("write_gate_hook"):
            capabilities["write_gate_hook"] = (
                "verified" if verification["hook"] == "verified" else "degraded"
            )
        # Provider visibility is detected from config, but only an injected
        # provider smoke can promote it in a future adapter-specific verifier.
        verification["mcp"] = "not-run"
    tier = support_tier(verification)
    return PlatformProbeResult(
        platform=platform_key,
        binary=binary,
        # Binary presence is not authentication. No adapter exposes an auth probe
        # yet, so a present binary is "unknown", never "authenticated" (F5).
        authentication="unknown" if binary.found else "unavailable",
        capabilities=capabilities,
        verification=verification,
        support_tier=tier,
    )


def probe_and_persist(
    project_root: Path,
    platform_key: str,
    *,
    verify: bool = False,
    smoke_runner: Optional[Callable] = None,
) -> PlatformProbeResult:
    root = Path(project_root)
    result = probe_platform(platform_key, root, verify=verify, smoke_runner=smoke_runner)
    path = profile_path(root, platform_key)
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    data["detection"] = {
        "binary": {
            "path": result.binary.path,
            "version": result.binary.version,
            "found": result.binary.found,
            "version_supported": result.binary.version_supported,
        },
        "authentication": {"state": result.authentication},
        "last_detected_at": datetime.now(timezone.utc).isoformat(),
    }
    adapter_enabled = bool((data.get("adapter") or {}).get("enabled", True))
    entrypoint = "pass" if result.verification["entrypoint"] == "verified" else result.verification["entrypoint"]
    hook = "pass" if result.verification["hook"] == "verified" else result.verification["hook"]
    worker = ("pass" if result.verification["worker"] == "verified" else
              "fail" if result.verification["worker"] in {"degraded", "unavailable"} else
              result.verification["worker"])
    if verify:
        data["capabilities"] = dict(result.capabilities)
        verification = {
            "entrypoint_smoke_test": entrypoint,
            "hook_smoke_test": hook,
            "worker_smoke_test": worker,
            "mcp_smoke_test": result.verification["mcp"],
            "last_verified_at": datetime.now(timezone.utc).isoformat(),
        }
        if worker == "pass":
            identity = binary_identity(
                result.binary.path, version=result.binary.version,
            )
            if identity is None:
                verification["worker_smoke_test"] = "fail"
                data["capabilities"]["fresh_session"] = "degraded"
            else:
                verification["worker_binary"] = identity
                verification["verified_worker_profile_fingerprint"] = (
                    data.get("profile_fingerprint") or profile_fingerprint(data)
                )
    else:
        # A non-verifying probe re-detects the binary but must never erase or
        # downgrade prior verification evidence (F3): the worker/mcp smoke did not
        # run, so those and any verified capabilities are preserved.
        prior = data.get("verification") or {}
        prior_caps = data.get("capabilities") or {}
        caps = dict(result.capabilities)
        current_identity = binary_identity(
            result.binary.path, version=result.binary.version,
        )
        identity_unchanged = identities_match(prior.get("worker_binary"), current_identity)
        for name, state in prior_caps.items():
            if state == "verified" and identity_unchanged:
                caps[name] = "verified"
        data["capabilities"] = caps
        verification = {
            # entrypoint/hook presence is a live check and is refreshed; a prior
            # verified hook keeps its "pass" only while its config still exists.
            "entrypoint_smoke_test": entrypoint,
            "hook_smoke_test": "pass" if (prior.get("hook_smoke_test") == "pass"
                                          and hook != "unavailable") else hook,
            # worker/mcp smoke did not run: preserve the prior verification result.
            "worker_smoke_test": (prior.get("worker_smoke_test", "not-run")
                                  if identity_unchanged else "not-run"),
            "mcp_smoke_test": prior.get("mcp_smoke_test", result.verification["mcp"]),
            "last_verified_at": prior.get("last_verified_at") if identity_unchanged else None,
        }
        if identity_unchanged:
            for key in ("worker_binary", "verified_worker_profile_fingerprint"):
                if key in prior:
                    verification[key] = prior[key]
        elif prior.get("worker_smoke_test") == "pass":
            data["verification_invalidated_reason"] = "worker binary identity changed"
            caps["fresh_session"] = "degraded" if result.binary.found else "unavailable"
    verification["support_tier"] = _persisted_support_tier(verification, adapter_enabled)
    data["verification"] = verification
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return result


def _persisted_support_tier(verification: Mapping[str, str], adapter_enabled: bool) -> int:
    """Support tier from the persisted verification vocabulary (pass/fail/…)."""
    if not adapter_enabled:
        return 0
    if verification.get("entrypoint_smoke_test") != "pass":
        return 0
    if verification.get("hook_smoke_test") != "pass" or verification.get("worker_smoke_test") != "pass":
        return 1
    if verification.get("mcp_smoke_test") == "verified":
        return 3
    return 2
