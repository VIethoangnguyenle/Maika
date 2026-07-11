"""Tests for canonical asset resolution used by self-contained installs.

`cli.assets` must resolve the Maika asset root (the directory carrying
`cli/plugin-manifest.yaml` and the `.maika/` runtime tree) across three tiers:
explicit `--source`, the bundled package assets, and a source checkout — and
must never silently accept an incomplete bundle.
"""

from pathlib import Path

import pytest

from cli import assets

REPO_ROOT = Path(__file__).resolve().parents[2]

# The consumed assets that are files (everything else in REQUIRED_ASSETS is a dir).
_FILE_ASSETS = {
    "cli/plugin-manifest.yaml",
    ".maika/agent/KERNEL.md",
    ".maika/knowledge/README.md",
}


def _make_bundle(root: Path, omit=()):
    """Materialize a complete (minus `omit`) fake asset bundle under root."""
    for rel in assets.REQUIRED_ASSETS:
        if rel in omit:
            continue
        path = root / rel
        if rel in _FILE_ASSETS:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("x", encoding="utf-8")
        else:
            path.mkdir(parents=True, exist_ok=True)
    return root


def test_validate_asset_bundle_complete_is_empty(tmp_path):
    _make_bundle(tmp_path)
    assert assets.validate_asset_bundle(tmp_path) == []


def test_validate_asset_bundle_reports_missing(tmp_path):
    _make_bundle(tmp_path, omit=(".maika/rules", ".maika/hooks"))
    missing = assets.validate_asset_bundle(tmp_path)
    assert ".maika/rules" in missing
    assert ".maika/hooks" in missing


def test_asset_root_uses_explicit_source(tmp_path):
    _make_bundle(tmp_path)
    assert assets.asset_root(str(tmp_path)) == tmp_path.resolve()


def test_asset_root_rejects_incomplete_explicit_source(tmp_path):
    _make_bundle(tmp_path, omit=(".maika/skills",))
    with pytest.raises(FileNotFoundError, match=r"\.maika/skills"):
        assets.asset_root(str(tmp_path))


def test_asset_root_falls_back_to_source_checkout():
    # No explicit source and (running from a checkout) no bundled _assets → the
    # repo checkout root, which carries every consumed asset.
    root = assets.asset_root()
    assert (root / ".maika").is_dir()
    assert assets.validate_asset_bundle(root) == []


def test_load_asset_manifest_reads_plugins():
    manifest = assets.load_asset_manifest(REPO_ROOT)
    assert manifest["plugins"]
    assert "mcp_capabilities" in manifest
