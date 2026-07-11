"""Typed advertise → detect → verify pipeline for host adapters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from typing import Callable, Mapping, Optional

import yaml

from cli.config.platforms import adapter_descriptor
from cli.platforms import get_platform
from cli.runtime.platform_profile import load_platform_runtime_profile, profile_path
from cli.runtime.worker_resolver import FRESH_PROCESS, WorkerProfile, run_worker_smoke_test


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
        return BinaryProbe(name, True, path, raw or None, proc.returncode == 0)
    except (OSError, subprocess.TimeoutExpired):
        return BinaryProbe(name, True, path, None, False)


def _verify_entrypoint(project_root: Path, platform_key: str) -> str:
    path = project_root / adapter_descriptor(platform_key)["entrypoint"]
    return "verified" if path.is_file() and path.stat().st_size > 0 else "unavailable"


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
    evaluator = project_root / ".maika/hooks/write-gate/write_gate.py"
    if not evaluator.is_file():
        return "unavailable"
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location("maika_hook_smoke", evaluator)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        decision = module.evaluate_write(project_root, Path("README.md"), ".maika")
    except Exception:
        return "degraded"
    return "verified" if getattr(decision, "ok", False) else "degraded"


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
        name: ("detected" if advertised and binary.found else
               "advertised" if advertised else "unavailable")
        for name, advertised in platform.capabilities.items()
    }
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
                platform_key, FRESH_PROCESS, stored.worker.executable, stored.worker.args,
                stored.worker.timeout_seconds, False, "capability verification probe",
            )
            prompt = root / ".maika/runtime/worker-smoke-prompt.txt"
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text(
                "Read the project entrypoint without writing files and return a structured OK response.\n",
                encoding="utf-8",
            )
            try:
                result = (smoke_runner or run_worker_smoke_test)(candidate, prompt)
                worker_state = result.get("state", "degraded")
            finally:
                prompt.unlink(missing_ok=True)
        verification["worker"] = "verified" if worker_state == "verified" else worker_state
        if platform.capabilities.get("fresh_session"):
            capabilities["fresh_session"] = (
                "verified" if worker_state == "verified" else
                "degraded" if binary.found else "advertised"
            )
        # Provider visibility is detected from config, but only an injected
        # provider smoke can promote it in a future adapter-specific verifier.
        verification["mcp"] = "detected" if platform.capabilities else "unsupported"
    tier = support_tier(verification)
    return PlatformProbeResult(
        platform=platform_key,
        binary=binary,
        authentication="detected" if binary.found else "unavailable",
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
    data["capabilities"] = dict(result.capabilities)
    data["verification"] = {
        "entrypoint_smoke_test": "pass" if result.verification["entrypoint"] == "verified" else result.verification["entrypoint"],
        "hook_smoke_test": "pass" if result.verification["hook"] == "verified" else result.verification["hook"],
        "worker_smoke_test": "pass" if result.verification["worker"] == "verified" else
                             "fail" if result.verification["worker"] in {"degraded", "unavailable"} else result.verification["worker"],
        "mcp_smoke_test": result.verification["mcp"],
        "support_tier": result.support_tier,
        "last_verified_at": datetime.now(timezone.utc).isoformat() if verify else None,
    }
    path.write_text(yaml.safe_dump(data, sort_keys=False, allow_unicode=True), encoding="utf-8")
    return result
