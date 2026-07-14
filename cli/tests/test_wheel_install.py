"""Wheel-install end-to-end.

Builds a wheel, checks it bundles every consumed runtime asset (and no
framework-only tests/caches/local state), installs it into a clean venv,
scaffolds a project with the source checkout hidden from the subprocess, and
proves the bundle and the source checkout scaffold an equivalent tree.

These tests shell out to pip/venv; they are the W1 packaging gate and are
naturally slower than the unit suite.
"""

import shutil
import subprocess
import sys
import venv
import zipfile
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]


def _run(cmd, **kw):
    # Decode subprocess output as utf-8 explicitly — on Windows the default
    # locale codec (cp1252) chokes on the Maika banner's non-ASCII bytes in the
    # capture reader thread (PytestUnhandledThreadExceptionWarning).
    kw.setdefault("encoding", "utf-8")
    kw.setdefault("errors", "replace")
    return subprocess.run(cmd, check=True, capture_output=True, text=True, **kw)


def _tree(root: Path):
    """Relative-path set of every file/dir under root (the scaffold snapshot)."""
    return {str(p.relative_to(root).as_posix()) + ("/" if p.is_dir() else "")
            for p in root.rglob("*")}


@pytest.fixture(scope="module")
def wheel(tmp_path_factory):
    dest = tmp_path_factory.mktemp("wheelhouse")
    # Build from a clean state — a stale build/ tree (copied by pip into its
    # temp build dir) would ship packages the current config excludes.
    for stale in ("build", "maika_cli.egg-info"):
        shutil.rmtree(REPO_ROOT / stale, ignore_errors=True)
    _run([
        sys.executable, "-m", "pip", "wheel", str(REPO_ROOT),
        "--no-deps", "--no-build-isolation", "-w", str(dest),
    ])
    wheels = list(dest.glob("maika_cli-*.whl"))
    assert len(wheels) == 1, f"expected exactly one wheel, got {wheels}"
    return wheels[0]


@pytest.fixture(scope="module")
def installed_maika(wheel, tmp_path_factory):
    """A clean venv with the wheel installed (no deps, no index). Returns the
    `maika` entry-point path."""
    venv_dir = tmp_path_factory.mktemp("venv")
    venv.create(venv_dir, system_site_packages=True, with_pip=True)
    bin_dir = venv_dir / ("Scripts" if sys.platform == "win32" else "bin")
    pip = bin_dir / "pip"
    _run([str(pip), "install", "--no-deps", "--no-index", str(wheel)])
    return bin_dir / ("maika.exe" if sys.platform == "win32" else "maika")


def test_wheel_bundles_consumed_assets_without_tests(wheel):
    names = zipfile.ZipFile(wheel).namelist()

    # Canonical asset tree is present and self-contained.
    assert "cli/_assets/cli/plugin-manifest.yaml" in names
    for consumed in (
        "cli/_assets/.maika/rules/",
        "cli/_assets/.maika/skills/",
        "cli/_assets/.maika/hooks/",
        "cli/_assets/.maika/tools/",
        "cli/_assets/.maika/procedures/",
        "cli/_assets/.maika/profiles/",
        "cli/_assets/.maika/workflows/",
        "cli/_assets/.maika/knowledge/templates/",
    ):
        assert any(n.startswith(consumed) for n in names), f"missing {consumed}"
    assert any(n == "cli/_assets/.maika/agent/KERNEL.md" for n in names)

    # No framework-only tests, caches, or dev-local knowledge state.
    assert not any("_assets/" in n and "/tests/" in n for n in names)
    assert not any(n.startswith("cli/tests/") for n in names)
    assert not any(n.endswith(".pyc") for n in names)
    assert not any(n.endswith("knowledge/long-term/persona.yaml") for n in names)


def test_wheel_init_works_without_source_checkout(installed_maika, tmp_path):
    project = tmp_path / "proj"
    project.mkdir()
    # cwd is the empty project (never the repo) so the source checkout is not
    # importable — init must succeed purely from the packaged bundle.
    result = subprocess.run(
        [str(installed_maika), "init", "--target", str(project),
         "--platform", "codex", "--language", "python", "--yes"],
        cwd=str(project), check=False, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (project / ".maika").is_dir()
    assert (project / "AGENTS.md").exists()
    assert (project / ".codex" / "hooks.json").exists()
    assert (project / ".maika" / "resolved-config.yaml").exists()


def test_bundle_and_source_scaffold_are_equivalent(installed_maika, tmp_path):
    """Same installed CLI, same args → the bundled assets and an explicit
    --source checkout produce an identical scaffold tree (W1 changes only the
    asset source, never the output)."""
    from_bundle = tmp_path / "bundle"
    from_source = tmp_path / "source"
    from_bundle.mkdir()
    from_source.mkdir()

    base = ["init", "--platform", "codex", "--language", "python", "--yes"]
    _run([str(installed_maika), *base, "--target", str(from_bundle)],
         cwd=str(from_bundle))
    _run([str(installed_maika), *base, "--target", str(from_source),
          "--source", str(REPO_ROOT)], cwd=str(from_source))

    assert _tree(from_bundle) == _tree(from_source)
    assert ((from_bundle / "AGENTS.md").read_text(encoding="utf-8")
            == (from_source / "AGENTS.md").read_text(encoding="utf-8"))
