import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "capability.py"
spec = importlib.util.spec_from_file_location("capability", MOD)
cap = importlib.util.module_from_spec(spec)
spec.loader.exec_module(cap)


def test_parse_list_projects_skips_log_line():
    # Real cbm output: a log line, then the JSON on the last line.
    out = (
        "level=info msg=mem.init budget_mb=11712\n"
        '{"projects":[{"name":"home-zane-myapp","root_path":"/home/zane/myapp","nodes":42}]}\n'
    )
    projs = cap._parse_list_projects(out)
    assert projs == [{"name": "home-zane-myapp", "root_path": "/home/zane/myapp"}]


def test_parse_list_projects_empty():
    out = 'level=info msg=x\n{"projects":[],"hint":"No projects indexed."}\n'
    assert cap._parse_list_projects(out) == []


def test_parse_list_projects_drops_entries_without_root():
    out = '{"projects":[{"name":"noroot"},{"name":"ok","root_path":"/r"}]}'
    assert cap._parse_list_projects(out) == [{"name": "ok", "root_path": "/r"}]


def test_ua_indexed_projects_detects_graph(tmp_path):
    root = tmp_path / "proj"
    (root / ".understand-anything").mkdir(parents=True)
    (root / ".understand-anything" / "knowledge-graph.json").write_text("{}")
    (tmp_path / "nograph").mkdir()
    got = cap.ua_indexed_projects([str(root), str(tmp_path / "nograph")])
    assert got == [{"name": "proj", "root_path": str(root)}]


def test_parse_snippet_real_node():
    out = (
        "level=info msg=x\n"
        '{"name":"scaffold_plugin","qualified_name":"proj.cli.scaffold.scaffold_plugin",'
        '"file_path":"/abs/cli/scaffold.py","start_line":167}\n'
    )
    d = cap._parse_snippet(out)
    assert d["qualified_name"] == "proj.cli.scaffold.scaffold_plugin"
    assert d["file_path"] == "/abs/cli/scaffold.py"


def test_parse_snippet_fabricated_returns_none():
    # cbm prints nothing (or a non-JSON log line) for a nonexistent node.
    assert cap._parse_snippet("level=info msg=x\n") is None
