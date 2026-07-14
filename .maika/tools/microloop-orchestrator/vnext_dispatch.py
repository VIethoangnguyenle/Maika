# vnext_dispatch.py
"""Engine loop vNext: dispatch pending tasks to fresh workers."""
import json
import importlib.util
import hashlib
import os
import socket
import tempfile
from pathlib import Path
from datetime import datetime, timezone

import yaml

from adaptive_runtime import DEFAULT_TOKEN_BUDGET
from runtime_hardening import ReviewInvalid, parse_review


DISPATCH_KERNEL_ID = "KERNEL_ID: maika-knowledge-control-v1"
DISPATCH_TYPES = {
    "intent", "grounding", "database", "reconciliation", "brainstorming", "spec",
    "planning",
    "plan_review", "implementation", "fix", "task_review", "final_review",
    "verification", "knowledge_curator", "skill_evolution_curator",
    "skill_evolution_implementer", "skill_evolution_reviewer",
}
DEFAULT_EXTERNAL_WORKFLOWS = {
    "allowed": [],
    "request_only": ["understand", "understand-domain", "codebase-memory-index"],
}


def _dispatch_kernel():
    """Load the one canonical worker constitution; never duplicate prompt prose."""
    path = Path(__file__).resolve().parents[2] / "procedures" / "dispatch-kernel.md"
    text = path.read_text(encoding="utf-8")
    if DISPATCH_KERNEL_ID not in text:
        raise RuntimeError(f"invalid dispatch kernel: {path}")
    marker = "```text\n"
    start = text.find(marker)
    end = text.find("\n```", start + len(marker))
    if start < 0 or end < 0:
        raise RuntimeError(f"dispatch kernel has no canonical text block: {path}")
    return text[start + len(marker):end].strip()


def _load(name, rel):
    mod_path = Path(__file__).resolve().parent / rel if "/" not in rel else \
        Path(__file__).resolve().parents[1] / rel
    spec = importlib.util.spec_from_file_location(name, mod_path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def _read_queue(ws):
    return json.loads((Path(ws) / "generated" / "TASK_QUEUE.json").read_text(encoding="utf-8"))


def _external_workflow_registry():
    path = Path(__file__).resolve().parents[2] / "config" / "external-workflows.yaml"
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return doc.get("workflows") or {}


def external_workflow_contract(task=None):
    task = task or {}
    supplied = task.get("external_workflows") or {}
    # Mutation #14 (harness plan §21): an EXPLICIT empty request_only stays
    # empty — defaults apply only when the key is absent.
    request_only = supplied.get("request_only")
    if request_only is None:
        request_only = DEFAULT_EXTERNAL_WORKFLOWS["request_only"]
    contract = {
        "allowed": list(supplied.get("allowed") or []),
        "request_only": list(request_only),
    }
    known = set(_external_workflow_registry())
    unknown = (set(contract["allowed"]) | set(contract["request_only"])) - known
    if unknown:
        raise ValueError(f"unknown external workflows in dispatch contract: {sorted(unknown)}")
    return contract


def validate_external_workflow_request(text, contract=None):
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return False, f"invalid external workflow request YAML: {exc}", None
    if not isinstance(doc, dict):
        return False, "external workflow request must be a mapping", None
    if doc.get("request_type") != "external_workflow":
        return False, "request_type must be external_workflow", doc
    workflow = doc.get("workflow")
    registry = _external_workflow_registry()
    if workflow not in registry:
        return False, f"unknown external workflow: {workflow!r}", doc
    contract = contract or external_workflow_contract()
    permitted = set(contract["allowed"]) | set(contract["request_only"])
    if workflow not in permitted:
        return False, f"workflow not granted or requestable: {workflow}", doc
    if not isinstance(doc.get("reason"), str) or not doc["reason"].strip():
        return False, "external workflow request requires reason", doc
    if not isinstance(doc.get("required_for"), list) or not doc["required_for"]:
        return False, "external workflow request requires required_for", doc
    for field in ("observed_freshness", "resume_role"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            return False, f"external workflow request requires {field}", doc
    if not isinstance(doc.get("affected_claims"), list):
        return False, "external workflow request affected_claims must be a list", doc
    return True, None, doc


def validate_db_reprobe_request(text):
    """DB_REPROBE_REQUEST.yaml — environment-bound re-probe request (plan §16)."""
    try:
        doc = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        return False, f"invalid DB re-probe request YAML: {exc}", None
    if not isinstance(doc, dict):
        return False, "DB re-probe request must be a mapping", None
    if doc.get("request_type") != "db_reprobe":
        return False, "request_type must be db_reprobe", doc
    for field in ("reason", "environment", "database", "resume_role"):
        if not isinstance(doc.get(field), str) or not doc[field].strip():
            return False, f"DB re-probe request requires {field}", doc
    return True, None, doc


_REFRESH_REQUEST_FILES = {
    "external_workflow": "EXTERNAL_WORKFLOW_REQUEST.yaml",
    "db_reprobe": "DB_REPROBE_REQUEST.yaml",
}


def _graph_baseline_hash(ws) -> str:
    path = Path(ws) / "exploration" / "TRACE_EVIDENCE.yaml"
    if not path.is_file():
        return ""
    doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return ((doc.get("graph") or {}).get("observation")) or ""


def _fresh_invocation_hash(ws, provider, tool, baseline) -> str:
    """Latest success invocation hash for provider(/tool) that differs from
    the recorded baseline — the mechanical 'new provider evidence' check
    (mutation #13: refresh fulfilled without new evidence must fail)."""
    path = Path(ws) / "exploration" / "PROVIDER_INVOCATIONS.jsonl"
    if not path.is_file():
        return ""
    latest = ""
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if record.get("provider_id") != provider or record.get("status") != "success":
            continue
        if tool and record.get("tool") != tool:
            continue
        response_hash = record.get("response_hash") or ""
        if response_hash and response_hash != baseline:
            latest = response_hash
    return latest


def block_on_refresh_request(ws, role, request, vs, code):
    """Persist a durable BLOCKED refresh/re-probe blocker (plan §16/§17, B7).

    The request file records the evidence baseline at block time; fulfillment
    (fulfill_blocked_request) demands a provider invocation whose response
    hash differs from it. Never relies on parent conversation memory."""
    if code not in _REFRESH_REQUEST_FILES:
        raise ValueError(f"unknown refresh blocker code: {code}")
    ws = Path(ws)
    request = dict(request or {})
    if code == "external_workflow":
        request["baseline_evidence_hash"] = _graph_baseline_hash(ws)
        workflow = request.get("workflow")
        canonical = (((_external_workflow_registry().get(workflow) or {})
                      .get("commands") or {}).get("canonical") or workflow)
        remediation = (f"run {canonical}, record the refresh probe via "
                       "`maika provider record`, then vnext-fulfill-workflow")
    else:
        request["baseline_evidence_hash"] = _fresh_invocation_hash(
            ws, "db-access", None, "")
        remediation = ("re-probe DB Access for the declared environment, record it "
                       "via `maika provider record`, then vnext-fulfill-workflow")
    request["requested_at"] = datetime.now(timezone.utc).isoformat()
    request_file = _REFRESH_REQUEST_FILES[code]
    (ws / request_file).write_text(
        yaml.safe_dump(request, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )
    current = vs.load_state(ws).get("state")
    blocked = {
        "reason": "capability",
        "code": code,
        "role": role,
        "workflow": request.get("workflow"),
        "request_file": request_file,
        "remediation": remediation,
        "created_at": request["requested_at"],
        "resume_state": current,
        "resume_action": (f"vnext-dispatch-role --role "
                          f"{request.get('resume_role') or role}"),
    }
    vs.transition(ws, "BLOCKED", blocked=blocked)
    return blocked


def fulfill_blocked_request(ws, vs):
    """Fulfill a refresh/re-probe blocker with NEW provider evidence.

    Returns (ok, detail): detail is a failure reason, or on success a dict
    with the resolution record and the original role's resume action."""
    ws = Path(ws)
    state = vs.load_state(ws)
    blocked = state.get("blocked") or {}
    if state.get("state") != "BLOCKED" or blocked.get("code") not in _REFRESH_REQUEST_FILES:
        return False, "workspace is not blocked on an external workflow or DB re-probe"
    request_path = ws / (blocked.get("request_file") or "")
    if not request_path.is_file():
        return False, f"blocker request file missing: {blocked.get('request_file')}"
    request = yaml.safe_load(request_path.read_text(encoding="utf-8")) or {}
    baseline = request.get("baseline_evidence_hash") or ""
    if blocked["code"] == "external_workflow":
        provider = ((_external_workflow_registry().get(request.get("workflow")) or {})
                    .get("owner")) or ""
        tool = "get_graph_metadata" if provider == "understand-anything" else None
    else:
        provider, tool = "db-access", None
    if not provider:
        return False, f"workflow {request.get('workflow')!r} has no owning provider"
    evidence_hash = _fresh_invocation_hash(ws, provider, tool, baseline)
    if not evidence_hash:
        return False, (f"no NEW {provider} evidence — record a fresh success "
                       "invocation (response hash must differ from the baseline)")
    resolution = {
        "result_file": "exploration/PROVIDER_INVOCATIONS.jsonl",
        "evidence_hash": evidence_hash,
        "resolved_at": datetime.now(timezone.utc).isoformat(),
    }
    result_path = ws / "generated" / f"{request_path.stem}_RESULT.yaml"
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(
        yaml.safe_dump(dict(request, resolved=resolution), sort_keys=False,
                       allow_unicode=True),
        encoding="utf-8",
    )
    request_path.unlink()
    vs.transition(ws, blocked.get("resume_state"))
    return True, {"resolution": resolution, "role": blocked.get("role"),
                  "resume_action": blocked.get("resume_action"),
                  "result_file": str(result_path)}


def _write_queue(ws, doc, expected_generation=None):
    q_path = Path(ws) / "generated" / "TASK_QUEUE.json"
    current_generation = 0
    if q_path.exists():
        current_generation = int(json.loads(q_path.read_text(encoding="utf-8")).get("generation") or 0)
    if expected_generation is not None and current_generation != int(expected_generation):
        raise ValueError(f"queue generation mismatch: expected {expected_generation}, found {current_generation}")
    doc["schema_version"] = int(doc.get("schema_version") or 1)
    doc["generation"] = current_generation + 1
    doc.setdefault("version", 1)
    payload = json.dumps(doc, ensure_ascii=False, indent=2)
    fd, temp_name = tempfile.mkstemp(prefix=".TASK_QUEUE.", dir=q_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, q_path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except FileNotFoundError:
            pass
        raise
    return doc


def _update_task(ws, tid, **fields):
    doc = _read_queue(ws)
    generation = int(doc.get("generation") or 0)
    for task in doc["tasks"]:
        if task["id"] == tid:
            if fields.get("status") == "in_progress":
                fields.setdefault("lease", {
                    "version": 1, "pid": os.getpid(), "host": socket.gethostname(),
                    "started_at": datetime.now(timezone.utc).isoformat(),
                })
            elif fields.get("status") in {"done", "blocked", "changes_required"}:
                fields.setdefault("lease", None)
            task.update(fields)
            return _write_queue(ws, doc, expected_generation=generation)
    raise ValueError(f"task {tid} not in queue")


def _task_by_id(doc, tid):
    return next((t for t in doc.get("tasks", []) if t.get("id") == tid), None)


def _next_pending_task(doc):
    done = {t["id"] for t in doc.get("tasks", []) if t.get("status") == "done"}
    for task in doc.get("tasks", []):
        if task.get("status") in {"pending", "changes_required", "in_progress", "reviewing"}:
            if all(dep in done for dep in task.get("depends_on", []) or []):
                return task
    return None


def _append_dispatch_log(ws, record):
    path = Path(ws) / "generated" / "DISPATCH_LOG.jsonl"
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")


def _verdict(ws, text, review_type):
    queue = _read_queue(ws)
    try:
        return parse_review(
            text, review_type, queue.get("base_commit"),
            "sha256:" + queue.get("plan_sha256", ""),
        )["verdict"]
    except ReviewInvalid:
        return None


def run_planning_dispatch(ws, repo_root):
    ws = Path(ws)
    pc = _load("plan_compiler", "plan_compiler.py")
    res = pc.compile_plan(ws, repo_root)
    if res.get("verdict") == "REVISE":
        import yaml
        req = {
            "request_type": "context",
            "missing": [f"Plan validation failed: {res.get('reason')}"],
            "blocked_reason": "vnext-plan gate failed"
        }
        (ws / "CONTEXT_REQUEST.yaml").write_text(
            yaml.safe_dump(req, sort_keys=False, allow_unicode=True),
            encoding="utf-8"
        )
        return False
    return True

# Dispatch type -> canonical skill file pinned into the worker prompt (M8).
DISPATCH_SKILLS = {
    "intent": "intent-analysis",
    "grounding": "grounding-explorer",
    "database": "database-explorer",
    "reconciliation": "architecture-reconciler",
    "brainstorming": "grounded-brainstorming",
    "spec": "writing-spec",
    "planning": "writing-plan",
    "plan_review": "validating-plan",
    "implementation": "executing-task",
    "fix": "executing-task",
    "task_review": "reviewing-task",
    "final_review": "reviewing-change",
    "verification": "verification-before-completion",
    "knowledge_curator": "knowledge-promoter",
}

_PINNED_WORKSPACE_ARTIFACTS = (
    ("TRACE_REQUEST", "exploration/TRACE_REQUEST.yaml"),
    ("TRACE_EVIDENCE", "exploration/TRACE_EVIDENCE.yaml"),
    ("DATABASE_REQUEST", "exploration/DATABASE_REQUEST.yaml"),
    ("DATABASE_CONTEXT", "exploration/DATABASE_CONTEXT.yaml"),
    ("PROVIDER_INVOCATIONS", "exploration/PROVIDER_INVOCATIONS.jsonl"),
)


def control_surfaces_block(ws, klass) -> str:
    """Content-addressed control surfaces for a dispatch (harness plan §15, B6).

    The worker receives exact file paths + sha256 of the skill, provider
    registry, capability registry and any trace/DB artifacts — policy is
    pinned, never recalled from model memory. Computed at dispatch time from
    the files themselves, so a worker cannot be handed stale or hand-waved
    policy without the hash changing."""
    ws = Path(ws)
    framework = ws.parents[1]
    surfaces = []
    skill = DISPATCH_SKILLS.get(klass)
    if skill:
        surfaces.append(("SKILL", framework / "skills" / skill / "SKILL.md"))
    surfaces.append(("PROVIDER_REGISTRY",
                     framework / "config" / "provider-registry.yaml"))
    surfaces.append(("CAPABILITY_REGISTRY",
                     framework / "profiles" / "capability-registry.yaml"))
    for label, rel in _PINNED_WORKSPACE_ARTIFACTS:
        surfaces.append((label, ws / rel))
    lines = ["CONTROL_SURFACES (content-addressed — read these exact files):"]
    for label, path in surfaces:
        if not path.is_file():
            continue
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{label}_FILE: {path}")
        lines.append(f"{label}_SHA256: sha256:{digest}")
    lines += [
        "Do not infer provider policy from memory.",
        "Use only the pinned provider/tool contracts above.",
        "Do not claim provider health without invocation evidence.",
        "Do not call tools outside the allowed lane.",
    ]
    return "\n".join(lines)


def build_prompt(klass, ws, brief_rel, result_rel, extra=None, task=None):
    if klass not in DISPATCH_TYPES:
        raise ValueError(f"unknown dispatch type: {klass}")
    ws = Path(ws)
    task = task or {}
    task_id = task.get("id", "stub")
    allowed = json.dumps(task.get("files") or {}, ensure_ascii=False, sort_keys=True)
    dependencies = json.dumps(task.get("depends_on") or [], ensure_ascii=False)
    capsule = task.get("capsule_path") or "none"
    context_package = task.get("context_package_path") or "none"
    prior_review = task.get("review_path") or "none"
    external_workflows = json.dumps(
        external_workflow_contract(task), ensure_ascii=False, sort_keys=True,
    )
    lines = [
        f"DISPATCH_TYPE: {klass}",
        f"ROLE: {klass}",
        f"TASK_ID: {task_id}",
        f"ARTIFACT_FILE: {ws / brief_rel}",
        f"BRIEF_FILE: {ws / brief_rel}",
        f"OUTPUT_FILE: {ws / result_rel}",
        f"ALLOWED_SCOPE: {allowed}",
        f"DEPENDENCY_OUTPUTS: {dependencies}",
        f"KNOWLEDGE_CAPSULE: {ws / capsule if capsule != 'none' else capsule}",
        f"CONTEXT_PACKAGE: {ws / context_package if context_package != 'none' else context_package}",
        f"PRIOR_REVIEW: {ws / prior_review if prior_review != 'none' else prior_review}",
        f"EXTERNAL_WORKFLOWS: {external_workflows}",
        DISPATCH_KERNEL_ID,
        "",
        _dispatch_kernel(),
        "",
        control_surfaces_block(ws, klass),
        "",
        "Read exactly the assigned artifacts above and write exactly the output file.",
        "For implementation/review, read KNOWLEDGE_CAPSULE and record consumed IDs.",
        "Do not write outside ALLOWED_SCOPE.",
    ]
    if extra:
        lines.extend(["", str(extra)])
    return "\n".join(lines) + "\n"

# Authoring dispatch (PR 10): public commands execute skills, not only
# transition/validate. One row per role: expected states, prompt input/output,
# state after a gate-passing run (None = stay, e.g. optional brainstorming).
AUTHORING_ROLES = {
    "grounding": {
        "expected": ("INTAKE", "EXPLORING"),
        "input": "INTENT.md",
        "output": "exploration/GROUNDING.yaml",
        "success_state": "RECONCILING",
        "extra": ("Skill: grounding-explorer. Write the full exploration package under "
                  "exploration/ (QUERY_PLAN.yaml, TOOL_HEALTH.yaml, GROUNDING.yaml, "
                  "EVIDENCE_MANIFEST.yaml, CONFLICTS.yaml, COVERAGE.yaml)."),
    },
    "database": {
        "expected": ("EXPLORING",),
        "input": "exploration/DATABASE_REQUEST.yaml",
        "output": "exploration/DATABASE_CONTEXT.yaml",
        "success_state": None,
        "extra": ("Skill: database-explorer. Fill environment/database in "
                  "exploration/DATABASE_REQUEST.yaml explicitly, probe DB Access "
                  "through the exploration lane only (no data reads, writes or "
                  "scripts), record every call via maika provider record, and "
                  "write exploration/DATABASE_CONTEXT.yaml v2 (provider, probe, "
                  "allowed_tools, observations, code_consumers, classified drift)."),
    },
    "reconciliation": {
        "expected": ("RECONCILING",),
        "input": "exploration/GROUNDING.yaml",
        "output": "RECONCILIATION.md",
        "success_state": "BRAINSTORMING",
        "extra": ("Skill: architecture-reconciler. Reconcile evidence conflicts; update "
                  "exploration/CONFLICTS.yaml; RECONCILIATION.md must carry a Knowledge Trace."),
    },
    "brainstorming": {
        "expected": ("BRAINSTORMING",),
        "input": "RECONCILIATION.md",
        "output": "RECONCILIATION.md",
        "success_state": None,
        "extra": ("Skill: grounded-brainstorming. Compare evidence-backed approaches and "
                  "record them (with rejected options) in RECONCILIATION.md."),
    },
    "spec": {
        "expected": ("BRAINSTORMING",),
        "input": "RECONCILIATION.md",
        "output": "SPEC.md",
        "success_state": "SPEC_REVIEW",
        "extra": "Skill: writing-spec. Produce a class-aware SPEC.md with a Knowledge Trace.",
    },
    "planning": {
        "expected": ("PLANNING",),
        "input": "SPEC.md",
        "output": "IMPLEMENTATION_PLAN.md",
        "success_state": "PLAN_REVIEW",
        "extra": "Skill: writing-plan. Produce IMPLEMENTATION_PLAN.md per the plan doctrine.",
    },
}

_TRACE_BLOCK = None  # compiled lazily; extraction only — validation lives in gate-check


def markdown_trace_block(text):
    """Extract the Knowledge Trace YAML block from a markdown artifact."""
    global _TRACE_BLOCK
    import re
    if _TRACE_BLOCK is None:
        _TRACE_BLOCK = re.compile(
            r"^##\s+Knowledge Trace\s*$.*?```yaml\s*(.*?)```", re.MULTILINE | re.DOTALL
        )
    match = _TRACE_BLOCK.search(text)
    return match.group(1) if match else None


def database_lane_context(framework_path) -> str:
    """Allowed/denied DB tools for the database-explorer worker prompt
    (harness plan §11, M7 safety boundary). Pinned from the provider
    registry's lane contract — never author this list by hand."""
    registry_path = Path(framework_path) / "config" / "provider-registry.yaml"
    if not registry_path.exists():
        registry_path = (Path(__file__).resolve().parents[2]
                         / "config" / "provider-registry.yaml")
    registry = yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}
    lanes = ((((registry.get("providers") or {}).get("db-access") or {})
              .get("tool_contract") or {}).get("lanes") or {})
    allowed = sorted((lanes.get("exploration") or {}).get("tools") or [])
    denied = sorted({
        tool
        for lane, lane_spec in lanes.items() if lane != "exploration"
        for tool in (lane_spec or {}).get("tools") or []
    })
    return (
        f"ALLOWED_DB_TOOLS (exploration lane): {json.dumps(allowed)}\n"
        f"DENIED_DB_TOOLS (data probe/write/script — out of lane): {json.dumps(denied)}\n"
        "Any denied tool call fails the database-context gate; data-probe tools "
        "require data_probe_required: true in DATABASE_REQUEST.yaml."
    )


def run_authoring_dispatch(ws, role, runner, vs, validator=None):
    """Dispatch one authoring role, gate its output, transition on success.

    ``validator`` is a callable ``(ws) -> (ok, reason)`` supplied by the
    orchestrator (it owns the gate wiring); ``vs`` is the loaded vnext_state
    module. Returns a result dict — never raises for workflow-level failures.
    """
    spec = AUTHORING_ROLES.get(role)
    if spec is None:
        raise ValueError(f"unknown authoring role: {role}")
    ws = Path(ws)
    current = vs.load_state(ws).get("state")
    if current not in spec["expected"]:
        return {"ok": False,
                "reason": f"wrong state {current} (expected {'/'.join(spec['expected'])})"}
    if role == "grounding" and current == "INTAKE":
        vs.start_exploration(ws)
    extra = spec["extra"]
    if role == "database":
        extra = f"{extra}\n\n{database_lane_context(ws.parents[1])}"
    prompt = build_prompt(role, ws, spec["input"], spec["output"], extra=extra)

    # §18 observability: the dispatch log must answer which providers were
    # called during this dispatch and what the gates decided.
    invocations_path = ws / "exploration" / "PROVIDER_INVOCATIONS.jsonl"

    def _provider_calls():
        if not invocations_path.is_file():
            return 0
        return sum(1 for line in invocations_path.read_text(encoding="utf-8")
                   .splitlines() if line.strip())

    state_before = current
    started_at = datetime.now(timezone.utc).isoformat()
    calls_before = _provider_calls()
    exit_code, output = runner(prompt)

    def _log(outcome, gate_results=""):
        now = datetime.now(timezone.utc).isoformat()
        _append_dispatch_log(ws, {
            "dispatch_type": role, "role": role, "change_id": ws.name,
            "output": spec["output"], "worker_exit": exit_code,
            "outcome": outcome, "gate_results": gate_results,
            "provider_calls": _provider_calls() - calls_before,
            "state_before": state_before,
            "state_after": vs.load_state(ws).get("state"),
            "started_at": started_at, "ended_at": now, "ts": now,
        })

    out_path = ws / spec["output"]
    workflow_request = ws / "EXTERNAL_WORKFLOW_REQUEST.yaml"
    if workflow_request.exists():
        ok, reason, request = validate_external_workflow_request(
            workflow_request.read_text(encoding="utf-8")
        )
        _log("external_workflow_request")
        return {
            "ok": False,
            "reason": "EXTERNAL_WORKFLOW_REQUEST" if ok else reason,
            "request": request,
        }
    reprobe_request = ws / "DB_REPROBE_REQUEST.yaml"
    if reprobe_request.exists():
        ok, reason, request = validate_db_reprobe_request(
            reprobe_request.read_text(encoding="utf-8")
        )
        _log("db_reprobe_request")
        return {
            "ok": False,
            "reason": "DB_REPROBE_REQUEST" if ok else reason,
            "request": request,
        }
    if not out_path.exists():
        _log("no_output")
        return {"ok": False,
                "reason": f"worker produced no {spec['output']} (exit {exit_code}: {output})"}
    if validator is not None:
        ok, reason = validator(ws)
        if not ok:
            _log("gate_failed", reason)
            return {"ok": False, "reason": f"gate failed: {reason}"}
    if spec["success_state"]:
        vs.transition(ws, spec["success_state"])
    _log("ok", "pass")
    return {"ok": True, "state": vs.load_state(ws).get("state")}


def review_plan(ws, runner, output_path=None):
    ws = Path(ws)
    prompt = build_prompt("plan_review", ws, "IMPLEMENTATION_PLAN.md", "reviews/plan-review.md")
    (ws / "reviews").mkdir(exist_ok=True)
    out = output_path or (ws / "reviews" / "plan-review.md")
    if out.exists():
        out.unlink()
    
    exit_code, output = runner(prompt)
    if not out.exists():
        out.write_text(f"VERDICT: FINDINGS\nWorker exit {exit_code}: {output}", encoding="utf-8")
        
    text = out.read_text(encoding="utf-8")
    gates = _load("gates_plan_review", "gate-check/gates.py")
    queue = _read_queue(ws)
    evidence_ids = {item for task in queue.get("tasks") or [] for item in task.get("evidence_ids") or []}
    review = gates.validate_plan_review(
        text, valid_evidence_ids=evidence_ids, repo_root=queue.get("repo_root")
    )
    if review.ok and _verdict(ws, text, "plan") == "APPROVED":
        return "APPROVED"
    return "FINDINGS"


def _dispatch_to_runner(ws, dispatch_type, task, artifact_rel, output_rel, runner,
                        *, attempt=0, extra=None):
    queue = _read_queue(ws)
    metrics = queue.setdefault("runtime_metrics", {})
    task_class = queue.get("task_class", "standard")
    limits = (queue.get("runtime_limits") or {}).get(task_class) or DEFAULT_TOKEN_BUDGET[task_class]
    maximum = int(limits["max_worker_calls"])
    prompt = build_prompt(dispatch_type, ws, artifact_rel, output_rel, extra=extra, task=task)
    context_bytes = len(prompt.encode("utf-8"))
    for rel in {artifact_rel, task.get("capsule_path"), task.get("context_package_path"), task.get("review_path")}:
        path = Path(ws) / rel if rel else None
        if path and path.is_file():
            context_bytes += path.stat().st_size
    estimated_tokens = (context_bytes + 3) // 4
    metrics.update({
        "prompt_bytes": len(prompt.encode("utf-8")),
        "context_bytes": context_bytes,
        "estimated_tokens": int(metrics.get("estimated_tokens") or 0) + estimated_tokens,
        "estimation_method": "chars_div_4",
        "total_tokens": metrics.get("total_tokens", "unavailable"),
    })
    if estimated_tokens > int(limits["max_context_tokens"]):
        _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))
        return 76, (f"{task_class} context budget exceeded "
                    f"({estimated_tokens}/{limits['max_context_tokens']} estimated tokens)")
    if int(metrics.get("worker_calls") or 0) >= maximum:
        return 75, f"{task_class} worker-call budget exhausted; escalate or block"
    metrics["worker_calls"] = int(metrics.get("worker_calls") or 0) + 1
    if metrics["worker_calls"] == maximum:
        metrics["budget_warning"] = f"worker-call budget reached ({maximum}/{maximum})"
    if dispatch_type == "fix":
        metrics["retry_count"] = int(metrics.get("retry_count") or 0) + 1
    _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))
    _append_dispatch_log(ws, {
        "dispatch_type": dispatch_type,
        "task_id": task.get("id") if task else None,
        "artifact_path": artifact_rel,
        "output_path": output_rel,
        "attempt": attempt,
        "kernel_id": DISPATCH_KERNEL_ID.split(": ", 1)[1],
        "capsule_path": task.get("capsule_path") if task else None,
    })
    return runner(prompt)


def _validate_brief(ws, gates, task, queue_doc):
    brief_path = Path(ws) / task["brief_path"]
    if not brief_path.exists():
        return gates.Result(False, f"missing brief: {task['brief_path']}")
    brief = gates.validate_brief_integrity(
        brief_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
    )
    if not brief.ok:
        return brief
    # W4: Task Knowledge Capsule must be immutable + fresh before dispatch.
    capsule_path = task.get("capsule_path")
    if capsule_path:
        cap_file = Path(ws) / capsule_path
        if not cap_file.exists():
            return gates.Result(False, f"missing capsule: {capsule_path}")
        ev = Path(ws) / "exploration" / "EVIDENCE_MANIFEST.yaml"
        capsule_result = gates.validate_capsule_integrity(
            cap_file.read_text(encoding="utf-8"),
            queue_doc=queue_doc,
            task_id=task["id"],
            evidence_manifest_text=ev.read_text(encoding="utf-8") if ev.exists() else None,
        )
        if not capsule_result.ok:
            return capsule_result
        context_rel = task.get("context_package_path")
        if not context_rel:
            return gates.Result(False, "missing context_package_path")
        context_file = Path(ws) / context_rel
        if not context_file.exists():
            return gates.Result(False, f"missing context package: {context_rel}")
        import hashlib
        observed = hashlib.sha256(context_file.read_text(encoding="utf-8").encode("utf-8")).hexdigest()
        if observed != task.get("context_package_hash"):
            return gates.Result(False, "context package hash mismatch")
        return gates.validate_context_package(context_file.read_text(encoding="utf-8"))
    return brief


def _run_implementation_or_fix(ws, gates, task, runner, max_retries, dispatch_type,
                               starting_attempt=0):
    task_id = task["id"]
    result_path = Path(ws) / task["result_path"]
    last_reason = None
    for attempt in range(starting_attempt, max_retries + 1):
        queue_doc = _read_queue(ws)
        current = _task_by_id(queue_doc, task_id)
        brief = _validate_brief(ws, gates, current, queue_doc)
        if not brief.ok:
            _update_task(ws, task_id, status="blocked", blocked_reason=brief.reason)
            return {"status": "blocked", "reason": brief.reason, "attempt": attempt}

        if result_path.exists():
            result_path.unlink()
        update_path = result_path.with_name(f"{task_id}.EVIDENCE_UPDATE_REQUEST.yaml")
        if update_path.exists():
            update_path.unlink()
        workflow_request_path = result_path.with_name(
            f"{task_id}.EXTERNAL_WORKFLOW_REQUEST.yaml"
        )
        if workflow_request_path.exists():
            workflow_request_path.unlink()
        _update_task(ws, task_id, status="in_progress", attempts=attempt)
        exit_code, output = _dispatch_to_runner(
            ws, dispatch_type, current, current["brief_path"], current["result_path"],
            runner, attempt=attempt,
        )
        if workflow_request_path.exists():
            ok, reason, request = validate_external_workflow_request(
                workflow_request_path.read_text(encoding="utf-8"),
                external_workflow_contract(current),
            )
            _update_task(
                ws, task_id, status="blocked",
                blocked_reason="EXTERNAL_WORKFLOW_REQUEST" if ok else reason,
                external_workflow_request=str(workflow_request_path.relative_to(ws)),
            )
            return {
                "status": "blocked",
                "reason": "EXTERNAL_WORKFLOW_REQUEST" if ok else reason,
                "request": request,
                "attempt": attempt,
            }
        if update_path.exists():
            request = gates.validate_evidence_update_request(update_path.read_text(encoding="utf-8"))
            if request.ok:
                _update_task(ws, task_id, status="blocked", blocked_reason="EVIDENCE_UPDATE_REQUEST",
                             evidence_update_request=str(update_path.relative_to(ws)))
                return {"status": "blocked", "reason": "EVIDENCE_UPDATE_REQUEST", "attempt": attempt}
            last_reason = request.reason
        elif exit_code != 0:
            last_reason = f"{dispatch_type} exit {exit_code}: {output}"
        elif not result_path.exists():
            last_reason = f"{dispatch_type} exit 0 but did not write {current['result_path']}"
        else:
            queue_doc = _read_queue(ws)
            result = gates.validate_result_contract(
                result_path.read_text(encoding="utf-8"),
                queue_doc=queue_doc,
                task_id=task_id,
            )
            if result.ok:
                _update_task(ws, task_id, status="reviewing", result_path=current["result_path"])
                return {"status": "ready_for_review", "attempt": attempt}
            last_reason = result.reason
        if attempt >= max_retries:
            break

    _update_task(ws, task_id, status="blocked", blocked_reason=last_reason)
    return {"status": "blocked", "reason": last_reason, "attempt": max_retries}


def _run_task_review(ws, gates, task, runner, attempt):
    task_id = task["id"]
    review_rel = f"reviews/{task_id}.md"
    review_path = Path(ws) / review_rel
    if review_path.exists():
        review_path.unlink()
    exit_code, output = _dispatch_to_runner(
        ws, "task_review", task, task["result_path"], review_rel, runner, attempt=attempt,
    )
    if exit_code != 0:
        reason = f"task_review exit {exit_code}: {output}"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    if not review_path.exists():
        reason = f"task_review exit 0 but did not write {review_rel}"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    queue_doc = _read_queue(ws)
    review = gates.validate_task_review(
        review_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
        task_id=task_id,
    )
    if not review.ok:
        _update_task(ws, task_id, status="blocked", blocked_reason=review.reason)
        return {"status": "blocked", "reason": review.reason}
    verdict = _verdict(ws, review_path.read_text(encoding="utf-8"), "task")
    if verdict == "APPROVED":
        _update_task(ws, task_id, status="done", review_path=review_rel)
        return {"status": "approved"}
    if verdict != "CHANGES_REQUESTED":
        reason = "task review is malformed or has unsupported verdict"
        _update_task(ws, task_id, status="blocked", blocked_reason=reason)
        return {"status": "blocked", "reason": reason}
    _update_task(ws, task_id, status="changes_required", review_path=review_rel)
    return {"status": "changes_required"}


def _run_one_task(ws, gates, task, runner, max_retries):
    dispatch_type = "fix" if task.get("status") == "changes_required" else "implementation"
    attempt = int(task.get("attempts") or 0)
    while attempt <= max_retries:
        if task.get("status") != "reviewing":
            impl = _run_implementation_or_fix(
                ws, gates, task, runner, max_retries, dispatch_type, starting_attempt=attempt,
            )
            if impl["status"] == "blocked":
                return {"status": "blocked", "task_id": task["id"], "reason": impl["reason"]}
            attempt = impl["attempt"]
        current = _task_by_id(_read_queue(ws), task["id"])
        review = _run_task_review(ws, gates, current, runner, attempt)
        if review["status"] == "approved":
            return {"status": "done", "task_id": task["id"]}
        if review["status"] == "blocked":
            return {"status": "blocked", "task_id": task["id"], "reason": review["reason"]}
        attempt += 1
        if attempt > max_retries:
            reason = "task review requested changes after retry budget"
            _update_task(ws, task["id"], status="blocked", blocked_reason=reason)
            return {"status": "blocked", "task_id": task["id"], "reason": reason}
        task = _task_by_id(_read_queue(ws), task["id"])
        dispatch_type = "fix"
    reason = "retry budget exhausted"
    _update_task(ws, task["id"], status="blocked", blocked_reason=reason)
    return {"status": "blocked", "task_id": task["id"], "reason": reason}


def _run_final_review(ws, gates, runner):
    review_rel = "reviews/FINAL_REVIEW.md"
    review_path = Path(ws) / review_rel
    if review_path.exists():
        review_path.unlink()
    queue_doc = _read_queue(ws)
    loaded = ["generated/TASK_QUEUE.json"]
    knowledge_slice, source_anchors = [], []
    for queued in queue_doc.get("tasks") or []:
        loaded.extend([queued.get("brief_path"), queued.get("capsule_path"),
                       queued.get("result_path"), queued.get("review_path")])
        capsule_path = Path(ws) / queued["capsule_path"]
        capsule = yaml.safe_load(capsule_path.read_text(encoding="utf-8")) or {}
        knowledge_slice.extend(capsule.get("project_knowledge") or [])
        source_anchors.extend((capsule.get("knowledge_slice") or {}).get("code_evidence") or [])
    package = {
        "version": 1, "role": "reviewer", "change_id": queue_doc.get("change_id"),
        "state": "FINAL_REVIEW", "loaded_artifacts": [item for item in loaded if item],
        "knowledge_slice": knowledge_slice, "memory_slice": [],
        "source_anchors": source_anchors, "database_slice": [],
        "missing_context": [], "degradation": [], "confidence": "high",
        "freshness": {"repository_commit": (yaml.safe_load(
            (Path(ws) / "briefs" / f"{queue_doc['tasks'][0]['id']}.knowledge.yaml")
            .read_text(encoding="utf-8")) or {}).get("freshness", {}).get("repository_commit"),
                      "generated_at": datetime.fromtimestamp(
                          (Path(ws) / "generated" / "TASK_QUEUE.json").stat().st_mtime,
                          timezone.utc,
                      ).isoformat()},
    }
    context_rel = "generated/CONTEXT_PACKAGE.final-review.yaml"
    context_path = Path(ws) / context_rel
    context_text = yaml.safe_dump(package, sort_keys=False, allow_unicode=True)
    context_path.write_text(context_text, encoding="utf-8")
    context_gate = gates.validate_context_package(context_text)
    if not context_gate.ok:
        return {"status": "blocked", "reason": context_gate.reason}
    task = {
        "id": "FINAL_REVIEW", "files": {}, "depends_on": [],
        "context_package_path": context_rel,
        "context_package_hash": hashlib.sha256(context_text.encode("utf-8")).hexdigest(),
    }
    exit_code, output = _dispatch_to_runner(
        ws, "final_review", task, "generated/TASK_QUEUE.json", review_rel, runner,
    )
    if exit_code != 0:
        return {"status": "blocked", "reason": f"final_review exit {exit_code}: {output}"}
    if not review_path.exists():
        return {"status": "blocked", "reason": f"final_review exit 0 but did not write {review_rel}"}
    if _verdict(ws, review_path.read_text(encoding="utf-8"), "final") != "APPROVED":
        return {"status": "blocked", "reason": "final review is malformed or not approved"}
    final = gates.validate_final_review(
        review_path.read_text(encoding="utf-8"),
        queue_doc=queue_doc,
    )
    if not final.ok:
        return {"status": "blocked", "reason": final.reason}
    # W5: the final review must report whole-change knowledge impact.
    ki_path = Path(ws) / "reviews" / "KNOWLEDGE_IMPACT.yaml"
    if not ki_path.exists():
        return {"status": "blocked", "reason": "final review missing reviews/KNOWLEDGE_IMPACT.yaml"}
    ki = gates.validate_knowledge_impact(ki_path.read_text(encoding="utf-8"))
    if not ki.ok:
        return {"status": "blocked", "reason": ki.reason}
    return {"status": "done"}


def run_queue(ws, repo_root, runner, max_retries=2, runtime_policy=None):
    ws = Path(ws)
    gates = _load("gates", "gate-check/gates.py")
    if runtime_policy is not None:
        queue = _read_queue(ws)
        queue["runtime_limits"] = runtime_policy.token_budget
        _write_queue(ws, queue, expected_generation=int(queue.get("generation") or 0))

    while True:
        doc = _read_queue(ws)
        blocked = next((t for t in doc.get("tasks", []) if t.get("status") == "blocked"), None)
        if blocked:
            return {
                "status": "blocked",
                "task_id": blocked.get("id"),
                "reason": blocked.get("blocked_reason") or "task blocked",
            }
        task = _next_pending_task(doc)
        if task is None:
            if all(t.get("status") == "done" for t in doc.get("tasks", [])):
                final = _run_final_review(ws, gates, runner)
                return final
            return {"status": "blocked", "reason": "no runnable task"}
        out = _run_one_task(ws, gates, task, runner, max_retries)
        if out["status"] == "blocked":
            return out
