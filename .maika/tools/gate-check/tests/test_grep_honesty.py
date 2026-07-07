import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

# indexed_projects: list of {"name","root_path"} — as returned by a cbm/UA probe.
CUR = [{"name": "myapp", "root_path": "/home/zane/myapp"}]
CUR_UP = [
    {"name": "myapp", "root_path": "/home/zane/myapp"},
    {"name": "libcore", "root_path": "/home/zane/libcore"},  # upstream dep
]


def test_grep_on_indexed_current_repo_file_fails():
    # Agent claims grep-fallback but the file it explored belongs to an indexed project.
    text = (
        "## Evidence\n"
        "cbm unavailable — grep fallback, MEDIUM\n"
        "Found handler in cli/platforms/base.py:100\n"
    )
    res = g.validate_grep_honesty(text, indexed_projects=CUR, repo_root="/home/zane/myapp")
    assert res.ok is False
    assert "myapp" in res.reason


def test_grep_on_upstream_indexed_file_fails():
    # Upstream file referenced by absolute path; upstream project IS indexed → lazy grep.
    text = (
        "## Evidence\n"
        "UA unavailable — grep fallback, MEDIUM\n"
        "auth logic at /home/zane/libcore/auth.py:42\n"
    )
    res = g.validate_grep_honesty(text, indexed_projects=CUR_UP, repo_root="/home/zane/myapp")
    assert res.ok is False
    assert "libcore" in res.reason


def test_grep_on_unindexed_file_passes():
    # File belongs to no indexed project (upstream not indexed yet) → grep is legit.
    text = (
        "## Evidence\n"
        "cbm unavailable — grep fallback, MEDIUM\n"
        "seen in /home/zane/newdep/x.py:7\n"
    )
    res = g.validate_grep_honesty(text, indexed_projects=CUR_UP, repo_root="/home/zane/myapp")
    assert res.ok is True


def test_no_grep_claim_passes():
    # Real cbm evidence, no grep-fallback → nothing to block.
    text = (
        "## Evidence\n"
        "node: BasePlatform.capabilities (cli/platforms/base.py:100) via cbm search_code project=myapp\n"
    )
    res = g.validate_grep_honesty(text, indexed_projects=CUR, repo_root="/home/zane/myapp")
    assert res.ok is True


def test_no_indexed_projects_passes():
    # Nothing indexed → knowledge tools genuinely cannot serve → grep allowed.
    text = "cbm unavailable — grep fallback, MEDIUM\nfound in cli/platforms/base.py:100\n"
    res = g.validate_grep_honesty(text, indexed_projects=[], repo_root="/home/zane/myapp")
    assert res.ok is True
