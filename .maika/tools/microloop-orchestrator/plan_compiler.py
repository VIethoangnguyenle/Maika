# plan_compiler.py
"""Deterministic plan compiler (v2 §17 W1 subset): verdict -> queue -> verbatim briefs."""
import hashlib
import importlib.util
import json
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


def compile_plan(ws, repo_root):
    ws = Path(ws)
    pp = _load("plan_parser", "plan_parser.py")
    orch = _load("orchestrator", "orchestrator.py")
    gates = _load("gates", "gate-check/gates.py")
    text = (ws / "IMPLEMENTATION_PLAN.md").read_text(encoding="utf-8")
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
        capsule = {
            "task_id": tid,
            "knowledge_slice": {k: (kn.get(k) or []) for k in slice_keys},
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
        queue_tasks.append({
            "id": tid, "depends_on": t["header"].get("depends_on") or [],
            "status": "pending",
            "brief_path": str(brief_path.relative_to(ws)),
            "brief_hash": brief_hash,
            "capsule_path": str(capsule_path.relative_to(ws)),
            "capsule_hash": _sha(capsule_text),
            "result_path": f"results/{tid}.yaml",
            "files": t["header"].get("files") or {},
        })
    (gen / "TASK_QUEUE.json").write_text(json.dumps(
        {"change_id": manifest["change_id"], "plan_sha256": plan_sha,
         "tasks": queue_tasks}, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"verdict": "APPROVED", **manifest}
