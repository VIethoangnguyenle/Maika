import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)

CONV = """
code_hygiene:
  java:
    no_unused_imports: {severity: mandatory}
    no_wildcard_imports: {severity: mandatory}
    no_redundant_imports: {severity: mandatory}
"""
NO_RULES = "naming: {}\n"

DIRTY = (
    "package com.example;\n"
    "import java.util.*;\n"
    "import java.io.File;\n"
    "import com.example.Used;\n"
    "class A { Used u; }\n"
)
CLEAN = (
    "package com.example;\n"
    "import com.example.Used;\n"
    "class A { Used u; }\n"
)


def test_dirty_java_fails_with_wildcard_and_unused():
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": DIRTY})
    assert res.ok is False
    assert "wildcard" in res.reason and "unused" in res.reason


def test_clean_java_passes():
    assert g.validate_code_hygiene(CONV, java_sources={"A.java": CLEAN}).ok is True


def test_duplicate_import_fails():
    src = ("import com.example.Used;\n" "import com.example.Used;\n"
           "class A { Used u; }\n")
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": src})
    assert res.ok is False and "duplicate" in res.reason


def test_direct_java_lang_import_is_redundant():
    src = "import java.lang.String;\nclass A { String s; }\n"
    res = g.validate_code_hygiene(CONV, java_sources={"A.java": src})
    assert res.ok is False and "redundant" in res.reason


def test_used_static_import_passes():
    src = ("import static org.junit.Assert.assertTrue;\n"
           "class T { void t() { assertTrue(true); } }\n")
    assert g.validate_code_hygiene(CONV, java_sources={"T.java": src}).ok is True


def test_no_rules_configured_passes():
    assert g.validate_code_hygiene(NO_RULES, java_sources={"A.java": DIRTY}).ok is True


def test_unknown_changed_files_fails_loudly():
    res = g.validate_code_hygiene(CONV, java_sources=None)
    assert res.ok is False and "changed files" in res.reason


def test_no_changed_java_files_passes():
    assert g.validate_code_hygiene(CONV, java_sources={}).ok is True


def test_block_commented_imports_ignored():
    src = (
        "package com.example;\n"
        "/*\n"
        "import java.util.*;\n"
        "import java.io.File;\n"
        "*/\n"
        "import java.io.File;\n"
        "class A { File f; }\n"
    )
    assert g.validate_code_hygiene(CONV, java_sources={"A.java": src}).ok is True


def test_recommended_severity_does_not_block():
    conv = ("code_hygiene:\n  java:\n"
            "    no_redundant_imports: {severity: recommended}\n")
    src = "import java.lang.String;\nclass A { String s; }\n"
    assert g.validate_code_hygiene(conv, java_sources={"A.java": src}).ok is True
