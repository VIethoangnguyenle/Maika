import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
import projector  # noqa: E402

DNA = HERE / "fixtures" / "sample-author-dna.yaml"
CONV = HERE / "fixtures" / "sample-conventions.yaml"

def _norm(rules):
    return sorted([json.dumps(r, sort_keys=True) for r in rules])

def test_build_ir_matches_expected_rules():
    ir = projector.build_ir(str(DNA), str(CONV))
    expected = json.loads((HERE / "fixtures" / "expected-ir.json").read_text())
    assert _norm(ir["rules"]) == _norm(expected["rules"])

def test_semantic_principle_excluded():
    ir = projector.build_ir(str(DNA), str(CONV))
    ids = [r["id"] for r in ir["rules"]]
    assert not any("HP-5" in i for i in ids)

def test_bare_dna_still_projects_floor():
    bare = HERE / "fixtures" / "bare-author-dna.yaml"
    ir = projector.build_ir(str(bare), str(CONV))
    irules = {r["ir_rule"] for r in ir["rules"]}
    assert "max_if_nesting" in irules        # from thresholds floor
    assert "max_method_lines" in irules
    assert "naming_regex" in irules
    assert "forbid_else" not in irules

def test_dict_schema_v11_principles_project():
    """Schema v1.1: hard_principles là dict keyed by rule_id — không được crash."""
    dna_v11 = HERE / "fixtures" / "sample-author-dna-v11.yaml"
    ir = projector.build_ir(str(dna_v11), str(CONV))
    ids = [r["id"] for r in ir["rules"]]
    assert "HP-6.max_for_nesting" in ids
    assert "SP-5.require_javadoc_tag" in ids
    assert not any("HP-5" in i for i in ids)

def test_draft_conventions_skipped():
    import tempfile, textwrap
    draft = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    draft.write(textwrap.dedent('''
        meta:
          status: draft
        naming_patterns:
          - target: TypeName
            pattern: "^X.*$"
    '''))
    draft.close()
    ir = projector.build_ir(str(DNA), draft.name)
    assert not any(r["ir_rule"] == "naming_regex" for r in ir["rules"])

def test_code_hygiene_projected_with_severity_mapping():
    conv = {"meta": {"status": "approved"},
            "code_hygiene": {"java": {
                "no_unused_imports": {"severity": "mandatory"},
                "no_wildcard_imports": {"severity": "mandatory"},
                "no_redundant_imports": {"severity": "recommended"}}}}
    rules = projector.project_code_hygiene(conv)
    assert [r["ir_rule"] for r in rules] == [
        "no_unused_imports", "no_wildcard_imports", "no_redundant_imports"]
    by_id = {r["id"]: r for r in rules}
    assert by_id["hygiene.java.no_unused_imports"]["severity"] == "error"
    assert by_id["hygiene.java.no_redundant_imports"]["severity"] == "warning"
    assert all(r["source_ref"] == "conventions.yaml#code_hygiene" for r in rules)

def test_code_hygiene_absent_or_empty_projects_nothing():
    assert projector.project_code_hygiene({}) == []
    assert projector.project_code_hygiene({"code_hygiene": {}}) == []
    assert projector.project_code_hygiene({"code_hygiene": {"java": {}}}) == []

def test_code_hygiene_skipped_for_draft_conventions():
    import tempfile, textwrap
    draft = tempfile.NamedTemporaryFile("w", suffix=".yaml", delete=False)
    draft.write(textwrap.dedent('''
        meta:
          status: draft
        code_hygiene:
          java:
            no_unused_imports:
              severity: mandatory
    '''))
    draft.close()
    ir = projector.build_ir(str(DNA), draft.name)
    assert all(not r["id"].startswith("hygiene.") for r in ir["rules"])

def test_code_hygiene_unknown_key_passes_through():
    # documented: projector KHÔNG tự lọc kind — schema/backend là chốt validate
    conv = {"code_hygiene": {"java": {"foo_bar": {"severity": "mandatory"}}}}
    rules = projector.project_code_hygiene(conv)
    assert [r["ir_rule"] for r in rules] == ["foo_bar"]
