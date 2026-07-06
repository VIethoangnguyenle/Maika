import importlib.util
from pathlib import Path

CLI = Path(__file__).resolve().parents[1] / "cli.py"
spec = importlib.util.spec_from_file_location("gate_cli", CLI)
cli = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cli)

INDEX = """\
entries:
  - id: SP-6
    applies_to: [java-service]
  - id: HP-1
    applies_to: []
  - id: RC-2
    applies_to: [react-component]
"""

# Index không có global rule và không có entry nào cho java-service.
INDEX_NO_MATCH = """\
entries:
  - id: RC-2
    applies_to: [react-component]
"""

HANDOFF = "## Applicable DNA/Conventions\n- SP-6\n## Allowed Files\n- src/App.java\n"


def _write(tmp_path, name, content):
    p = tmp_path / name
    p.write_text(content, encoding="utf-8")
    return str(p)


def test_load_index_includes_global_rules_for_artifact_type(tmp_path):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    ids, empty = cli._load_index_rule_ids(idx, "java-service")
    assert ids == {"SP-6", "HP-1"}  # HP-1 global (applies_to rỗng) phải nằm trong slice
    assert empty is False


def test_load_index_without_artifact_type_returns_all(tmp_path):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    ids, empty = cli._load_index_rule_ids(idx, None)
    assert ids == {"SP-6", "HP-1", "RC-2"}
    assert empty is False


def test_cli_handoff_slice_strict_pass(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    handoff = _write(tmp_path, "TASK_HANDOFF.node-1.md", HANDOFF)
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 0
    assert "PASS" in capsys.readouterr().out


def test_cli_handoff_slice_strict_fail_wrong_type(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    handoff = _write(
        tmp_path, "TASK_HANDOFF.node-1.md",
        "## Applicable DNA/Conventions\n- SP-6\n- RC-2\n",
    )
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 1
    assert "RC-2" in capsys.readouterr().out


def test_cli_empty_slice_falls_back_to_legacy_with_warn(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX_NO_MATCH)
    handoff = _write(tmp_path, "TASK_HANDOFF.node-1.md", HANDOFF)
    rc = cli.main(["handoff-slice", handoff, "--index", idx, "--artifact-type", "java-service"])
    out = capsys.readouterr().out
    assert rc == 0          # legacy: ≥1 rule-id là đủ
    assert "WARN" in out    # nhưng phải cảnh báo slice rỗng


def test_cli_legacy_mode_without_index(tmp_path, capsys):
    handoff = _write(
        tmp_path, "TASK_HANDOFF.node-1.md",
        "## Applicable DNA/Conventions\n- XX-99\n",
    )
    rc = cli.main(["handoff-slice", handoff])
    assert rc == 0  # không --index → behavior cũ giữ nguyên


def test_cli_implementation_context_strict_fail_nonexistent(tmp_path, capsys):
    idx = _write(tmp_path, "knowledge-index.yaml", INDEX)
    impl = _write(
        tmp_path, "IMPLEMENTATION_CONTEXT.md",
        "## Applicable DNA/Conventions\n- XX-99\n"
        "## Evidence\ndomain_overview: user service\n"
        "node_id: svc.User#1\nblast-radius: 2 nodes\n"
        "## Allowed Files\n- src/App.java\n",
    )
    rc = cli.main(["implementation-context", impl, "--index", idx, "--artifact-type", "java-service"])
    assert rc == 1
    assert "XX-99" in capsys.readouterr().out
