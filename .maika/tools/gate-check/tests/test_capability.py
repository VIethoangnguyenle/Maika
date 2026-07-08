import importlib.util
import json
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


class _FakeProc:
    def __init__(self, stdout):
        self.stdout = stdout


def test_verify_nodes_real_and_fabricated(monkeypatch):
    def fake_run(cmd, **kw):
        payload = json.loads(cmd[3])
        qn = payload["qualified_name"]
        if qn == "proj.cli.a.Foo":
            return _FakeProc('{"qualified_name":"proj.cli.a.Foo","file_path":"/repo/cli/a.py"}')
        return _FakeProc("")  # nonexistent → cbm prints nothing
    monkeypatch.setattr(cap.subprocess, "run", fake_run)
    verified, ok = cap.verify_nodes(["proj.cli.a.Foo", "proj.cli.Fake.nope"])
    assert ok is True
    assert verified == {"proj.cli.a.Foo": "/repo/cli/a.py"}


def test_verify_nodes_probe_unavailable(monkeypatch):
    def boom(cmd, **kw):
        raise OSError("binary not found")
    monkeypatch.setattr(cap.subprocess, "run", boom)
    verified, ok = cap.verify_nodes(["proj.cli.a.Foo"])
    assert ok is False and verified == {}


def test_changed_java_files_in_tmp_git_repo(tmp_path):
    import subprocess
    def git(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "A.java").write_text("class A {}\n")
    (tmp_path / "x.py").write_text("pass\n")
    git("add", "."); git("commit", "-q", "-m", "init")
    (tmp_path / "A.java").write_text("class A { int x; }\n")   # modified
    (tmp_path / "B.java").write_text("class B {}\n")           # untracked
    (tmp_path / "x.py").write_text("pass  # changed\n")        # non-java: ignored
    files = cap.changed_java_files(str(tmp_path))
    names = sorted(p.rsplit("/", 1)[-1] for p in files)
    assert names == ["A.java", "B.java"]


def test_changed_java_files_none_outside_git(tmp_path):
    sub = tmp_path / "not-a-repo"; sub.mkdir()
    assert cap.changed_java_files(str(sub)) is None


def test_changed_java_files_from_subdir_resolves_repo_top(tmp_path):
    import subprocess
    def git(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "A.java").write_text("class A {}\n")
    sub = tmp_path / "sub"; sub.mkdir()
    (sub / "keep.txt").write_text("x\n")
    git("add", "."); git("commit", "-q", "-m", "init")
    (tmp_path / "A.java").write_text("class A { int x; }\n")   # modified at top
    files = cap.changed_java_files(str(sub))                    # called from SUBDIR
    assert files is not None and len(files) == 1
    import os
    assert os.path.isfile(files[0]) and files[0].endswith("A.java")


def test_changed_java_files_excludes_deleted(tmp_path):
    import subprocess, os
    def git(*a):
        subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", *a],
                       cwd=tmp_path, check=True, capture_output=True)
    git("init", "-q")
    (tmp_path / "Gone.java").write_text("class Gone {}\n")
    (tmp_path / "Stay.java").write_text("class Stay {}\n")
    git("add", "."); git("commit", "-q", "-m", "init")
    os.remove(tmp_path / "Gone.java")                           # deleted tracked
    (tmp_path / "Stay.java").write_text("class Stay { int x; }\n")
    files = cap.changed_java_files(str(tmp_path))
    names = [p.rsplit("/", 1)[-1] for p in files]
    assert names == ["Stay.java"]
