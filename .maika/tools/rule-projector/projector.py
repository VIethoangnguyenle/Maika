"""Rule Projector: author-dna.yaml + conventions.yaml -> IR (neutral JSON)."""
import argparse, hashlib, json, sys
from datetime import datetime, timezone
from pathlib import Path
import yaml

IR_VERSION = "1.0"

def _load_yaml(path):
    return yaml.safe_load(Path(path).read_text()) or {}

def _approved(doc):
    meta = doc.get("meta", {}) if isinstance(doc, dict) else {}
    return meta.get("status") == "approved"

def _rule(rid, ir_rule, severity, params, source_ref):
    return {"id": rid, "ir_rule": ir_rule, "severity": severity,
            "params": params, "source_ref": source_ref}

def _severity(agent_action, override=None):
    if override:
        return override
    if agent_action and agent_action.startswith("REJECT"):
        return "error"
    return "warning"

def project_thresholds(thresholds):
    rules = []
    if not thresholds:
        return rules
    ref = "author-dna.yaml#complexity_thresholds"
    if "max_nesting_depth" in thresholds:
        rules.append(_rule("threshold.max_if_nesting", "max_if_nesting", "error",
                           {"max": thresholds["max_nesting_depth"]}, ref))
    if "max_method_branches" in thresholds:
        rules.append(_rule("threshold.max_cyclomatic", "max_cyclomatic", "warning",
                           {"max": thresholds["max_method_branches"]}, ref))
    if "max_lines_per_method" in thresholds:
        rules.append(_rule("threshold.max_method_lines", "max_method_lines", "warning",
                           {"max": thresholds["max_lines_per_method"]}, ref))
    return rules

def _normalize_principles(principles):
    """Schema v1.1: dict keyed by rule_id. Legacy: list of {id: ...}."""
    if isinstance(principles, dict):
        return [{**v, "id": v.get("id", k)} for k, v in principles.items()
                if isinstance(v, dict)]
    return principles or []

def project_principles(principles):
    rules = []
    for p in _normalize_principles(principles):
        if not p.get("mechanically_checkable"):
            continue
        pid = p.get("id", "UNKNOWN")
        for spec in p.get("check_spec", []):
            params = dict(spec.get("params", {}))
            override = params.get("severity_override")
            rules.append(_rule(f"{pid}.{spec['ir_rule']}", spec["ir_rule"],
                              _severity(p.get("agent_action"), override),
                              params, f"author-dna.yaml#{pid}"))
    return rules

def project_naming(conventions):
    rules = []
    for n in (conventions.get("naming_patterns") or []):
        target = n["target"]
        rules.append(_rule(f"naming.{target}", "naming_regex", "warning",
                          {"target": target, "pattern": n["pattern"]},
                          "conventions.yaml#naming_patterns"))
    return rules

def project_code_hygiene(conventions):
    """code_hygiene.java (machine lane) -> IR. Key = ir_rule 1:1; backend/schema
    là chốt validate kind (như naming: projector không tự lọc)."""
    rules = []
    java = (conventions.get("code_hygiene") or {}).get("java") or {}
    for key, spec in java.items():
        sev = "error" if (spec or {}).get("severity") == "mandatory" else "warning"
        rules.append(_rule(f"hygiene.java.{key}", key, sev, {},
                           "conventions.yaml#code_hygiene"))
    return rules

def _dedupe(rules):
    seen, out = set(), []
    for r in rules:
        key = (r["ir_rule"], r["params"].get("target"))
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    return out

def compute_source_hash(paths):
    h = hashlib.sha256()
    for p in paths:
        h.update(Path(p).read_bytes())
    return h.hexdigest()

def build_ir(dna_path, conventions_path):
    dna = _load_yaml(dna_path)
    conv = _load_yaml(conventions_path)
    rules = []
    rules += project_principles(dna.get("hard_principles"))
    rules += project_principles(dna.get("style_preferences"))
    rules += project_thresholds(dna.get("complexity_thresholds"))
    if _approved(conv):
        rules += project_naming(conv)
        rules += project_code_hygiene(conv)
    rules = _dedupe(rules)
    return {
        "version": IR_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_hash": compute_source_hash([dna_path, conventions_path]),
        "sources": [Path(dna_path).name, Path(conventions_path).name],
        "rules": rules,
    }

def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--dna", required=True)
    ap.add_argument("--conventions", required=True)
    ap.add_argument("--out", default="generated")
    args = ap.parse_args(argv)
    ir = build_ir(args.dna, args.conventions)
    out = Path(args.out) / "rules.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(ir, indent=2, ensure_ascii=False))
    print(f"IR written: {out} ({len(ir['rules'])} rules)")
    return 0

if __name__ == "__main__":
    sys.exit(main())
