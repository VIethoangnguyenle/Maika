"""Per-platform adapter descriptors + install records.

`platforms.yaml` captures each enabled adapter's descriptor (entrypoint, native
hook config, hook strategy); `install-manifest.yaml` records the exact
repo-relative files each adapter installed, so disable removes precisely them.
"""

from __future__ import annotations

from pathlib import Path
from typing import List, Optional

import yaml

from cli.platforms import get_platform

# Native host hook-config path per platform (mirrors the requires_platform hook
# plugins in cli/plugin-manifest.yaml). None → the host has no native hook file.
_HOOK_CONFIG = {
    "antigravity": ".agents/hooks.json",
    "codex": ".codex/hooks.json",
    "claude-code": ".claude/settings.json",
    "generic": None,
}

_PLATFORMS_REL = "config/platforms.yaml"
_MANIFEST_REL = "config/install-manifest.yaml"


def adapter_descriptor(platform_key: str) -> dict:
    """Entrypoint + native hook config for a platform's adapter."""
    return {
        "entrypoint": get_platform(platform_key).config_entry_point,
        "hook_config": _HOOK_CONFIG.get(platform_key),
    }


def adapter_files(platform_key: str) -> List[str]:
    descriptor = adapter_descriptor(platform_key)
    files = [descriptor["entrypoint"]]
    if descriptor["hook_config"]:
        files.append(descriptor["hook_config"])
    return files


def write_platforms_config(target, enabled: List[str]) -> None:
    path = Path(target) / ".maika" / _PLATFORMS_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "version": 1,
        "platforms": {
            key: {**adapter_descriptor(key), "hook_strategy": "native"}
            for key in enabled
        },
    }
    path.write_text(
        "# Maika platform adapters\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _load_manifest(target) -> dict:
    path = Path(target) / ".maika" / _MANIFEST_REL
    if path.exists():
        return yaml.safe_load(path.read_text(encoding="utf-8")) or {"version": 1, "adapters": {}}
    return {"version": 1, "adapters": {}}


def _save_manifest(target, data: dict) -> None:
    path = Path(target) / ".maika" / _MANIFEST_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Maika install manifest\n"
        + yaml.safe_dump(data, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def record_install(target, platform_key: str, files: List[str]) -> None:
    data = _load_manifest(target)
    data.setdefault("adapters", {})[platform_key] = sorted(set(files))
    _save_manifest(target, data)


def installed_files(target, platform_key: str) -> List[str]:
    return _load_manifest(target).get("adapters", {}).get(platform_key, [])


def remove_install(target, platform_key: str) -> None:
    data = _load_manifest(target)
    data.get("adapters", {}).pop(platform_key, None)
    _save_manifest(target, data)
