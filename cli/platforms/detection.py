"""Host platform detection — binary presence, version, and capability states.

Separates *advertised* (the adapter declares it) from *detected* (the host
binary is present). Detection NEVER emits ``verified`` — verification requires a
successful smoke path, which is a separate, more expensive step.
"""

from __future__ import annotations

import shutil
import subprocess

ADVERTISED = "advertised"
DETECTED = "detected"
UNAVAILABLE = "unavailable"


def detect_binary(name: str) -> dict:
    """Locate a CLI binary on PATH (shutil.which — no execution)."""
    path = shutil.which(name) if name else None
    return {"found": path is not None, "path": path, "name": name}


def probe_version(argv, timeout: int = 5) -> dict:
    """Run a version probe with argv + shell=False + timeout. Never raises."""
    try:
        proc = subprocess.run(
            argv, capture_output=True, text=True, timeout=timeout, check=False,
        )
    except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
        return {"ok": False, "raw": "", "returncode": None}
    raw = (proc.stdout or proc.stderr or "").strip()
    return {"ok": proc.returncode == 0, "raw": raw, "returncode": proc.returncode}


def detect_platform(platform) -> dict:
    """Detect one platform's host binary + advertised/detected capability states."""
    binary_name = platform.worker_binary
    binary = detect_binary(binary_name) if binary_name else {"found": False, "path": None, "name": None}
    version = {"ok": False, "raw": "", "returncode": None}
    if binary["found"]:
        version = probe_version([binary_name, "--version"])

    capabilities = {}
    for cap, advertised in platform.capabilities.items():
        if not advertised:
            capabilities[cap] = UNAVAILABLE
        elif binary["found"]:
            capabilities[cap] = DETECTED
        else:
            capabilities[cap] = ADVERTISED

    return {
        "platform": platform.name,
        "binary": binary,
        "version": version,
        "capabilities": capabilities,
    }
