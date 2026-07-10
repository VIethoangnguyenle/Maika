"""CLI: gate-check <gate> <file>  → exit 0 (pass) / 1 (fail)."""
import argparse
import os
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
    "code-evidence": "validate_code_evidence",
    "vnext-plan": "validate_vnext_plan",
    "vnext-workspace": "validate_change_workspace",
    "intent": "validate_intent",
    "exploration-evidence": "validate_exploration_evidence",
    "query-plan": "validate_query_plan",
    "tool-health": "validate_tool_health",
    "conflicts": "validate_conflicts",
    "coverage": "validate_coverage",
    "database-context": "validate_database_context",
    "spec": "validate_vnext_spec",
    "brief-integrity": "validate_brief_integrity",
    "capsule-integrity": "validate_capsule_integrity",
    "evidence-update-request": "validate_evidence_update_request",
    "result-contract": "validate_result_contract",
    "task-review": "validate_task_review",
    "final-review": "validate_final_review",
    "plan-review": "validate_plan_review",
    "knowledge-impact": "validate_knowledge_impact",
    "verification-report": "validate_verification_report",
    "meta-prompt-constitution": "validate_meta_prompt_constitution",
    "bootstrap-complete": "validate_bootstrap_complete",
    "context-package": "validate_context_package",
    "dispatch-kernel": "validate_dispatch_kernel",
    "knowledge-trace": "validate_knowledge_trace",
    "skill-feedback": "validate_skill_feedback",
    "skill-evolution-candidate": "validate_skill_evolution_candidate",
    "skill-evolution-review": "validate_skill_evolution_review",
    "skill-evolution-promotion": "validate_skill_evolution_promotion",
}


def _load_module(name):
    import importlib.util
    mod = Path(__file__).resolve().parent / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, mod)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _load_gates():
    return _load_module("gates")


def _load_index_rule_ids(index_path, artifact_type=None):
    data = yaml.safe_load(Path(index_path).read_text(encoding="utf-8")) or {}
    entries = data.get("entries") or []
    matched = []
    for entry in entries:
        applies = entry.get("applies_to") or []
        if artifact_type is None or artifact_type in applies:
            if entry.get("id"):
                matched.append(entry["id"])
    return set(matched), len(matched) == 0


def main(argv=None):
    import importlib.util
    argv = argv or sys.argv[1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("gate", choices=VALIDATORS)
    parser.add_argument("file")
    parser.add_argument("--against")
    parser.add_argument("--index")
    parser.add_argument("--artifact-type")
    parser.add_argument("--repo-root", help="repo root for code-evidence (default: cwd)")
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
    elif args.gate in {"ac-coverage", "integration-coverage"}:
        if not args.against:
            print("FAIL — --against is required for coverage checks")
            return 2
        kwargs["spec_text"] = Path(args.against).read_text(encoding="utf-8")
    elif args.gate == "code-evidence":
        repo_root = args.repo_root or os.getcwd()
        cap = _load_module("capability")
        indexed = cap.indexed_projects(repo_root)
        gates_mod = _load_module("gates")
        node_ids = gates_mod._parse_node_table(text)
        verified, ok = cap.verify_nodes(node_ids)
        kwargs["indexed_projects"] = indexed
        kwargs["verified_node_files"] = verified
        kwargs["repo_root"] = repo_root
        kwargs["probe_ok"] = ok
    elif args.gate == "vnext-plan":
        pp_path = Path(__file__).resolve().parents[1] / "microloop-orchestrator" / "plan_parser.py"
        spec_pp = importlib.util.spec_from_file_location("plan_parser", pp_path)
        pp = importlib.util.module_from_spec(spec_pp); spec_pp.loader.exec_module(pp)
        kwargs["plan_doc"] = pp.parse_plan(text)
        kwargs["repo_root"] = args.repo_root or os.getcwd()
        if args.against:
            import hashlib
            kwargs["spec_sha256"] = hashlib.sha256(
                Path(args.against).read_bytes()).hexdigest()
    elif args.gate == "intent":
        if not args.against:
            print("FAIL — --against is required for intent gate (CHANGE.yaml)")
            return 2
        kwargs["change_text"] = Path(args.against).read_text(encoding="utf-8")
    elif args.gate == "exploration-evidence":
        if not args.against:
            print("FAIL — --against is required for exploration-evidence gate")
            return 2
        kwargs["evidence_text"] = Path(args.against).read_text(encoding="utf-8")
        kwargs["repo_root"] = args.repo_root or os.getcwd()
    elif args.gate == "query-plan":
        reg = yaml.safe_load(
            (Path(__file__).resolve().parents[2] / "profiles" / "capability-registry.yaml")
            .read_text(encoding="utf-8")
        ) or {}
        caps = reg.get("capabilities") or {}
        kwargs["valid_capabilities"] = set(caps)
        coverable = set()
        for spec_ in caps.values():
            coverable.update(spec_.get("preferred_evidence") or [])
        kwargs["coverable_evidence"] = coverable
    elif args.gate == "spec":
        if not args.against:
            print("FAIL — --against is required for spec gate (CHANGE.yaml)")
            return 2
        change_doc = yaml.safe_load(Path(args.against).read_text(encoding="utf-8")) or {}
        kwargs["change_class"] = change_doc.get("class", "standard")
    elif args.gate == "brief-integrity":
        import json
        ws_root = Path(args.file).resolve().parents[1]
        kwargs["queue_doc"] = json.loads((ws_root / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
    elif args.gate == "capsule-integrity":
        import json
        ws_root = Path(args.file).resolve().parents[1]
        kwargs["queue_doc"] = json.loads((ws_root / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
        kwargs["task_id"] = Path(args.file).name.split(".")[0]
        ev = ws_root / "exploration" / "EVIDENCE_MANIFEST.yaml"
        if ev.exists():
            kwargs["evidence_manifest_text"] = ev.read_text(encoding="utf-8")
    elif args.gate == "result-contract":
        import json
        ws_root = Path(args.file).resolve().parents[1]
        kwargs["queue_doc"] = json.loads((ws_root / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
        kwargs["task_id"] = Path(args.file).stem
    elif args.gate == "task-review":
        import json
        ws_root = Path(args.file).resolve().parents[1]
        kwargs["queue_doc"] = json.loads((ws_root / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))
        kwargs["task_id"] = Path(args.file).stem
    elif args.gate == "final-review":
        import json
        ws_root = Path(args.file).resolve().parents[1]
        kwargs["queue_doc"] = json.loads((ws_root / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))

    res = getattr(g, VALIDATORS[args.gate])(text, **kwargs)
    print(("PASS" if res.ok else f"FAIL — {res.reason}"))
    return 0 if res.ok else 1


if __name__ == "__main__":
    sys.exit(main())
