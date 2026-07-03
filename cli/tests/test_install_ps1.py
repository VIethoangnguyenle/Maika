"""Static guards for the Windows bootstrap script (install.ps1)."""

import re
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


def test_checks_scaffold_exit_code(ps1_text):
    # LASTEXITCODE must be checked right AFTER each scaffold invocation, not just elsewhere.
    for verb in ("init", "update"):
        marker = f"cli.maika {verb}"
        assert marker in ps1_text
        pos = ps1_text.index(marker)
        assert "LASTEXITCODE" in ps1_text[pos:pos + 200], f"No LASTEXITCODE check near {marker}"


def test_passes_hook_python_launcher(ps1_text):
    # The resolved launcher must flow into scaffolding so the Windows hook uses it.
    assert "--hook-python" in ps1_text
    assert "$HookPython" in ps1_text


def test_native_calls_are_exit_checked(ps1_text):
    # PS 5.1: $ErrorActionPreference='Stop' does NOT cover native exit codes.
    assert "function Assert-NativeExit" in ps1_text
    # venv creation + pip upgrade + pip floors + pip -e = 4 guarded call sites.
    assert ps1_text.count("Assert-NativeExit") >= 5


def test_failed_venv_bootstrap_is_cleaned_up(ps1_text):
    # A half-built venv must not survive to poison the next run.
    assert "Remove-Item -Recurse -Force -LiteralPath $Venv" in ps1_text


def test_python_floor_matches_pyproject(ps1_text):
    pyproject = (REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    floor = re.search(r'requires-python\s*=\s*">=(\d+\.\d+)"', pyproject).group(1)
    assert f"[version]'{floor}'" in ps1_text, f"install.ps1 floor must be {floor}"
    assert "[version]'3.8'" not in ps1_text
    sh_text = (REPO_ROOT / "install.sh").read_text(encoding="utf-8")
    assert floor in sh_text, f"install.sh must enforce Python >= {floor}"


def test_pyyaml_hint_uses_resolved_launcher(ps1_text):
    # `py -3` boxes must not be told to run bare `py -m pip ...`.
    assert "Run: $HookPython -m pip" in ps1_text


def test_pyyaml_auto_remediation(ps1_text):
    # Clean boxes get pyyaml installed (announced, --user); warn only on failure.
    assert "pip install --user --quiet pyyaml" in ps1_text
    # Re-check after the attempted install (two import probes total).
    assert ps1_text.count('-c "import yaml"') >= 2


def test_path_write_is_registry_safe(ps1_text):
    # SetEnvironmentVariable flattens REG_EXPAND_SZ -> REG_SZ and writes back
    # the EXPANDED value, hardcoding other tools' %VAR% PATH entries.
    assert "SetEnvironmentVariable" not in ps1_text
    assert "GetEnvironmentVariable" not in ps1_text
    assert "DoNotExpandEnvironmentNames" in ps1_text
    assert "GetValueKind" in ps1_text


def test_shim_handles_non_ascii_paths(ps1_text):
    # -Encoding ASCII mangles paths like C:\Users\Viet\ into '?' - the shim
    # must fall back to the 8.3 short path (pure ASCII by construction).
    assert "ShortPath" in ps1_text
    assert "[^\\x00-\\x7F]" in ps1_text
