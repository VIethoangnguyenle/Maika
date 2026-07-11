"""Canonical project config: `.maika/config/project.yaml`.

Holds the enabled host adapters and the primary host over one `.maika` core.
Pure dict mutators (enable/disable/set_primary) keep the command layer thin.
"""

from __future__ import annotations

import copy
from pathlib import Path

import yaml

CORE_ROOT = ".maika"
_CONFIG_REL = "config/project.yaml"


def _default() -> dict:
    return {
        "version": 1,
        "framework": {"core_root": CORE_ROOT},
        "platforms": {"enabled": [], "primary": None},
    }


def config_path(target, core_root: str = CORE_ROOT) -> Path:
    return Path(target) / core_root / _CONFIG_REL


def load(target) -> dict:
    path = config_path(target)
    if not path.exists():
        return _default()
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    data.setdefault("version", 1)
    data.setdefault("framework", {}).setdefault("core_root", CORE_ROOT)
    platforms = data.setdefault("platforms", {})
    platforms.setdefault("enabled", [])
    platforms.setdefault("primary", None)
    return data


def save(target, cfg: dict) -> None:
    path = config_path(target)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "# Maika canonical project config\n"
        + yaml.safe_dump(cfg, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def enable(cfg: dict, platform: str) -> dict:
    cfg = copy.deepcopy(cfg)
    enabled = cfg["platforms"]["enabled"]
    if platform not in enabled:
        enabled.append(platform)
    if cfg["platforms"]["primary"] is None:
        cfg["platforms"]["primary"] = platform
    return cfg


def disable(cfg: dict, platform: str) -> dict:
    cfg = copy.deepcopy(cfg)
    enabled = cfg["platforms"]["enabled"]
    if platform in enabled:
        enabled.remove(platform)
    if cfg["platforms"]["primary"] == platform:
        cfg["platforms"]["primary"] = enabled[0] if enabled else None
    return cfg


def set_primary(cfg: dict, platform: str) -> dict:
    if platform not in cfg["platforms"]["enabled"]:
        raise ValueError(f"platform not enabled: {platform}")
    cfg = copy.deepcopy(cfg)
    cfg["platforms"]["primary"] = platform
    return cfg
