import json
from pathlib import Path
import jsonschema

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent

def _load(p):
    return json.loads((Path(p)).read_text(encoding="utf-8"))

def test_expected_ir_validates_against_schema():
    schema = _load(ROOT / "ir_schema.json")
    ir = _load(HERE / "fixtures" / "expected-ir.json")
    jsonschema.validate(ir, schema)  # raises if invalid

def test_unknown_ir_rule_fails_schema():
    schema = _load(ROOT / "ir_schema.json")
    bad = {"version": "1.0", "source_hash": "0"*64, "sources": [], "rules": [
        {"id": "x", "ir_rule": "NOT_A_RULE", "severity": "error", "params": {}}]}
    try:
        jsonschema.validate(bad, schema)
        assert False, "should have raised"
    except jsonschema.ValidationError:
        pass
