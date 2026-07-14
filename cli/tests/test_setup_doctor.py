"""`maika doctor setup --target [--json]` — whole-adapter installation health.

Findings are machine-readable {id, severity, ok, evidence, remediation}; core
integrity failures set a non-zero exit code, advisory checks (host binaries,
worker strategy, legacy roots) never do.
"""

import json
from pathlib import Path

import pytest

from cli.commands.doctor import build_setup_findings, run_doctor_setup

REPO_ROOT = Path(__file__).resolve().parents[2]
_SEVERITIES = {"error", "warning", "info"}


def _init(target: Path, platform_key: str = "claude-code"):
    from cli.commands.init import run_init

    run_init(target_dir=str(target), maika_root=str(REPO_ROOT),
             platform_key=platform_key, selected_mcps=[], language="python",
             assume_yes=True)


def _by_id(findings):
    return {f["id"]: f for f in findings}


def test_findings_have_machine_readable_schema(tmp_path):
    _init(tmp_path)
    findings = build_setup_findings(tmp_path, maika_root=str(REPO_ROOT))
    assert findings
    for f in findings:
        assert set(f) >= {"id", "severity", "ok", "evidence", "remediation"}
        assert f["severity"] in _SEVERITIES
        assert isinstance(f["ok"], bool)


def test_fresh_init_core_checks_pass(tmp_path):
    _init(tmp_path)
    found = _by_id(build_setup_findings(tmp_path, maika_root=str(REPO_ROOT)))
    assert found["canonical-core"]["ok"]
    assert found["managed-entrypoint"]["ok"]
    assert found["native-hook"]["ok"]
    assert found["asset-bundle"]["ok"]


def test_flags_missing_managed_block(tmp_path):
    _init(tmp_path)
    entry = tmp_path / "CLAUDE.md"
    entry.write_text("# hand-written, no Maika block\n", encoding="utf-8")
    found = _by_id(build_setup_findings(tmp_path, maika_root=str(REPO_ROOT)))
    assert found["managed-entrypoint"]["ok"] is False
    assert found["managed-entrypoint"]["remediation"]


def test_missing_core_is_error_and_nonzero_exit(tmp_path, capsys):
    # empty dir — never init'd
    found = _by_id(build_setup_findings(tmp_path, maika_root=str(REPO_ROOT)))
    assert found["canonical-core"]["ok"] is False
    assert found["canonical-core"]["severity"] == "error"
    rc = run_doctor_setup(str(tmp_path), as_json=False)
    assert rc == 1


def test_json_output_is_parseable(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()  # discard init scaffold logs; doctor --json must emit pure JSON
    rc = run_doctor_setup(str(tmp_path), as_json=True)
    payload = json.loads(capsys.readouterr().out)
    assert rc == 0
    ids = {f["id"] for f in payload["findings"]}
    assert {"canonical-core", "managed-entrypoint", "native-hook", "asset-bundle"} <= ids


def test_worker_strategy_finding_is_advisory(tmp_path):
    # Host CLI absent in CI → worker unverified. The finding is advisory (never
    # severity "error", never a non-zero exit) but ok=False: no dispatchable
    # worker exists until `maika platform verify` runs (F2/F6). It must not
    # overclaim usability via a shadow inline fallback.
    _init(tmp_path)
    found = _by_id(build_setup_findings(tmp_path, maika_root=str(REPO_ROOT)))
    ws = found["worker-strategy"]
    assert ws["severity"] in {"info", "warning"}
    assert ws["severity"] != "error"
    assert ws["ok"] is False
    assert run_doctor_setup(str(tmp_path), as_json=False) == 0
