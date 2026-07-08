import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_parse_node_table_extracts_node_ids():
    text = (
        "### 2.3 Key Components\n"
        "| Component | node_id | Vai trò |\n"
        "|-----------|---------|---------|\n"
        "| capabilities | proj.cli.base.BasePlatform.capabilities | handler |\n"
        "| scaffold | proj.cli.scaffold.scaffold_plugin | builder |\n"
        "\n---\n## 3. Enum\n| x | proj.other.node | y |\n"
    )
    assert g._parse_node_table(text) == [
        "proj.cli.base.BasePlatform.capabilities",
        "proj.cli.scaffold.scaffold_plugin",
    ]  # stops at §3; skips header/separator


def test_parse_node_table_skips_placeholder_rows():
    text = "### 2.3 Key Components\n| Component | node_id | Vai trò |\n| ... | ... | ... |\n"
    assert g._parse_node_table(text) == []


def test_section_files_collects_only_named_sections():
    text = (
        "## 2.2 Entry Points\n| H | C | Path |\n| h | c | cli/a.py |\n"
        "## 3. Enum\nunrelated cli/z.py\n"
        "## 4. Phát hiện\nfound in cli/b.py:10\n"
    )
    got = g._section_files(text, ("Entry Points", "Phát hiện"))
    assert got == {"cli/a.py", "cli/b.py"}  # §3 not scanned


IDX = [{"name": "proj", "root_path": "/repo"}]
# §2.3 with one node; verified map says that node exists at /repo/cli/base.py
NODE = "proj.cli.base.BasePlatform.capabilities"
V = {NODE: "/repo/cli/base.py"}


def _art(node_row="", section4="", entry_path=""):
    return (
        "## 2.2 Entry Points\n| H | C | Path |\n" + (f"| h | c | {entry_path} |\n" if entry_path else "")
        + "### 2.3 Key Components\n| Component | node_id | Vai trò |\n"
        + (node_row + "\n" if node_row else "")
        + "## 4. Phát hiện\n" + (section4 + "\n" if section4 else "")
    )


def test_C_fabricated_node_fails():
    art = _art(node_row=f"| cap | {NODE} | h |")
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is False and "not found in cbm graph" in res.reason


def test_B_silent_grep_indexed_file_without_node_fails():
    art = _art(section4="found handler in cli/base.py:100")  # §2.3 empty, §4 names an indexed file
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is False and "no verified" in res.reason.lower()


def test_pass_verified_node_covers_finding():
    art = _art(node_row=f"| cap | {NODE} | h |", section4="handler in cli/base.py:100")
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files=V, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_unindexed_file_in_finding_passes():
    art = _art(section4="seen in /other/x.py:7")  # not under /repo
    res = g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_no_indexed_projects_passes():
    art = _art(section4="found in cli/base.py:100")
    res = g.validate_code_evidence(art, indexed_projects=[], verified_node_files={}, repo_root="/repo", probe_ok=True)
    assert res.ok is True


def test_probe_fail_needs_embedded_cbm_error():
    art = _art(section4="found in cli/base.py:100") + "\ncbm down\n"
    assert g.validate_code_evidence(art, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=False).ok is False
    art2 = _art(section4="found in cli/base.py:100") + '\nprobe error: "project is required"\n'
    assert g.validate_code_evidence(art2, indexed_projects=IDX, verified_node_files={}, repo_root="/repo", probe_ok=False).ok is True
