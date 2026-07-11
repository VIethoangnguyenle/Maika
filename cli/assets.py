"""Canonical asset resolution for self-contained (wheel/pipx/uvx) installs.

The Maika CLI scaffolds a project from an *asset root* — the directory that
carries `cli/plugin-manifest.yaml` and the `.maika/` runtime asset tree. In a
source checkout that root is the repo itself; in a wheel it is a bundle staged
into the installed package at build time (see setup.py).

Resolution order (`asset_root`):

  1. an explicit source path — framework development, `maika init --source`;
  2. the bundled package assets (`cli/_assets`), present in wheel installs;
  3. a source-tree checkout, when running from a repo clone.

A resolved root is never used unless it is complete: an incomplete bundle
raises with the concrete list of missing assets instead of silently
scaffolding a broken project.
"""

from __future__ import annotations

from importlib import resources
from pathlib import Path
from typing import List, Optional

from cli.scaffold import load_manifest

# Directory inside the installed `cli` package where the build step stages the
# canonical asset tree (`.maika/` + `cli/plugin-manifest.yaml`).
_BUNDLE_DIRNAME = "_assets"

# Runtime assets scaffold actually consumes (relative to an asset root). Missing
# any of these means the bundle cannot scaffold a project — fail loudly. Kept in
# sync with cli/plugin-manifest.yaml plugin sources and cli.scaffold.SOURCE_MAP.
REQUIRED_ASSETS = (
    "cli/plugin-manifest.yaml",
    ".maika/agent/KERNEL.md",
    ".maika/rules",
    ".maika/skills",
    ".maika/workflows",
    ".maika/procedures",
    ".maika/profiles",
    ".maika/config/artifact-registry.yaml",
    ".maika/tools",
    ".maika/hooks",
    ".maika/knowledge/templates",
    ".maika/knowledge/active",
    ".maika/knowledge/long-term",
    ".maika/knowledge/README.md",
    ".maika/knowledge/skill-evolution",
)


def validate_asset_bundle(root: Path) -> List[str]:
    """Return the REQUIRED_ASSETS missing under `root` (empty list == complete)."""
    return [rel for rel in REQUIRED_ASSETS if not (root / rel).exists()]


def _require_complete(root: Path, origin: str) -> None:
    missing = validate_asset_bundle(root)
    if missing:
        raise FileNotFoundError(
            f"incomplete Maika asset bundle ({origin}); missing: {', '.join(missing)}"
        )


def _bundled_root() -> Optional[Path]:
    """The staged package bundle, or None when running from a source checkout."""
    try:
        root = Path(str(resources.files("cli") / _BUNDLE_DIRNAME))
    except (ModuleNotFoundError, AttributeError, TypeError):
        return None
    return root if root.is_dir() else None


def _source_checkout_root() -> Path:
    # cli/assets.py -> cli/ -> repo root
    return Path(__file__).resolve().parent.parent


def asset_root(explicit_source: Optional[str] = None) -> Path:
    """Resolve the canonical asset root. See the module docstring for the tiers."""
    if explicit_source:
        root = Path(explicit_source).resolve()
        _require_complete(root, origin=f"--source {explicit_source}")
        return root

    bundled = _bundled_root()
    if bundled is not None:
        _require_complete(bundled, origin="installed package assets")
        return bundled

    checkout = _source_checkout_root()
    _require_complete(checkout, origin=f"source checkout {checkout}")
    return checkout


def load_asset_manifest(root: Optional[Path] = None) -> dict:
    """Load the plugin manifest from the resolved (or given) asset root."""
    return load_manifest(root if root is not None else asset_root())
