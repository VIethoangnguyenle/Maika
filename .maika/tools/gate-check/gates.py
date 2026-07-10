"""Deterministic evidence validators for decision-point gates.

Each returns a Result(ok, reason). They check the CONTENT (evidence) of a
checkpoint/report — never whether a tool was 'called'. See spec §2.
"""
import os
import re
from dataclasses import dataclass

import yaml


@dataclass
class Result:
    ok: bool
    reason: str = ""


_RULE_ID = re.compile(r"\b[A-Z]{2,3}-\d+\b")              # e.g. SP-6, HP-12, IW-05
_NODE_ID = re.compile(r"\bnode_id\s*[:=]", re.IGNORECASE)
_BLAST = re.compile(r"blast-radius", re.IGNORECASE)
# Degrade line must be COMPACT (the canonical "KG unavailable — grep fallback,
# MEDIUM" is ~18 chars between the anchors). The {0,40} bound rejects rambling
# prose that merely happens to contain both "KG unavailable" and "MEDIUM".
_DEGRADE = re.compile(r"KG unavailable.{0,40}MEDIUM", re.IGNORECASE)
_NUMBERS = re.compile(r"(nodes?|edges?)\s*[:=]\s*\d+", re.IGNORECASE)
# Agent-memory MCP evidence: either a health probe ("agent-memory: healthy")
# or the compact degrade line ("agent-memory unavailable — skip recall/save").
# Health probe: the canonical line is "agent-memory: healthy" — the status word
# immediately follows the label, so we anchor tightly (optional colon + spaces)
# to reject negated/stale prose like "agent-memory is not healthy".
_MEMORY_OK = re.compile(r"agent-memory:?\s*(healthy|ok|ready)\b", re.IGNORECASE)
# Degrade line: canonical is "agent-memory unavailable — skip recall/save" (~3 chars
# between anchors). Keep the bound tight (like _DEGRADE) to reject rambling prose.
_MEMORY_DEGRADE = re.compile(
    r"agent-memory unavailable.{0,15}(skip|recall|save)", re.IGNORECASE
)
# Recall evidence (pre-spec hard gate): canonical line is
#   agent-memory recall — query:"<query>" · results:<N> — ảnh hưởng reasoning
# Anchors: the literal query:"..." and a numeric results:. The {0,10} bounds
# between anchors reject rambling prose (same technique as _DEGRADE).
_MEMORY_RECALL = re.compile(
    r'agent-memory recall.{0,10}query:"[^"]{1,200}".{0,10}results:\s*\d+',
    re.IGNORECASE,
)
_UA_EVIDENCE = re.compile(
    r"\b(UA evidence|domain_overview|domain_flow|domain_relationships)\b",
    re.IGNORECASE,
)
_UA_DEGRADE = re.compile(
    r"UA unavailable.{0,60}(explicit override|override|approved|MEDIUM)",
    re.IGNORECASE,
)
_NO_KNOWLEDGE = re.compile(r"no approved (dna|conventions).*low", re.IGNORECASE)
_SECTION = r"##\s+{name}[ \t]*\n(.*?)(?=\n##\s|\Z)"


def _section_text(text: str, name: str) -> str:
    pattern = re.compile(_SECTION.format(name=re.escape(name)), re.DOTALL | re.IGNORECASE)
    match = pattern.search(text)
    return match.group(1).strip() if match else ""


def validate_knowledge_checkpoint(
    text: str, valid_rule_ids=None, allow_no_knowledge: bool = True
) -> Result:
    if _NO_KNOWLEDGE.search(text):
        if allow_no_knowledge:
            return Result(True)  # fresh project: no approved DNA/conventions yet → proceed at LOW confidence
        return Result(False, "governance-degrade is allowed only when knowledge-index has no matching entries")
    cited_rule_ids = set(_RULE_ID.findall(text))
    if valid_rule_ids is not None:
        valid_rule_ids = set(valid_rule_ids)
        if not cited_rule_ids.intersection(valid_rule_ids):
            return Result(False, "no valid rule-id from knowledge-index cited")
    elif not cited_rule_ids:
        return Result(False, "no rule-id (e.g. SP-6) cited")
    has_facts = bool(_NODE_ID.search(text) and _BLAST.search(text))
    if has_facts or _DEGRADE.search(text):
        return Result(True)
    return Result(False, "missing codebase evidence (node_id+blast-radius) or degrade line")


def validate_mcp_status(text: str) -> Result:
    if (
        _NUMBERS.search(text)
        or _DEGRADE.search(text)
        or _MEMORY_OK.search(text)
        or _MEMORY_DEGRADE.search(text)
    ):
        return Result(True)
    return Result(False, "MCP status lacks probe numbers and degrade line ('Runtime Ready' alone is invalid)")


# A file path: an optional dir prefix + a filename with an extension. Stops at
# ':' so "base.py:100" yields "base.py". Matches repo-relative, absolute, and
# bare (no directory) filenames.
_FILE_PATH = re.compile(r"/?(?:[\w.-]+/)*[\w.-]+\.[A-Za-z0-9]+")

_CODE_EXT = {
    "py", "js", "jsx", "ts", "tsx", "go", "rs", "java", "kt", "rb",
    "c", "h", "cc", "cpp", "hpp", "cs", "php", "scala", "swift", "m", "mm",
}


def _is_code(path: str) -> bool:
    return path.rsplit(".", 1)[-1].lower() in _CODE_EXT if "." in path else False


def _under(path: str, root: str) -> bool:
    p = os.path.normpath(path)
    r = os.path.normpath(root)
    return p == r or p.startswith(r + os.sep)


_CBM_ERROR = re.compile(
    r"project is required|no projects indexed|not indexed|connection refused|"
    r"index_status|ECONNREFUSED|codebase-memory-mcp.*error",
    re.IGNORECASE,
)


def _section(text: str, needle: str) -> str:
    """Body under the first heading (## / ### / ####) containing needle, up to the
    next heading of the SAME OR HIGHER level. Deeper sub-headings do not truncate."""
    out, collecting, level = [], False, 0
    for line in text.splitlines():
        s = line.strip()
        m = re.match(r"^(#{2,6})\s", s)
        if m:
            h = len(m.group(1))
            if collecting and h <= level:
                break
            if not collecting and needle.lower() in s.lower():
                collecting, level = True, h
            continue
        if collecting:
            out.append(line)
    return "\n".join(out)


def _parse_node_table(text: str):
    """node_id (2nd column) of each real row in the §2.3 Key Components table."""
    ids = []
    for line in _section(text, "Key Components").splitlines():
        line = line.strip()
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) < 2:
            continue
        nid = cells[1]
        if not nid or nid == "node_id" or nid == "..." or set(nid) <= set("-"):
            continue
        ids.append(nid)
    return ids


def _section_files(text: str, needles):
    files = set()
    for needle in needles:
        files.update(_FILE_PATH.findall(_section(text, needle)))
    return files


def _abs(path: str, repo_root):
    return path if path.startswith("/") else (os.path.join(repo_root, path) if repo_root else path)


def _project_for(path, indexed_projects):
    for proj in indexed_projects:
        if _under(path, proj["root_path"]):
            return proj
    return None


def validate_code_evidence(text, indexed_projects=None, verified_node_files=None,
                           repo_root=None, probe_ok=True) -> Result:
    """Positive code-evidence gate (see R-Tool-5). Every section-scoped (§2.2/§2.3/§4)
    code-fact about a file in an indexed project must be backed by a §2.3 node_id that
    cbm verifies exists. Catches confessed grep (A), silent grep (B), fabricated node (C)."""
    verified_node_files = verified_node_files or {}
    if not indexed_projects:
        return Result(True)                      # nothing indexed → grep legit
    if not probe_ok:                             # cbm probe failed → fail-open only with real error
        if _CBM_ERROR.search(text):
            return Result(True)
        return Result(False, "cbm probe failed; embed the real cbm error output to justify degrade")
    for nid in _parse_node_table(text):          # (C) every §2.3 node must exist
        if nid not in verified_node_files:
            return Result(False, f"§2.3 node_id '{nid}' not found in cbm graph (fabricated or wrong project)")
    verified_abs = {os.path.normpath(_abs(f, repo_root)) for f in verified_node_files.values()}
    verified_base = {os.path.basename(p) for p in verified_abs}
    for raw in _section_files(text, ("Entry Points", "Phát hiện")):   # (B) indexed-file facts need a node
        if not _is_code(raw):
            continue                              # cbm indexes code symbols, not md/yaml/json/config
        if "/" in raw:                             # path form: map to a project by root, require exact node file
            path = os.path.normpath(_abs(raw, repo_root))
            proj = _project_for(path, indexed_projects)
            if not proj:
                continue                           # un-indexed (e.g. upstream not indexed) → grep legit
            if path not in verified_abs:
                return Result(False, f"'{raw}' (indexed project '{proj['name']}') has no verified §2.3 node — trace via cbm, don't grep")
        else:                                      # bare filename: cover by basename against verified nodes
            if os.path.basename(raw) not in verified_base:
                return Result(False, f"'{raw}' has no verified §2.3 node (cite full path or add the cbm node) — don't grep")
    return Result(True)


def validate_memory_recall(text: str) -> Result:
    """Pre-spec recall evidence (R-Tool-6): either a real recall line
    (query + numeric result count) or the canonical degrade line."""
    if _MEMORY_RECALL.search(text) or _MEMORY_DEGRADE.search(text):
        return Result(True)
    return Result(False, "no agent-memory recall evidence (query+results) or degrade line")


def validate_phase_chain(text: str) -> Result:
    seen = [n for n in (1, 2, 3) if re.search(rf"Pha\s*{n}\s*DONE", text)]
    if seen and seen == list(range(1, max(seen) + 1)):
        return Result(True)
    return Result(False, f"phase markers not contiguous from 1: found {seen}")


def validate_apply_gate(text: str) -> Result:
    """Apply-entry evidence (R-Flow-2): spec phase complete + no open blocker.

    PASS requires a 'Pha 2 DONE' marker and that every '[BLOCKER-ARCH]' has a
    matching '[BLOCKER-ARCH RESOLVED]'. Unlike validate_phase_chain, a 'Pha 1
    DONE'-only transparency does NOT pass — code writes need the spec phase done.
    """
    if not re.search(r"Pha\s*2\s*DONE", text):
        return Result(False, "apply-gate: no 'Pha 2 DONE' marker (spec phase not complete)")
    opens = text.count("[BLOCKER-ARCH]")
    resolved = text.count("[BLOCKER-ARCH RESOLVED]")
    if opens > resolved:
        return Result(False, f"apply-gate: {opens - resolved} unresolved [BLOCKER-ARCH]")
    return Result(True)


def validate_handoff_slice(text: str) -> Result:
    m = re.search(r"##\s+Applicable DNA/Conventions[ \t]*\n(.*?)(?=\n##\s|\Z)", text, re.DOTALL)
    if not m or not _RULE_ID.search(m.group(1)):
        return Result(False, "handoff missing non-empty 'Applicable DNA/Conventions' with rule-ids")
    return Result(True)


def validate_implementation_context(text: str) -> Result:
    applicable = _section_text(text, "Applicable DNA/Conventions")
    if not applicable or not _RULE_ID.search(applicable):
        return Result(False, "implementation context missing Applicable DNA/Conventions rule-ids")
    evidence = _section_text(text, "Evidence")
    if not evidence:
        return Result(False, "implementation context missing Evidence section")
    has_ua = bool(_UA_EVIDENCE.search(evidence) or _UA_DEGRADE.search(evidence))
    has_codebase = bool((_NODE_ID.search(evidence) and _BLAST.search(evidence)) or _DEGRADE.search(evidence))
    if not has_ua:
        return Result(False, "implementation context missing UA evidence or explicit UA degrade override")
    if not has_codebase and _UA_DEGRADE.search(evidence):
        return Result(False, "implementation context with UA degrade also needs codebase evidence or KG degrade")
    allowed = _section_text(text, "Allowed Files")
    if not allowed:
        return Result(False, "implementation context missing Allowed Files section")
    return Result(True)


def _section_has_text(text: str, name: str) -> bool:
    return bool(_section_text(text, name))


_TM_VALID = ("none", "captured", "declined", "pending-confirmation")
_TM_PLACEHOLDERS = {"fill before archive"}


def _tm_field(body: str, key: str, multiline: bool = False) -> str:
    if multiline:
        m = re.search(rf"^{key}:[ \t]*(.*(?:\n[ \t]+.*)*)", body, re.MULTILINE)
    else:
        m = re.search(rf"^{key}:[ \t]*(.*)$", body, re.MULTILINE)
    return m.group(1).strip() if m else ""


def validate_teaching_moment(text: str) -> Result:
    """R-DNA-7 pre-archive acknowledgment. Structural invariants only — cannot
    prove a teaching moment actually occurred (honor-code; see spec C-24)."""
    m = re.search(_SECTION.format(name=re.escape("Teaching Moment Check")), text, re.DOTALL | re.IGNORECASE)
    if not m:
        return Result(False, "Teaching Moment Check section missing. Add section before archive.")
    body = m.group(1)
    status = _tm_field(body, "status")
    if status not in _TM_VALID:
        return Result(False, "status must be one of none, captured, declined, pending-confirmation.")
    if status == "none":
        note = _tm_field(body, "note")
        if not note or note.lower() in _TM_PLACEHOLDERS:
            return Result(False, "status none requires a non-empty active assertion note.")
    elif status == "captured":
        if not _tm_field(body, "target_updates", multiline=True):
            return Result(False, "status captured requires non-empty target_updates.")
    elif status in ("declined", "pending-confirmation"):
        if "[R-DNA-7]" not in body:
            return Result(False, f"status {status} requires [R-DNA-7] WARN and reason.")
        if not _tm_field(body, "reason"):
            return Result(False, f"status {status} requires [R-DNA-7] WARN and reason.")
    return Result(True)


_ARCHIVE_BLOCKED = {"blocked-by-arch", "blocked-by-data"}
_RESET_ALLOWED = {"completed", "cancelled", "stashed"}
_WORD = re.compile(r"[A-Za-z0-9_\-/]+", re.IGNORECASE)
_STOPWORDS = {
    "the", "and", "for", "with", "that", "this", "from", "when", "then",
    "user", "system", "can", "must", "should", "error", "validation",
    "api", "id", "missing", "returns",
}


def validate_archive_ready(text: str) -> Result:
    """Pre-archive guard: refuse to archive/reset while the task is blocked.
    Reads phase_state from the '## Phase State' section. Deterministic check;
    honor-code trigger (archive is not hook-intercepted)."""
    m = re.search(_SECTION.format(name=re.escape("Phase State")), text, re.DOTALL | re.IGNORECASE)
    section = m.group(1) if m else ""
    ps = re.search(r"phase_state:\s*(\S+)", section)
    phase_state = ps.group(1).strip() if ps else ""
    if phase_state in _ARCHIVE_BLOCKED:
        return Result(False, f"archive blocked: phase_state={phase_state} — resolve the blocker first")
    return Result(True)


def validate_reset_ready(text: str) -> Result:
    """Refuse destructive active-context reset unless the task is closed or stashed
    and the Teaching Moment Check is structurally valid."""
    m = re.search(_SECTION.format(name=re.escape("Phase State")), text, re.DOTALL | re.IGNORECASE)
    section = m.group(1) if m else ""
    ps = re.search(r"phase_state:\s*(\S+)", section)
    phase_state = ps.group(1).strip() if ps else ""
    if phase_state in _ARCHIVE_BLOCKED:
        return Result(False, f"reset blocked: phase_state={phase_state} — resolve the blocker first")
    if phase_state not in _RESET_ALLOWED:
        return Result(False, "reset requires phase_state completed, cancelled, or stashed")
    tm = validate_teaching_moment(text)
    if not tm.ok:
        return Result(False, f"reset requires valid Teaching Moment Check: {tm.reason}")
    return Result(True)


def _heading_section(text: str, heading: str) -> str:
    lines = text.splitlines()
    collecting = False
    body = []
    needle = heading.lower()
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("## "):
            if collecting:
                break
            collecting = needle in stripped.lower()
            continue
        if collecting:
            body.append(line)
    return "\n".join(body).strip()


def _bullets(section: str):
    items = []
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")):
            value = stripped[2:].strip()
            if value and not value.startswith("<!--"):
                items.append(value)
    return items


def _keywords(text: str):
    words = {w.lower() for w in _WORD.findall(text)}
    return {w for w in words if len(w) >= 4 and w not in _STOPWORDS}


def _covered(item: str, spec_text: str) -> bool:
    item_words = _keywords(item)
    if not item_words:
        return True
    spec_words = _keywords(spec_text)
    needed = 1 if len(item_words) <= 2 else max(2, min(4, len(item_words)))
    return len(item_words.intersection(spec_words)) >= needed


def validate_ac_coverage(requirement_text: str, spec_text: str = "") -> Result:
    section = _heading_section(requirement_text, "Acceptance Criteria")
    items = _bullets(section)
    if not items:
        return Result(True)
    missing = [item for item in items if not _covered(item, spec_text)]
    if missing:
        return Result(False, "uncovered AC: " + "; ".join(missing))
    return Result(True)


def validate_integration_coverage(requirement_text: str, spec_text: str = "") -> Result:
    section = _heading_section(requirement_text, "Integrations")
    if not section:
        return Result(True)
    items = []
    for line in section.splitlines():
        stripped = line.strip()
        heading = re.match(r"^###+\s+Integration:\s*(.+)$", stripped, re.IGNORECASE)
        if heading:
            items.append(heading.group(1).strip())
        elif stripped.startswith("- Integration:"):
            items.append(stripped.split(":", 1)[1].strip())
    if not items:
        return Result(True)
    missing = [item for item in items if not _covered(item, spec_text)]
    if missing:
        return Result(False, "uncovered integration(s): " + "; ".join(missing))
    return Result(True)


def validate_context_request(text: str) -> Result:
    """Validate a subagent CONTEXT_REQUEST (YAML schema shared with the
    microloop-orchestrator contract: request_type=='context' + substantive
    'missing' evidence and a 'blocked_reason')."""
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return Result(False, f"context request is not valid YAML: {exc}")
    if not isinstance(data, dict):
        return Result(False, "context request must be a YAML mapping")
    if data.get("request_type") != "context":
        return Result(False, "context request must set request_type: context")
    missing = data.get("missing")
    if not isinstance(missing, list) or not missing:
        return Result(False, "context request must list non-empty 'missing' evidence")
    if not str(data.get("blocked_reason") or "").strip():
        return Result(False, "context request must explain 'blocked_reason'")
    return Result(True)


def validate_node_checkpoint(text: str) -> Result:
    required = ("Files Changed", "Requirement Satisfied", "Evidence Used", "Verification")
    missing = [name for name in required if not _section_has_text(text, name)]
    if missing:
        return Result(False, f"node checkpoint missing sections: {', '.join(missing)}")
    if not _RULE_ID.search(text):
        return Result(False, "node checkpoint missing rule-id evidence")
    return Result(True)

_PLACEHOLDER = re.compile(r"\b(TODO|TBD|FIXME)\b")
_VALID_MODES = {"exact", "guided", "intent"}
_SHA256_FMT = re.compile(r"^sha256:[0-9a-f]{64}$")
VALID_CHANGE_CLASSES = {"trivial", "small", "standard", "architectural"}


def validate_change_workspace(text: str) -> Result:
    """Gate `vnext-workspace` (v2 §22 change-workspace, minimal W1)."""
    doc = yaml.safe_load(text) or {}
    for key in ("change_id", "class", "title", "created_at"):
        if not doc.get(key):
            return Result(False, f"CHANGE.yaml missing {key}")
    if doc["class"] not in VALID_CHANGE_CLASSES:
        return Result(False, f"bad change class: {doc['class']}")
    return Result(True)


def validate_intent(text: str, change_text: str = "") -> Result:
    """Gate `intent` — W2 consumer for INTENT.md."""
    change = yaml.safe_load(change_text) or {}
    klass = change.get("class", "standard")
    body = (text or "").strip()
    summary = _section_text(text or "", "Summary")
    if not summary:
        match = re.search(r"(?im)^Summary:\s*(.+)$", text or "")
        summary = match.group(1).strip() if match else ""
    if klass in {"standard", "architectural"} and len(body) < 20:
        return Result(False, "intent summary required for standard/architectural change")
    if klass in {"standard", "architectural"} and len(summary) < 10:
        return Result(False, "intent summary content required for standard/architectural change")
    if klass not in VALID_CHANGE_CLASSES:
        return Result(False, f"bad change class: {klass}")
    return Result(True)


def validate_exploration_evidence(text: str, evidence_text: str = "", repo_root=None) -> Result:
    """Gate `exploration-evidence` — three-lens grounding + claim manifest.

    When ``repo_root`` is given, every verified ``exact_code_fact`` source is
    checked for authenticity: the file must exist, its current sha256 must match
    the declared ``file_hash``, and the ``symbol`` must appear in the file. This
    rejects fake path, fake symbol, and fabricated/stale hash (DoD #9, #27)."""
    grounding = yaml.safe_load(text) or {}
    for lens in ("codebase", "business", "conventions"):
        if not isinstance(grounding.get(lens), dict) or not grounding[lens]:
            return Result(False, f"GROUNDING.yaml missing {lens} lens")
    codebase = grounding["codebase"]
    for key in ("entry_points", "current_flow", "extension_seams", "related_tests", "blast_radius"):
        if not codebase.get(key):
            return Result(False, f"GROUNDING.yaml codebase.{key} required")
    business = grounding["business"]
    for key in ("terminology", "actors", "rules", "states_and_transitions", "evidence_sources"):
        if not business.get(key):
            return Result(False, f"GROUNDING.yaml business.{key} required")
    conventions = grounding["conventions"]
    for key in ("applicable_rule_ids", "architecture_patterns", "naming_patterns", "testing_patterns"):
        if not conventions.get(key):
            return Result(False, f"GROUNDING.yaml conventions.{key} required")
    evidence = yaml.safe_load(evidence_text) or {}
    claims = evidence.get("claims")
    if not isinstance(claims, list) or not claims:
        return Result(False, "EVIDENCE_MANIFEST.yaml claims required")
    ids = set()
    for claim in claims:
        cid = claim.get("id")
        if not cid:
            return Result(False, "claim id required")
        if cid in ids:
            return Result(False, f"duplicate claim id: {cid}")
        ids.add(cid)
        if claim.get("status") not in {"verified", "inferred", "conflicting", "unverified", "stale"}:
            return Result(False, f"{cid}: invalid status")
        if claim.get("category") == "exact_code_fact" and claim.get("status") == "verified":
            sources = claim.get("sources")
            if not isinstance(sources, list) or not sources:
                return Result(False, f"{cid}: verified code fact requires sources")
            for i, source in enumerate(sources, 1):
                file = source.get("file")
                symbol = source.get("symbol")
                fhash = str(source.get("file_hash", ""))
                if not file:
                    return Result(False, f"{cid}: source {i} missing file")
                if not symbol:
                    return Result(False, f"{cid}: source {i} missing symbol")
                if not _SHA256_FMT.match(fhash):
                    return Result(False, f"{cid}: source {i} missing file_hash")
                if repo_root:
                    import hashlib
                    p = file if os.path.isabs(file) else os.path.join(repo_root, file)
                    if not os.path.isfile(p):
                        return Result(False, f"{cid}: source {i} file not found: {file}")
                    raw = open(p, "rb").read()
                    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
                    if actual != fhash:
                        return Result(False, f"{cid}: source {i} file_hash mismatch (stale/fabricated): {file}")
                    if symbol not in raw.decode("utf-8", errors="replace"):
                        return Result(False, f"{cid}: source {i} symbol '{symbol}' not found in {file}")
    return Result(True)


_SMALL_SPEC_SECTIONS = (
    "Goal", "Current Behavior", "Desired Behavior", "Acceptance Criteria",
    "Relevant Evidence", "Evidence References",
)
_FULL_SPEC_SECTIONS = (
    "Goal", "Context", "Current Behavior", "Desired Behavior", "Actors",
    "Functional Requirements", "Business Rules", "States and Transitions",
    "Architecture", "Components and Boundaries", "Data Flow",
    "API and Contract Changes", "Persistence Changes", "Event and Async Behavior",
    "Error Handling", "Security and Authorization", "Observability and Audit",
    "Migration", "Rollback", "Testing Strategy", "Acceptance Criteria",
    "Non-goals", "Risks", "Evidence References",
)


def _has_heading(text: str, heading: str) -> bool:
    return bool(re.search(rf"^##\s+{re.escape(heading)}\s*$", text, re.MULTILINE))


def validate_vnext_spec(text: str, change_class: str = "standard") -> Result:
    """Gate `spec` — class-aware W2 spec contract."""
    if change_class not in VALID_CHANGE_CLASSES:
        return Result(False, f"bad change class: {change_class}")
    if change_class == "trivial":
        return Result(True)
    required = _SMALL_SPEC_SECTIONS if change_class == "small" else _FULL_SPEC_SECTIONS
    missing = [h for h in required if not _has_heading(text, h)]
    if missing:
        return Result(False, f"SPEC.md missing sections: {', '.join(missing)}")
    if not re.search(r"\bAC-\d+\b", _section_text(text, "Acceptance Criteria")):
        return Result(False, "SPEC.md Acceptance Criteria must include AC ids")
    if not re.search(r"\b[A-Z]+-\d+\b", _section_text(text, "Evidence References")):
        return Result(False, "SPEC.md Evidence References must cite claim ids")
    return Result(True)


def _ac_ids(spec_text: str) -> set:
    return set(re.findall(r"\bAC-\d+\b", _section_text(spec_text or "", "Acceptance Criteria")))


def validate_vnext_plan(
    text, plan_doc=None, repo_root=None, spec_sha256=None, evidence_sha256=None, spec_text=None
) -> Result:
    """Gate `vnext-plan` — mechanical subset W1 (v2 §26 W1; full §16 là W2+)."""
    if plan_doc is None:
        return Result(False, "plan_doc required (cli parses via plan_parser)")
    import subprocess
    from pathlib import Path
    meta, tasks = plan_doc["meta"], plan_doc["tasks"]
    if spec_sha256 is not None and meta.get("spec_hash") != f"sha256:{spec_sha256}":
        return Result(False, "spec_hash mismatch: plan compiled against different SPEC.md")
    if evidence_sha256 is not None and meta.get("evidence_hash") != f"sha256:{evidence_sha256}":
        return Result(False, "evidence_hash mismatch: plan compiled against different EVIDENCE_MANIFEST.yaml")
    if not _SHA256_FMT.match(str(meta.get("evidence_hash", ""))):
        return Result(False, "evidence_hash must be sha256:<64hex> (manifest match arrives W2)")
    if repo_root:
        probe = subprocess.run(["git", "cat-file", "-t", str(meta["base_commit"])],
                               cwd=repo_root, capture_output=True, text=True)
        if probe.returncode != 0 or probe.stdout.strip() != "commit":
            return Result(False, f"base_commit not resolvable: {meta['base_commit']}")
    ids = [t["id"] for t in tasks]
    if len(ids) != len(set(ids)):
        return Result(False, "duplicate task ids")
    known = set(ids)
    for t in tasks:
        h = t["header"]
        if h.get("implementation_mode") not in _VALID_MODES:
            return Result(False, f"{t['id']}: bad implementation_mode")
        for dep in h.get("depends_on", []) or []:
            if dep not in known:
                return Result(False, f"{t['id']}: unknown dep {dep}")
        ver = h.get("verification") or {}
        if not ver.get("command") or not ver.get("expected"):
            return Result(False, f"{t['id']}: verification.command/expected required")
        if _PLACEHOLDER.search(t["section_text"]):
            return Result(False, f"{t['id']}: placeholder TODO/TBD/FIXME in section")
        files = h.get("files") or {}
        if repo_root:
            for key in ("modify", "delete", "test"):
                for p in files.get(key, []) or []:
                    if not (Path(repo_root) / p).exists():
                        return Result(False, f"{t['id']}: files.{key} missing on disk: {p}")
            for path, names in (h.get("symbols") or {}).items():
                target = Path(repo_root) / path
                if not target.exists():
                    return Result(False, f"{t['id']}: symbol file missing: {path}")
                content = target.read_text(encoding="utf-8", errors="replace")
                for name in names or []:
                    if name not in content:
                        return Result(False, f"{t['id']}: symbol not found: {name} in {path}")
    if spec_text:
        plan_body = "\n".join(t["section_text"] for t in tasks)
        missing_ac = sorted(ac for ac in _ac_ids(spec_text) if ac not in plan_body)
        if missing_ac:
            return Result(False, f"acceptance criteria missing from plan tasks: {', '.join(missing_ac)}")
    # Validate the dependency graph with a compact Kahn pass.
    indeg = {i: 0 for i in ids}
    for t in tasks:
        for _ in t["header"].get("depends_on", []) or []:
            indeg[t["id"]] += 1
    ready = [i for i, d in indeg.items() if d == 0]
    seen = 0
    while ready:
        cur = ready.pop()
        seen += 1
        for t in tasks:
            if cur in (t["header"].get("depends_on") or []):
                indeg[t["id"]] -= 1
                if indeg[t["id"]] == 0:
                    ready.append(t["id"])
    if seen != len(ids):
        return Result(False, "dependency cycle in tasks")
    return Result(True)


def validate_brief_integrity(text: str, queue_doc=None) -> Result:
    """Gate `brief-integrity` (v2 §22): hash khớp manifest -> prevent silent edits."""
    if not queue_doc:
        return Result(False, "queue_doc required")
    try:
        header_text, _, body = text.partition("\n---\n")
        header = yaml.safe_load(header_text) or {}
        if not isinstance(header, dict):
            return Result(False, "brief header must be a dict")
    except Exception as e:
        return Result(False, f"bad brief format: {e}")
    tid = header.get("task_id")
    if not tid:
        return Result(False, "missing task_id in brief header")
    if header.get("plan_sha256") != queue_doc.get("plan_sha256"):
        return Result(False, "stale plan: plan_sha256 mismatch")
    task_info = next((t for t in queue_doc.get("tasks", []) if t.get("id") == tid), None)
    if not task_info:
        return Result(False, f"task_id {tid} not in queue")
    import hashlib
    actual_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    if actual_hash != task_info.get("brief_hash"):
        return Result(False, "brief_hash mismatch: body was edited after plan compilation")
    return Result(True)


def validate_result_contract(text: str, queue_doc=None, task_id=None) -> Result:
    """Gate `result-contract` (v2 §22): Kết quả run khớp files manifest + verification pass."""
    if not queue_doc or not task_id:
        return Result(False, "queue_doc and task_id required")
    try:
        res = yaml.safe_load(text) or {}
    except Exception as e:
        return Result(False, f"bad result format: {e}")
    if not isinstance(res, dict):
        return Result(False, "result contract must be a mapping")
    if res.get("task_id") != task_id:
        return Result(False, f"task_id mismatch: expected {task_id}, got {res.get('task_id')}")
    if res.get("status") != "success":
        return Result(False, f"task did not report success (status: {res.get('status')})")
    ver = res.get("verification") or {}
    if not ver.get("passed"):
        return Result(False, "verification failed (passed != true)")
    task_info = next((t for t in queue_doc.get("tasks", []) if t.get("id") == task_id), None)
    if not task_info:
        return Result(False, f"task_id {task_id} not in queue")
    expected_files = task_info.get("files") or {}
    actual_files = res.get("files") or {}
    for key in ("create", "modify", "delete", "test"):
        if set(expected_files.get(key) or []) != set(actual_files.get(key) or []):
            return Result(False, f"files mismatch on {key}")
    return Result(True)


def _field_value(text: str, name: str):
    match = re.search(rf"^{re.escape(name)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    return match.group(1).strip() if match else None


def validate_task_review(text: str, queue_doc=None, task_id=None) -> Result:
    """Gate `task-review`: one task review must name the task and return a verdict."""
    if not queue_doc or not task_id:
        return Result(False, "queue_doc and task_id required")
    task_info = next((t for t in queue_doc.get("tasks", []) if t.get("id") == task_id), None)
    if not task_info:
        return Result(False, f"task_id {task_id} not in queue")
    reviewed_id = _field_value(text, "TASK_ID")
    if reviewed_id != task_id:
        return Result(False, f"TASK_ID mismatch: expected {task_id}, got {reviewed_id}")
    verdict = _field_value(text, "VERDICT")
    if verdict not in {"APPROVED", "CHANGES_REQUIRED"}:
        return Result(False, "review verdict must be APPROVED or CHANGES_REQUIRED")
    return Result(True)


def validate_final_review(text: str, queue_doc=None) -> Result:
    """Gate `final-review`: whole-change review only after every task was reviewed."""
    if not queue_doc:
        return Result(False, "queue_doc required")
    tasks = queue_doc.get("tasks") or []
    if not tasks:
        return Result(False, "TASK_QUEUE has no tasks")
    for task in tasks:
        if task.get("status") != "done":
            return Result(False, f"{task.get('id')}: task is not done")
        if not task.get("review_path"):
            return Result(False, f"{task.get('id')}: task lacks review")
    verdict = _field_value(text, "VERDICT")
    if verdict not in {"APPROVED", "CHANGES_REQUIRED"}:
        return Result(False, "final review verdict must be APPROVED or CHANGES_REQUIRED")
    if verdict != "APPROVED":
        return Result(False, "final review has unresolved findings")
    return Result(True)


# ── W2 grounding-package validators (query plan, tool health, conflicts, ──────
#    coverage, database context). Pure: capability membership is passed in.

def validate_query_plan(text, valid_capabilities=None, coverable_evidence=None) -> Result:
    """Gate `query-plan` — every question declares real capabilities and its
    required evidence types are coverable by some capability (or the question is
    explicitly blocked with a reason). Rejects fabricated capability names and
    evidence types no provider can supply."""
    doc = yaml.safe_load(text) or {}
    questions = doc.get("questions")
    if not isinstance(questions, list) or not questions:
        return Result(False, "QUERY_PLAN.yaml requires a non-empty questions list")
    ids = set()
    for q in questions:
        qid = q.get("id")
        if not qid:
            return Result(False, "query-plan question missing id")
        if qid in ids:
            return Result(False, f"duplicate question id: {qid}")
        ids.add(qid)
        if not str(q.get("question") or "").strip():
            return Result(False, f"{qid}: question text required")
        caps = q.get("required_capabilities")
        if not isinstance(caps, list) or not caps:
            return Result(False, f"{qid}: required_capabilities required")
        if valid_capabilities is not None:
            for c in caps:
                if c not in valid_capabilities:
                    return Result(False, f"{qid}: unknown capability '{c}'")
        etypes = q.get("required_evidence_types")
        if not isinstance(etypes, list) or not etypes:
            return Result(False, f"{qid}: required_evidence_types required")
        status = q.get("status", "pending")
        if status not in {"pending", "answered", "blocked"}:
            return Result(False, f"{qid}: invalid status '{status}'")
        if status == "blocked":
            if not str(q.get("blocked_reason") or "").strip():
                return Result(False, f"{qid}: blocked question requires blocked_reason")
            continue
        if coverable_evidence is not None:
            for e in etypes:
                if e not in coverable_evidence:
                    return Result(False, f"{qid}: evidence type '{e}' not coverable by any capability")
    return Result(True)


def validate_tool_health(text) -> Result:
    """Gate `tool-health` — a `ready` provider must carry a real probe with
    observed output and freshness (registration != data); a degraded/unavailable
    provider must carry a structured degradation record. No silent 'ready'."""
    doc = yaml.safe_load(text) or {}
    providers = doc.get("providers")
    if not isinstance(providers, dict) or not providers:
        return Result(False, "TOOL_HEALTH.yaml requires a non-empty providers map")
    for name, p in providers.items():
        if not isinstance(p, dict):
            return Result(False, f"{name}: provider must be a mapping")
        status = p.get("status")
        if status not in {"ready", "degraded", "unavailable", "unsupported"}:
            return Result(False, f"{name}: invalid status '{status}'")
        if status == "ready":
            probe = p.get("probe")
            if not isinstance(probe, dict) or not probe.get("operation"):
                return Result(False, f"{name}: ready status requires a real probe (operation)")
            if not str(probe.get("observed") or "").strip():
                return Result(False, f"{name}: ready probe requires observed output (registration != data)")
            if not str(p.get("freshness") or "").strip():
                return Result(False, f"{name}: ready status requires freshness")
        elif status in {"degraded", "unavailable"}:
            deg = p.get("degradation")
            if not isinstance(deg, dict) or not deg:
                return Result(False, f"{name}: {status} status requires a structured degradation record")
    return Result(True)


def validate_conflicts(text) -> Result:
    """Gate `conflicts` — an `open` (unresolved material) conflict blocks design;
    resolved needs resolution + resolved_by; deferred needs a reason."""
    doc = yaml.safe_load(text) or {}
    conflicts = doc.get("conflicts")
    if conflicts is None:
        return Result(False, "CONFLICTS.yaml requires a conflicts list (use [] for none)")
    if not isinstance(conflicts, list):
        return Result(False, "conflicts must be a list")
    for c in conflicts:
        cid = c.get("id")
        if not cid:
            return Result(False, "conflict missing id")
        status = c.get("status")
        if status not in {"resolved", "deferred", "open"}:
            return Result(False, f"{cid}: invalid status '{status}'")
        if status == "open":
            return Result(False, f"{cid}: unresolved (open) conflict blocks design")
        if status == "resolved" and (not str(c.get("resolution") or "").strip() or not c.get("resolved_by")):
            return Result(False, f"{cid}: resolved conflict requires resolution + resolved_by")
        if status == "deferred" and not str(c.get("reason") or "").strip():
            return Result(False, f"{cid}: deferred conflict requires reason")
    return Result(True)


def validate_coverage(text) -> Result:
    """Gate `coverage` — question counts must be consistent and a READY verdict
    forbids missing evidence or blocked questions."""
    doc = yaml.safe_load(text) or {}
    q = doc.get("questions") or {}
    total, answered, blocked = q.get("total"), q.get("answered"), q.get("blocked")
    if not all(isinstance(x, int) for x in (total, answered, blocked)):
        return Result(False, "COVERAGE.yaml questions.total/answered/blocked must be integers")
    if answered + blocked > total:
        return Result(False, "coverage counts inconsistent: answered+blocked > total")
    missing = (doc.get("required_evidence") or {}).get("missing") or []
    verdict = doc.get("verdict")
    if verdict not in {"READY", "NEEDS_CONTEXT", "BLOCKED"}:
        return Result(False, f"invalid coverage verdict: {verdict}")
    if verdict == "READY":
        if missing:
            return Result(False, f"verdict READY but evidence still missing: {missing}")
        if blocked:
            return Result(False, "verdict READY but has blocked questions")
    return Result(True)


def validate_database_context(text) -> Result:
    """Gate `database-context` — exploration is read-only and must carry either
    real DB objects or a structured degradation record (DB unreachable)."""
    doc = yaml.safe_load(text) or {}
    if doc.get("read_only") is not True:
        return Result(False, "DATABASE_CONTEXT.yaml requires read_only: true")
    objects = doc.get("objects") or []
    degradation = doc.get("degradation")
    if not objects and not (isinstance(degradation, dict) and degradation):
        return Result(False, "DATABASE_CONTEXT.yaml requires DB objects or a structured degradation record")
    return Result(True)
