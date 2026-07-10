# plan_compiler.py
"""Deterministic plan compiler (v2 §17 W1 subset): verdict -> queue -> verbatim briefs."""
import hashlib
import importlib.util
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import yaml


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _sha(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _active_project_knowledge(framework_root, task_header, section_text):
    """Select the smallest active durable slice for a compiled task."""
    store = Path(framework_root) / "knowledge" / "long-term" / "project-knowledge"
    questions = task_header.get("knowledge_questions") or []
    files = task_header.get("files") or {}
    scope = [item for values in files.values() for item in (values or [])]
    terms = {word.lower() for value in [*scope, *questions, section_text]
             for word in re.findall(r"[A-Za-z0-9_-]{4,}", str(value))}
    matched = []
    for path in sorted(store.glob("*.yaml")) if store.is_dir() else []:
        item = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if not isinstance(item, dict) or item.get("status") != "active":
            continue
        haystack = " ".join([str(item.get("id", "")), str(item.get("statement", "")),
                             " ".join(item.get("applies_to") or [])]).lower()
        if not terms or any(term in haystack for term in terms):
            matched.append({
                "id": item.get("id"), "path": str(path),
                "statement": item.get("statement"),
                "provenance": item.get("provenance") or {},
                "freshness": item.get("freshness", "verified"),
                "confidence": item.get("confidence", "medium"),
            })
    return matched, questions


def compile_plan(ws, repo_root):
    ws = Path(ws)
    pp = _load("plan_parser", "plan_parser.py")
    orch = _load("orchestrator", "orchestrator.py")
    gates = _load("gates", "gate-check/gates.py")
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
        project_slice, knowledge_questions = _active_project_knowledge(
            framework_root, t["header"], body
        )
        capsule = {
            "task_id": tid,
            "knowledge_slice": {k: (kn.get(k) or []) for k in slice_keys},
            "project_knowledge": project_slice,
            "knowledge_questions": knowledge_questions,
            "forbidden_patterns": t["header"].get("forbidden_patterns") or [],
            "assumptions": t["header"].get("assumptions") or [],
            "freshness": {
                "repository_commit": manifest["base_commit"],
                "evidence_manifest_hash": evidence_manifest_hash,
            },
            "confidence": t["header"].get("confidence") or "medium",
        }
        capsule_text = yaml.safe_dump(capsule, sort_keys=False, allow_unicode=True)
        capsule_path = ws / "briefs" / f"{tid}.knowledge.yaml"
        capsule_path.write_text(capsule_text, encoding="utf-8")
        context_package = {
            "version": 1,
            "role": "application-implementer",
            "change_id": manifest["change_id"],
            "state": "EXECUTING",
            "loaded_artifacts": [str(brief_path.relative_to(ws)), str(capsule_path.relative_to(ws))],
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
            "brief_path": str(brief_path.relative_to(ws)),
            "brief_hash": brief_hash,
            "capsule_path": str(capsule_path.relative_to(ws)),
            "capsule_hash": _sha(capsule_text),
            "context_package_path": str(context_path.relative_to(ws)),
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
        {"change_id": manifest["change_id"], "plan_sha256": plan_sha,
         "repo_root": str(Path(repo_root).resolve()),
         "tasks": queue_tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "APPROVED", **manifest}
