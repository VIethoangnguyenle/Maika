"""Static guards for the Windows bootstrap script (install.ps1)."""

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
PS1 = REPO_ROOT / "install.ps1"


def test_install_ps1_exists():
    assert PS1.exists(), "install.ps1 missing at repo root"


@pytest.fixture
def ps1_text():
    return PS1.read_text(encoding="utf-8")


def test_uses_windows_venv_layout(ps1_text):
    # Windows venv puts executables under Scripts\, never bin/.
    assert r"Scripts\python.exe" in ps1_text
    assert "/bin/" not in ps1_text and r"\bin\python" not in ps1_text


def test_routes_init_and_update(ps1_text):
    assert "cli.maika init" in ps1_text
    assert "cli.maika update" in ps1_text


def test_checks_all_resolved_config_roots(ps1_text):
    # Mirror install.sh: .agents, .claude, .maika resolved-config.yaml
    for root in (".agents", ".claude", ".maika"):
        assert f"{root}\\resolved-config.yaml" in ps1_text


def test_installs_dependency_floors(ps1_text):
    assert "jinja2>=3.1" in ps1_text
    assert "pyyaml>=6.0" in ps1_text
