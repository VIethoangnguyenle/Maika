import json, sys, re
from pathlib import Path
import xml.dom.minidom as minidom

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from backends import checkstyle  # noqa: E402

def _norm(xml_str):
    return re.sub(r">\s+<", "><", xml_str.strip())

def test_ir_renders_wellformed_xml():
    ir = json.loads((HERE / "fixtures" / "expected-ir.json").read_text(encoding="utf-8"))
    xml = checkstyle.ir_to_checkstyle(ir)
    minidom.parseString(xml)

def test_forbid_else_is_regexp_warning():
    ir = {"version":"1.0","source_hash":"0"*64,"sources":[],"rules":[
        {"id":"HP-7.forbid_else","ir_rule":"forbid_else","severity":"warning","params":{},"source_ref":"author-dna.yaml#HP-7"}]}
    xml = checkstyle.ir_to_checkstyle(ir)
    assert "Regexp" in xml
    assert '<property name="severity" value="warning"/>' in _norm(xml)

def test_source_hash_embedded_in_header():
    ir = {"version":"1.0","source_hash":"abc123","sources":[],"rules":[]}
    xml = checkstyle.ir_to_checkstyle(ir)
    assert "source_hash=abc123" in xml

def test_nesting_maps_to_nestedifdepth():
    ir = {"version":"1.0","source_hash":"0"*64,"sources":[],"rules":[
        {"id":"t","ir_rule":"max_if_nesting","severity":"error","params":{"max":1},"source_ref":"x"}]}
    xml = checkstyle.ir_to_checkstyle(ir)
    assert "NestedIfDepth" in xml
    assert 'value="1"' in xml

def test_matches_golden_fixture():
    ir = json.loads((HERE / "fixtures" / "expected-ir.json").read_text(encoding="utf-8"))
    xml = checkstyle.ir_to_checkstyle(ir)
    golden = (HERE / "fixtures" / "expected-checkstyle.xml").read_text(encoding="utf-8")
    assert _norm(xml) == _norm(golden)
