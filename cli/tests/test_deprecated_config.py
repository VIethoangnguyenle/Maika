from pathlib import Path

import yaml

from cli.commands.doctor import build_setup_findings
from cli.commands.lifecycle import run_repair
from cli.commands.init import run_init
from cli.scaffold import load_resolved_config


REPO = Path(__file__).resolve().parents[2]


def test_old_hook_python_key_is_ignored_reported_and_repaired(tmp_path):
    run_init(str(tmp_path), str(REPO), "codex", [], "python", True)
    path = tmp_path / ".maika/resolved-config.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8"))
    doc["resolved"]["hook_python"] = "py -3"
    path.write_text(yaml.safe_dump(doc), encoding="utf-8")

    assert load_resolved_config(tmp_path)["platform"] == "codex"
    finding = {item["id"]: item for item in build_setup_findings(tmp_path)}["deprecated-config"]
    assert finding["ok"] is False
    assert "hook_python" in finding["evidence"]

    assert run_repair(str(tmp_path), "deprecated-config")["exit_code"] == 0
    assert "hook_python" not in load_resolved_config(tmp_path)
