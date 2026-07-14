"""Build shim: stage the canonical Maika asset tree into the wheel.

Project metadata lives in pyproject.toml. This file exists only to bundle the
runtime assets — `.maika/` plus `cli/plugin-manifest.yaml` — into the installed
package at build time, so wheel/pipx/uvx installs can scaffold a project
without a Maika source checkout.

Single source of truth: the bundle under `cli/_assets/` is generated during the
build (into the build tree, never the source tree) — there is no second,
hand-maintained asset copy to keep in sync.
"""

import shutil
from pathlib import Path

from setuptools import setup
from setuptools.command.build_py import build_py

HERE = Path(__file__).parent.resolve()

# Mirrors cli.renderer's scaffold exclusions: framework-only tests, caches, VCS,
# and per-project instance/build artifacts (never shipped as framework assets).
_EXCLUDE_DIRS = {"__pycache__", ".pytest_cache", ".git", "tests"}
_EXCLUDE_NAMES = {"persona.yaml", "rules.json"}


def _skip(rel: Path) -> bool:
    if set(rel.parts) & _EXCLUDE_DIRS:
        return True
    if rel.name in _EXCLUDE_NAMES:
        return True
    if rel.suffix == ".pyc" or rel.name.endswith(".generated.xml"):
        return True
    return False


def _stage_assets(dest_cli: Path) -> None:
    bundle = dest_cli / "_assets"
    if bundle.exists():
        shutil.rmtree(bundle)
    for item in (HERE / ".maika").rglob("*"):
        rel = item.relative_to(HERE)  # ".maika/..."
        if _skip(rel):
            continue
        if item.is_dir():
            (bundle / rel).mkdir(parents=True, exist_ok=True)
        else:
            (bundle / rel).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, bundle / rel)
    manifest_dest = bundle / "cli" / "plugin-manifest.yaml"
    manifest_dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(HERE / "cli" / "plugin-manifest.yaml", manifest_dest)


class BuildPyWithAssets(build_py):
    def run(self):
        super().run()
        _stage_assets(Path(self.build_lib) / "cli")


setup(cmdclass={"build_py": BuildPyWithAssets})
