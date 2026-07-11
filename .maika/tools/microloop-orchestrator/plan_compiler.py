# plan_compiler.py
"""Deterministic plan compiler (v2 §17 W1 subset): verdict -> queue -> verbatim briefs."""
import hashlib
import importlib.util
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    module_dir = str(mod_path.parent)
    inserted = module_dir not in sys.path
    if inserted:
        sys.path.insert(0, module_dir)
    try:
        spec.loader.exec_module(m)
    finally:
        if inserted:
            sys.path.remove(module_dir)
    return m


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _active_project_knowledge(framework_root, repo_root, task_header, section_text,
                              task_class, max_items):
    """Delegate production selection to the canonical freshness-aware service."""
    long_term = Path(framework_root) / "knowledge" / "long-term"
    index_path = long_term / "knowledge-index.yaml"
    questions = task_header.get("knowledge_questions") or []
    files = task_header.get("files") or {}
    scope = [item for values in files.values() for item in (values or [])]
    terms = {word.lower() for value in [*scope, *questions, section_text]
             for word in re.findall(r"[A-Za-z0-9_-]{4,}", str(value))}
    empty = {"retrieved": 0, "eligible": 0, "reused": 0, "rejected_stale": 0,
             "rejected_authority": 0, "rejected_scope": 0, "revalidated": 0,
             "newly_created": 0, "evidence_omitted": 0}
    if not index_path.exists():
        return [], questions, empty
    hardening = _load("runtime_hardening_knowledge", "runtime_hardening.py")
    result = hardening.select_knowledge_slice(
        index_path, long_term, Path(repo_root), "code-change", "task", [], scope,
        task_class=task_class, search_terms=terms, max_items=max_items,
        store_name="project-knowledge",
    )
    return result["entries"], questions, result["evidence_metrics"]


def compile_plan(ws, repo_root):
    ws = Path(ws)
    pp = _load("plan_parser", "plan_parser.py")
    orch = _load("orchestrator", "orchestrator.py")
    gates = _load("gates", "gate-check/gates.py")
    adaptive = _load("adaptive_runtime", "adaptive_runtime.py")
    text = (ws / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
    generated_at = datetime.fromtimestamp(
        (ws / "IMPLEMENTATION_PLAN.md").stat().st_mtime, timezone.utc
    ).isoformat()
    gen = ws / "generated"
    spec_path = ws / "SPEC.md"
    spec_sha = (hashlib.sha256(spec_path.read_bytes()).hexdigest()
                if spec_path.exists() else None)
    evidence_path = ws / "exploration" / "EVIDENCE_MANIFEST.yaml"
    evidence_sha = (hashlib.sha256(evidence_path.read_bytes()).hexdigest()
                    if evidence_path.exists() else None)
    spec_text = spec_path.read_text(encoding="utf-8") if spec_path.exists() else None
    try:
        doc = pp.parse_plan(text)
        res = gates.validate_vnext_plan(text, plan_doc=doc, repo_root=str(repo_root),
                                        spec_sha256=spec_sha,
                                        evidence_sha256=evidence_sha,
                                        spec_text=spec_text)
    except ValueError as e:
        res = gates.Result(False, str(e))
        doc = None
    verdict = "APPROVED" if res.ok else "REVISE"
    (gen / "PLAN_VALIDATION.json").write_text(json.dumps(
        {"verdict": verdict, "checks": [{"id": "vnext-plan", "ok": res.ok,
                                         "reason": res.reason}]},
        ensure_ascii=False, indent=2), encoding="utf-8")
    if verdict != "APPROVED":
        return {"verdict": verdict, "reason": res.reason}
    plan_sha = _sha(text)
    manifest = {
        "change_id": doc["meta"]["change_id"],
        "base_commit": doc["meta"]["base_commit"],
        "plan_sha256": plan_sha,
        "spec_sha256": spec_sha,
    }
    (gen / "PLAN_MANIFEST.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    topo_input = [{"id": t["id"], "depends_on": t["header"].get("depends_on") or []}
                  for t in doc["tasks"]]
    order = [t["id"] for t in orch.topo_sort(topo_input)]
    by_id = {t["id"]: t for t in doc["tasks"]}
    evidence_manifest_hash = ("sha256:" + evidence_sha) if evidence_sha else None
    slice_keys = ("author_dna", "conventions", "code_evidence", "business_rules",
                  "historical_context", "database_evidence")
    queue_tasks = []
    framework_root = ws.parents[1]
    change = yaml.safe_load((ws / "CHANGE.yaml").read_text(encoding="utf-8")) or {}
    config_path = framework_root / "profiles" / "execution-mode.local.yaml"
    if not config_path.exists():
        config_path = framework_root / "profiles" / "execution-mode.yaml"
    runtime_policy = adaptive.RuntimePolicy.from_config(
        yaml.safe_load(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    )
    task_class = change.get("class", "standard")
    evidence_limit = int(runtime_policy.token_budget[task_class]["max_evidence_items"])
    evidence_retrieved = 0
    evidence_reused = 0
    for tid in order:
        t = by_id[tid]
        body = t["section_text"]
        brief_hash = _sha(body)
        brief_path = ws / "briefs" / f"{tid}.md"
        header = yaml.safe_dump({"change_id": manifest["change_id"], "task_id": tid,
                                 "brief_hash": brief_hash, "plan_sha256": plan_sha},
                                sort_keys=False)
        brief_path.write_text(header + "\n---\n" + body, encoding="utf-8")
        # W4: Task Knowledge Capsule — smallest relevant knowledge slice + freshness.
        kn = t["header"].get("knowledge") or {}
        project_slice, knowledge_questions, evidence_metrics = _active_project_knowledge(
            framework_root, repo_root, t["header"], body, task_class, evidence_limit
        )
        capsule = {
            "task_id": tid,
            "knowledge_slice": {k: (kn.get(k) or []) for k in slice_keys},
            "project_knowledge": project_slice,
            "evidence_metrics": evidence_metrics,
            "knowledge_questions": knowledge_questions,
            "forbidden_patterns": t["header"].get("forbidden_patterns") or [],
            "assumptions": t["header"].get("assumptions") or [],
            "freshness": {
                "repository_commit": manifest["base_commit"],
                "evidence_manifest_hash": evidence_manifest_hash,
            },
            "confidence": t["header"].get("confidence") or "medium",
        }
        evidence_retrieved += evidence_metrics["retrieved"]
        evidence_reused += evidence_metrics["reused"]
        capsule_text = yaml.safe_dump(capsule, sort_keys=False, allow_unicode=True)
        capsule_path = ws / "briefs" / f"{tid}.knowledge.yaml"
        capsule_path.write_text(capsule_text, encoding="utf-8")
        context_package = {
            "version": 1,
            "role": "application-implementer",
            "change_id": manifest["change_id"],
            "state": "EXECUTING",
            "loaded_artifacts": [brief_path.relative_to(ws).as_posix(),
                                 capsule_path.relative_to(ws).as_posix()],
            "knowledge_slice": project_slice,
            "memory_slice": kn.get("historical_context") or [],
            "source_anchors": kn.get("code_evidence") or [],
            "database_slice": kn.get("database_evidence") or [],
            "missing_context": [],
            "degradation": [],
            "confidence": t["header"].get("confidence") or "medium",
            "freshness": {"repository_commit": manifest["base_commit"],
                          "generated_at": generated_at},
        }
        context_text = yaml.safe_dump(context_package, sort_keys=False, allow_unicode=True)
        context_path = gen / f"CONTEXT_PACKAGE.{tid}.yaml"
        context_path.write_text(context_text, encoding="utf-8")
        queue_tasks.append({
            "id": tid, "depends_on": t["header"].get("depends_on") or [],
            "role": t["header"].get("role") or "application-implementer",
            "status": "pending",
            "brief_path": brief_path.relative_to(ws).as_posix(),
            "brief_hash": brief_hash,
            "capsule_path": capsule_path.relative_to(ws).as_posix(),
            "capsule_hash": _sha(capsule_text),
            "context_package_path": context_path.relative_to(ws).as_posix(),
            "context_package_hash": _sha(context_text),
            "evidence_ids": list(dict.fromkeys(
                list((doc["meta"].get("knowledge_trace") or {}).get("evidence_ids") or []) +
                [item.get("id") for item in project_slice if item.get("id")]
            )),
            "knowledge_ids": [item.get("id") for item in project_slice if item.get("id")],
            "result_path": f"results/{tid}.yaml",
            "files": t["header"].get("files") or {},
        })
    (gen / "TASK_QUEUE.json").write_text(json.dumps(
        {"version": 1, "schema_version": 1, "generation": 1,
         "change_id": manifest["change_id"], "base_commit": manifest["base_commit"],
         "plan_sha256": plan_sha, "task_class": change.get("class", "standard"),
         "repo_root": str(Path(repo_root).resolve()),
         "runtime_metrics": {
             "version": 1, "task_class": change.get("class", "standard"),
             "total_tokens": "unavailable",
             "token_count_reason": "platform did not provide token usage",
             "worker_calls": 0, "tool_calls": 0,
             "evidence_reuse_ratio": evidence_reused / max(1, evidence_retrieved),
             "retry_count": 0, "real_verification_commands": 0, "review_findings": 0,
             "human_corrections": 0, "knowledge_entries_created": 0,
             "knowledge_entries_reused": sum(len(q.get("knowledge_ids") or []) for q in queue_tasks),
         },
         "tasks": queue_tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "APPROVED", **manifest}
