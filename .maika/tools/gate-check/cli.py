"""CLI: gate-check <gate> <file>  → exit 0 (pass) / 1 (fail)."""
import argparse
import sys
from pathlib import Path

import yaml

VALIDATORS = {
    "knowledge-checkpoint": "validate_knowledge_checkpoint",
    "mcp-status": "validate_mcp_status",
    "memory-recall": "validate_memory_recall",
    "phase-chain": "validate_phase_chain",
    "handoff-slice": "validate_handoff_slice",
    "implementation-context": "validate_implementation_context",
    "context-request": "validate_context_request",
    "node-checkpoint": "validate_node_checkpoint",
    "apply-gate": "validate_apply_gate",
    "teaching-moment": "validate_teaching_moment",
    "archive-ready": "validate_archive_ready",
    "reset-ready": "validate_reset_ready",
    "ac-coverage": "validate_ac_coverage",
    "integration-coverage": "validate_integration_coverage",
}


def _load_gates():
    import importlib.util
    mod = Path(__file__).resolve().parent / "gates.py"
    spec = importlib.util.spec_from_file_location("gates", mod)
    g = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(g)
    return g


def _load_index_rule_ids(index_path, artifact_type=None):
    data = yaml.safe_load(Path(index_path).read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    matched = []
    for entry in entries:
        applies = entry.get("applies_to") or []
        if artifact_type is None or artifact_type in applies or not applies:
            if entry.get("id"):
                matched.append(entry["id"])
    return set(matched), len(matched) == 0


def main(argv=None):
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", choices=VALIDATORS)
    parser.add_argument("file")
    parser.add_argument("--against")
    parser.add_argument("--index")
    parser.add_argument("--artifact-type")
    try:
        args = parser.parse_args(argv)
    except SystemExit:
        return 2

    g = _load_gates()
    text = Path(args.file).read_text(encoding="utf-8")
    kwargs = {}
    if args.gate == "knowledge-checkpoint" and args.index:
        valid_rule_ids, index_empty = _load_index_rule_ids(args.index, args.artifact_type)
        kwargs["valid_rule_ids"] = valid_rule_ids
        kwargs["allow_no_knowledge"] = index_empty
    elif args.gate in {"handoff-slice", "implementation-context"} and args.index:
        valid_rule_ids, slice_empty = _load_index_rule_ids(args.index, args.artifact_type)
        if slice_empty:
            print(f"WARN — slice empty for artifact_type={args.artifact_type} — falling back to legacy check")
        else:
            if args.artifact_type is None:
                print("WARN — --index without --artifact-type: checking rule-id existence only")
            kwargs["valid_rule_ids"] = valid_rule_ids
    elif args.gate in {"ac-coverage", "integration-coverage"}:
        if not args.against:
            print("FAIL — --against is required for coverage checks")
            return 2
        kwargs["spec_text"] = Path(args.against).read_text(encoding="utf-8")

    res = getattr(g, VALIDATORS[args.gate])(text, **kwargs)
    print(("PASS" if res.ok else f"FAIL — {res.reason}"))
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
