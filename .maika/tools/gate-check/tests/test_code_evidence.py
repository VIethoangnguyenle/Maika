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
