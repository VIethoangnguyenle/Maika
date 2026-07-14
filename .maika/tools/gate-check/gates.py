"""Deterministic evidence validators for decision-point gates.

Each returns a Result(ok, reason). They check the CONTENT (evidence) of a
checkpoint/report — never whether a tool was 'called'. See spec §2.
"""
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timezone

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


def _verify_source_file(repo_root, file, fhash, symbol=None):
    """Mechanically re-verify a source anchor: existence, current sha256, symbol
    presence. Returns an error string or None. Shared by exploration-evidence
    and trace-evidence (R5 — one enforcement path for source authenticity)."""
    import hashlib
    p = file if os.path.isabs(file) else os.path.join(repo_root, file)
    if not os.path.isfile(p):
        return f"file not found: {file}"
    raw = open(p, "rb").read()
    actual = "sha256:" + hashlib.sha256(raw).hexdigest()
    if actual != fhash:
        return f"file_hash mismatch (stale/fabricated): {file}"
    if symbol and symbol not in raw.decode("utf-8", errors="replace"):
        return f"symbol '{symbol}' not found in {file}"
    return None


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
                    problem = _verify_source_file(repo_root, file, fhash, symbol)
                    if problem:
                        return Result(False, f"{cid}: source {i} {problem}")
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


def _markdown_knowledge_trace(text: str):
    section = _section_text(text, "Knowledge Trace")
    match = re.search(r"```yaml\s*(.*?)```", section, re.DOTALL)
    return match.group(1) if match else ""


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
    trace = _markdown_knowledge_trace(text)
    if not trace:
        return Result(False, "SPEC.md requires canonical Knowledge Trace YAML")
    traced = validate_knowledge_trace(
        trace, valid_evidence_ids=set(re.findall(r"\b[A-Z]+-\d+\b", _section_text(text, "Evidence References")))
    )
    if not traced.ok:
        return Result(False, "SPEC.md Knowledge Trace: " + traced.reason)
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
    plan_trace = meta.get("knowledge_trace")
    if not isinstance(plan_trace, dict):
        return Result(False, "plan frontmatter requires knowledge_trace")
    traced = validate_knowledge_trace(yaml.safe_dump({"decision": plan_trace}, sort_keys=False))
    if not traced.ok:
        return Result(False, "plan Knowledge Trace: " + traced.reason)
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
    if task_info.get("context_package_path"):
        consumed = res.get("consumed") or {}
        evidence_ids = consumed.get("evidence_ids")
        knowledge_ids = consumed.get("knowledge_ids")
        if not isinstance(evidence_ids, list) or not evidence_ids:
            return Result(False, "result must record consumed.evidence_ids")
        if not isinstance(knowledge_ids, list):
            return Result(False, "result must record consumed.knowledge_ids")
        if not set(evidence_ids) <= set(task_info.get("evidence_ids") or []):
            return Result(False, "result consumed evidence IDs outside assigned capsule")
        if not set(knowledge_ids) <= set(task_info.get("knowledge_ids") or []):
            return Result(False, "result consumed knowledge IDs outside assigned capsule")
    return Result(True)


def _field_value(text: str, name: str):
    match = re.search(rf"^{re.escape(name)}\s*:\s*(.+?)\s*$", text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    if text.startswith("---\n") and "\n---\n" in text[4:]:
        try:
            front = yaml.safe_load(text[4:].split("\n---\n", 1)[0]) or {}
        except yaml.YAMLError:
            return None
        value = front.get(name.lower())
        if name == "VERDICT" and value == "CHANGES_REQUESTED":
            return "CHANGES_REQUIRED"
        return str(value) if value is not None else None
    return None


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
    if verdict == "APPROVED":
        # W5: an APPROVED review must show independent counter-evidence — the
        # reviewer anchored at least one material behavior in current source.
        counter = _section_text(text, "Counter-evidence")
        if not _FILE_PATH.search(counter):
            return Result(False, "APPROVED task review requires a Counter-evidence section with a source anchor")
        if queue_doc.get("repo_root"):
            anchors = _FILE_PATH.findall(counter)
            if not any((Path(queue_doc["repo_root"]) / anchor).exists() for anchor in anchors):
                return Result(False, "task review counter-evidence source anchor does not exist")
        trace = _markdown_knowledge_trace(text)
        traced = validate_knowledge_trace(
            trace, valid_evidence_ids=set(task_info.get("evidence_ids") or [])
        ) if trace else Result(False, "missing trace")
        if not traced.ok:
            return Result(False, "APPROVED task review requires valid Knowledge Trace: " + traced.reason)
    return Result(True)


def validate_knowledge_impact(text) -> Result:
    """Gate `knowledge-impact` — the whole-change review must report knowledge
    impact: every required lane must be present (empty list = considered, none)."""
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return Result(False, f"KNOWLEDGE_IMPACT.yaml is not valid YAML: {exc}")
    if not isinstance(doc, dict):
        return Result(False, "KNOWLEDGE_IMPACT.yaml must be a mapping")
    required = ("stale_entries", "superseded_decisions", "new_candidates",
                "graph_refresh_required", "memory_updates")
    missing = [k for k in required if k not in doc]
    if missing:
        return Result(False, f"KNOWLEDGE_IMPACT.yaml missing lanes: {', '.join(missing)}")
    if not isinstance(doc.get("graph_refresh_required"), bool):
        return Result(False, "graph_refresh_required must be a boolean")
    return Result(True)


def validate_verification_report(text) -> Result:
    """Gate `verification-report` — verification/COMMANDS.yaml must carry real
    per-command evidence (observed_output + integer exit_code + timestamp +
    pass/fail interpretation). Completion never rests on a marker alone."""
    doc = yaml.safe_load(text) or {}
    commands = doc.get("commands")
    if not isinstance(commands, list) or not commands:
        return Result(False, "verification COMMANDS.yaml requires a non-empty commands list")
    for i, rec in enumerate(commands, 1):
        if not isinstance(rec, dict):
            return Result(False, f"command {i} must be a mapping")
        name = rec.get("name")
        if not str(rec.get("observed_output") or "").strip():
            return Result(False, f"command {i} ({name}) missing observed_output")
        if not isinstance(rec.get("exit_code"), int):
            return Result(False, f"command {i} ({name}) missing integer exit_code")
        if not str(rec.get("timestamp") or "").strip():
            return Result(False, f"command {i} ({name}) missing timestamp")
        if rec.get("interpretation") not in {"pass", "fail"}:
            return Result(False, f"command {i} ({name}) invalid interpretation")
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
    counter = _section_text(text, "Counter-evidence")
    anchors = _FILE_PATH.findall(counter)
    if not anchors:
        return Result(False, "APPROVED final review requires source-anchored Counter-evidence")
    if queue_doc.get("repo_root") and not any(
        (Path(queue_doc["repo_root"]) / anchor).exists() for anchor in anchors
    ):
        return Result(False, "final review counter-evidence source anchor does not exist")
    trace = _markdown_knowledge_trace(text)
    valid_ids = {item for task in tasks for item in (task.get("evidence_ids") or [])}
    traced = validate_knowledge_trace(trace, valid_evidence_ids=valid_ids) if trace else Result(False, "missing trace")
    if not traced.ok:
        return Result(False, "APPROVED final review requires valid Knowledge Trace: " + traced.reason)
    return Result(True)


def validate_plan_review(text: str, valid_evidence_ids=None, repo_root=None) -> Result:
    verdict = _field_value(text, "VERDICT")
    if verdict not in {"APPROVED", "FINDINGS"}:
        return Result(False, "plan review verdict must be APPROVED or FINDINGS")
    if verdict == "FINDINGS":
        return Result(True)
    counter = _section_text(text, "Counter-evidence")
    anchors = _FILE_PATH.findall(counter)
    if not anchors:
        return Result(False, "APPROVED plan review requires Counter-evidence")
    if repo_root and not any((Path(repo_root) / anchor).exists() for anchor in anchors):
        return Result(False, "plan review counter-evidence anchor does not exist")
    trace = _markdown_knowledge_trace(text)
    traced = validate_knowledge_trace(trace, valid_evidence_ids=valid_evidence_ids) if trace else Result(False, "missing trace")
    return Result(False, "APPROVED plan review requires valid Knowledge Trace: " + traced.reason) if not traced.ok else Result(True)


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


def validate_database_request(text) -> Result:
    """Gate `database-request` — a persistence-sensitive change must declare
    WHERE its DB evidence comes from (harness plan §7; mutation #8: evidence
    is environment-bound, never assumed). The orchestrator compiles the
    skeleton; the worker fills environment/database explicitly."""
    doc = yaml.safe_load(text) or {}
    if doc.get("version") != 1:
        return Result(False, "DATABASE_REQUEST.yaml requires version 1")
    if not doc.get("change_id"):
        return Result(False, "DATABASE_REQUEST.yaml requires change_id")
    for key in ("environment", "database"):
        if not str(doc.get(key) or "").strip():
            return Result(False, f"DATABASE_REQUEST.yaml requires an explicit {key}")
    questions = doc.get("questions")
    if not isinstance(questions, list) or not questions:
        return Result(False, "DATABASE_REQUEST.yaml requires a non-empty questions list")
    if doc.get("allowed_lane") != "exploration":
        return Result(False, "database request allowed_lane must be exploration")
    if not isinstance(doc.get("data_probe_required"), bool):
        return Result(False, "data_probe_required must be an explicit boolean")
    return Result(True)


_DRIFT_CLASSES = {"source_ahead", "db_ahead", "mismatch"}


def validate_database_context(text) -> Result:
    """Gate `database-context` — DATABASE_CONTEXT v2 (harness plan §7, C-20).

    The context must be provider-identified, environment-bound, probe-backed
    (host_mcp invocation) and read-only; observed drift must be classified,
    and an unreachable DB needs a structured degradation record."""
    doc = yaml.safe_load(text) or {}
    if doc.get("version") != 2:
        return Result(False, "DATABASE_CONTEXT.yaml requires version 2")
    if not doc.get("change_id"):
        return Result(False, "DATABASE_CONTEXT.yaml requires change_id")
    if doc.get("read_only") is not True:
        return Result(False, "DATABASE_CONTEXT.yaml requires read_only: true")
    provider = doc.get("provider") or {}
    if not provider.get("id") or not provider.get("client_key"):
        return Result(False, "database context requires provider.id + provider.client_key")
    probe = doc.get("probe") or {}
    degradation = doc.get("degradation") or []
    if probe:
        if probe.get("invocation_mode") != "host_mcp":
            return Result(False, "probe.invocation_mode must be host_mcp")
        for key in ("database", "environment", "observed_at", "status"):
            if not str(probe.get(key) or "").strip():
                return Result(False, f"database probe requires {key}")
        if probe["status"] not in {"success", "error", "timeout"}:
            return Result(False, f"unknown probe status {probe['status']!r}")
    elif not degradation:
        return Result(False, "database context requires a probe or a structured "
                             "degradation record")
    if doc.get("allowed_lane") != "exploration":
        return Result(False, "database context allowed_lane must be exploration")
    if not doc.get("allowed_tools"):
        return Result(False, "database context requires allowed_tools (pinned lane)")
    observations = doc.get("observations") or []
    if not observations and not degradation:
        return Result(False, "database context requires observations or a "
                             "structured degradation record")
    for i, entry in enumerate(degradation, 1):
        if not isinstance(entry, dict) or not entry.get("kind") \
                or not str(entry.get("detail") or "").strip():
            return Result(False, f"degradation {i}: requires kind + detail")
    for i, entry in enumerate(doc.get("drift") or [], 1):
        if not isinstance(entry, dict):
            return Result(False, f"drift {i}: must be a mapping")
        if not entry.get("object"):
            return Result(False, f"drift {i}: object required")
        if entry.get("classification") not in _DRIFT_CLASSES:
            return Result(False, f"drift {i}: classification must be one of "
                                 f"{sorted(_DRIFT_CLASSES)} (unclassified drift "
                                 "is invalid)")
        if not str(entry.get("detail") or "").strip():
            return Result(False, f"drift {i}: detail required")
    if doc.get("confidence") not in {"high", "medium", "low"}:
        return Result(False, "database context requires confidence high|medium|low")
    return Result(True)


_INVOCATION_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_INVOCATION_TS = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$"
)
_INVOCATION_REQUIRED = (
    "trace_id", "change_id", "role", "provider_id", "tool", "invocation_mode",
    "request_hash", "response_hash", "started_at", "ended_at", "status",
)
_INVOCATION_STATUSES = {"success", "error", "timeout"}


def validate_provider_invocations(text, provider_registry=None) -> Result:
    """Gate `provider-invocations` — every trusted MCP call needs a host-delegated
    invocation record with payload hashes (harness plan §7/§12; blocker B3).
    Validates linkage (registered provider, snapshot tool, hash/timestamp shape),
    not the semantic truth of the response (errata E6)."""
    lines = [line for line in (text or "").splitlines() if line.strip()]
    if not lines:
        return Result(False, "no provider invocation records")
    providers = (provider_registry or {}).get("providers") or {}
    for lineno, line in enumerate(lines, 1):
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            return Result(False, f"line {lineno}: invalid JSON record")
        if not isinstance(record, dict):
            return Result(False, f"line {lineno}: record must be a JSON object")
        missing = [field for field in _INVOCATION_REQUIRED if not record.get(field)]
        if missing:
            return Result(False, f"line {lineno}: missing fields {missing}")
        if record["invocation_mode"] != "host_mcp":
            return Result(False, f"line {lineno}: invocation_mode must be host_mcp")
        if record["status"] not in _INVOCATION_STATUSES:
            return Result(False, f"line {lineno}: unknown status {record['status']!r}")
        for key in ("request_hash", "response_hash"):
            if not _INVOCATION_HASH.match(str(record[key])):
                return Result(False, f"line {lineno}: {key} must be sha256:<64 hex>")
        for key in ("started_at", "ended_at"):
            if not _INVOCATION_TS.match(str(record[key])):
                return Result(False, f"line {lineno}: {key} must be an ISO-8601 timestamp")
        if providers:
            spec = providers.get(record["provider_id"])
            if spec is None:
                return Result(
                    False, f"line {lineno}: unknown provider {record['provider_id']!r}"
                )
            snapshot = set(((spec.get("tool_contract") or {}).get("tools")) or [])
            if snapshot and record["tool"] not in snapshot:
                return Result(
                    False,
                    f"line {lineno}: tool {record['tool']!r} not in "
                    f"{record['provider_id']} tested tool snapshot",
                )
    return Result(True)


_TRACE_FRESHNESS = {"FRESH", "STALE", "VERY_STALE", "UNKNOWN"}
_TRACE_HEALTH = {"HEALTHY", "DEGRADED", "INVALID", "UNAVAILABLE"}


def validate_trace_request(text, valid_capabilities=None, trigger_vocabulary=None) -> Result:
    """Gate `trace-request` — orchestrator-compiled capability requirements for a
    structured trace (harness plan §7; capability-requirements semantics folded
    in per errata E1). Provider-neutral: only capability IDs and triggers."""
    doc = yaml.safe_load(text) or {}
    if doc.get("version") != 1:
        return Result(False, "TRACE_REQUEST.yaml requires version 1")
    if not doc.get("change_id"):
        return Result(False, "TRACE_REQUEST.yaml requires change_id")
    questions = doc.get("questions")
    if not isinstance(questions, list) or not questions:
        return Result(False, "TRACE_REQUEST.yaml requires a non-empty questions list")
    for q in questions:
        if not q.get("id") or not str(q.get("question") or "").strip():
            return Result(False, "trace request question requires id and question text")
    required = doc.get("required_capabilities") or []
    one_of = doc.get("one_of") or {}
    conditional = doc.get("conditional") or {}
    one_of_members = [m for members in one_of.values() for m in (members or [])]
    if valid_capabilities is not None:
        for cap in list(required) + one_of_members + list(conditional):
            if cap not in valid_capabilities:
                return Result(False, f"unknown capability {cap!r}")
    overlap = set(required) & set(conditional)
    if overlap:
        return Result(False, f"capabilities both required and conditional: {sorted(overlap)}")
    for capability, spec in conditional.items():
        triggers = (spec or {}).get("triggers") or []
        if not triggers:
            return Result(False, f"conditional capability {capability} requires triggers")
        if trigger_vocabulary is not None:
            for trigger in triggers:
                if trigger not in trigger_vocabulary:
                    return Result(False, f"unknown trigger {trigger!r} for {capability}")
    if not doc.get("freshness_requirement") or not doc.get("source_verification_requirement"):
        return Result(False, "trace request requires freshness_requirement and "
                             "source_verification_requirement")
    return Result(True)


def _invocation_hash_index(invocations_text):
    index = {}
    for line in (invocations_text or "").splitlines():
        if not line.strip():
            continue
        try:
            record = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(record, dict) and record.get("response_hash"):
            index[record["response_hash"]] = record
    return index


def validate_trace_evidence(text, request_text=None, invocations_text=None,
                            repo_root=None) -> Result:
    """Gate `trace-evidence` — provider-neutral trace evidence (harness plan §7/§14).

    Validates LINKAGE, not content truth (errata E6): every observation and
    support call must be hash-bound to a host-delegated invocation record;
    traversals must reference recorded observations; conditional capability use
    requires an activating trigger + reason; required/one_of capabilities must
    be covered; source verifications are mechanically re-hashed; a truncated
    observation forbids `complete: true`."""
    doc = yaml.safe_load(text) or {}
    if doc.get("version") != 1:
        return Result(False, "TRACE_EVIDENCE.yaml requires version 1")
    if not doc.get("change_id"):
        return Result(False, "TRACE_EVIDENCE.yaml requires change_id")
    request = (yaml.safe_load(request_text) or {}) if request_text else {}
    if request and request.get("change_id") != doc.get("change_id"):
        return Result(False, "trace evidence change_id disagrees with TRACE_REQUEST")

    observations = doc.get("provider_observations") or []
    invocations = (_invocation_hash_index(invocations_text)
                   if invocations_text is not None else None)
    obs_hashes = set()
    truncated = False
    for i, obs in enumerate(observations, 1):
        for key in ("provider_id", "tool", "response_hash"):
            if not obs.get(key):
                return Result(False, f"observation {i}: missing {key}")
        if invocations is not None:
            record = invocations.get(obs["response_hash"])
            if record is None:
                return Result(False, f"observation {i}: response_hash has no "
                                     "provider invocation record")
            if (record.get("provider_id") != obs["provider_id"]
                    or record.get("tool") != obs["tool"]):
                return Result(False, f"observation {i}: provider/tool disagree "
                                     "with invocation record")
        obs_hashes.add(obs["response_hash"])
        truncated = truncated or bool(obs.get("truncated"))

    limitations = doc.get("limitations") or []
    excused_caps, excused_groups = set(), set()
    for i, limitation in enumerate(limitations, 1):
        if not isinstance(limitation, dict) or not limitation.get("kind") \
                or not str(limitation.get("detail") or "").strip():
            return Result(False, f"limitation {i}: requires kind + detail "
                                 "(structured degradation, no prose)")
        if limitation.get("capability"):
            excused_caps.add(limitation["capability"])
        if limitation.get("one_of"):
            excused_groups.add(limitation["one_of"])

    graph = doc.get("graph") or {}
    if graph:
        for key in ("project", "graph_commit", "repository_head", "freshness", "health"):
            if not graph.get(key):
                return Result(False, f"graph block missing {key}")
        # Mutation #4: a graph claim must be produced by a recorded probe —
        # the block carries the response hash of its metadata observation.
        if graph.get("observation") not in obs_hashes:
            return Result(False, "graph block is not backed by a recorded probe "
                                 "observation (fresh-graph claim needs response hash)")
        if str(graph["freshness"]).upper() not in _TRACE_FRESHNESS:
            return Result(False, f"unknown graph freshness {graph['freshness']!r}")
        health = str(graph["health"]).upper()
        if health not in _TRACE_HEALTH:
            return Result(False, f"unknown graph health {graph['health']!r}")
        if health in {"INVALID", "UNAVAILABLE"} and not limitations:
            return Result(False, f"graph health {health} requires a limitations "
                                 "entry (structured degradation)")
    elif not limitations:
        return Result(False, "missing graph block requires a limitations entry "
                             "(e.g. ua_unavailable degradation)")

    required = set(request.get("required_capabilities") or []) if request else set()
    one_of = request.get("one_of") or {}
    conditional = request.get("conditional") or {}
    known_caps = (required
                  | {m for members in one_of.values() for m in (members or [])}
                  | set(conditional))
    covered = set()
    for i, traversal in enumerate(doc.get("traversals") or [], 1):
        capability = traversal.get("capability")
        if not capability:
            return Result(False, f"traversal {i}: capability required")
        refs = traversal.get("observations") or []
        if not refs:
            return Result(False, f"traversal {i}: must reference observation "
                                 "response hashes")
        for ref in refs:
            if ref not in obs_hashes:
                return Result(False, f"traversal {i}: references unrecorded "
                                     f"observation {ref!r}")
        if request and capability not in known_caps:
            return Result(False, f"traversal {i}: capability {capability!r} not "
                                 "in trace request")
        if capability in conditional:
            trigger = traversal.get("trigger")
            if not trigger or not str(traversal.get("reason") or "").strip():
                return Result(False, f"traversal {i}: conditional capability "
                                     f"{capability} requires trigger + reason")
            declared = (conditional[capability] or {}).get("triggers") or []
            if trigger not in declared:
                return Result(False, f"traversal {i}: trigger {trigger!r} not "
                                     f"declared for {capability}")
        covered.add(capability)

    for i, call in enumerate(doc.get("support_calls") or [], 1):
        for key in ("provider_id", "capability", "trigger", "reason", "response_hash"):
            if not str(call.get(key) or "").strip():
                return Result(False, f"support call {i}: missing {key} "
                                     "(conditional support needs trigger + reason)")
        if invocations is not None and call["response_hash"] not in invocations:
            return Result(False, f"support call {i}: response_hash has no "
                                 "provider invocation record")
        if request:
            spec = conditional.get(call["capability"])
            if spec is None:
                return Result(False, f"support call {i}: capability "
                                     f"{call['capability']!r} is not conditional "
                                     "in the trace request")
            if call["trigger"] not in ((spec or {}).get("triggers") or []):
                return Result(False, f"support call {i}: trigger {call['trigger']!r} "
                                     f"not declared for {call['capability']}")

    verifications = doc.get("source_verifications") or []
    for i, entry in enumerate(verifications, 1):
        file = entry.get("file")
        fhash = str(entry.get("sha256") or "")
        if not file or not _SHA256_FMT.match(fhash):
            return Result(False, f"source verification {i}: file + sha256 required")
        if repo_root:
            problem = _verify_source_file(repo_root, file, fhash, entry.get("symbol"))
            if problem:
                return Result(False, f"source verification {i}: {problem}")
    if verifications:
        covered.add("exact_source_inspection")

    if request:
        missing = required - covered - excused_caps
        if missing:
            return Result(False, f"required capabilities uncovered: {sorted(missing)}")
        for group, members in one_of.items():
            if members and not (set(members) & covered) and group not in excused_groups:
                return Result(False, f"one_of group {group} unsatisfied "
                                     f"(need one of {sorted(members)})")

    if doc.get("confidence") not in {"high", "medium", "low"}:
        return Result(False, "trace evidence requires confidence high|medium|low")
    if doc.get("complete") is True:
        if excused_caps or excused_groups:
            return Result(False, "complete: true while limitations excuse "
                                 "capabilities/groups (degraded trace is not complete)")
        if truncated:
            return Result(False, "complete: true with a truncated observation")
        if request and request.get("source_verification_requirement") and not verifications:
            return Result(False, "complete: true requires source verifications")
    return Result(True)


# ── W4: task knowledge capsule integrity + executor re-grounding request ─────

def validate_capsule_integrity(text, queue_doc=None, task_id=None,
                               evidence_manifest_text=None) -> Result:
    """Gate `capsule-integrity` — the Task Knowledge Capsule must match the queue
    hash (immutable after dispatch) and stay fresh against the current evidence
    manifest (stale knowledge blocks dispatch)."""
    if not queue_doc or not task_id:
        return Result(False, "queue_doc and task_id required")
    import hashlib
    try:
        cap = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return Result(False, f"bad capsule format: {exc}")
    if not isinstance(cap, dict):
        return Result(False, "capsule must be a mapping")
    if cap.get("task_id") != task_id:
        return Result(False, f"capsule task_id mismatch: {cap.get('task_id')} != {task_id}")
    task_info = next((t for t in queue_doc.get("tasks", []) if t.get("id") == task_id), None)
    if not task_info:
        return Result(False, f"task_id {task_id} not in queue")
    if hashlib.sha256(text.encode("utf-8")).hexdigest() != task_info.get("capsule_hash"):
        return Result(False, "capsule_hash mismatch: capsule edited after compilation")
    fr = cap.get("freshness") or {}
    if not fr.get("repository_commit"):
        return Result(False, "capsule missing freshness.repository_commit")
    if evidence_manifest_text is not None:
        current = "sha256:" + hashlib.sha256(evidence_manifest_text.encode("utf-8")).hexdigest()
        if fr.get("evidence_manifest_hash") != current:
            return Result(False, "stale capsule: evidence_manifest_hash != current EVIDENCE_MANIFEST")
    return Result(True)


_REGROUND_STATUSES = {"NEEDS_REGROUNDING", "EVIDENCE_CONFLICT", "STALE_KNOWLEDGE"}


def validate_evidence_update_request(text) -> Result:
    """Gate `evidence-update-request` — an executor's re-grounding request
    (`results/TASK-NNN.EVIDENCE_UPDATE_REQUEST.yaml`) must name the task, a valid
    re-grounding status, a reason, and the affected evidence."""
    try:
        doc = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return Result(False, f"evidence update request is not valid YAML: {exc}")
    if not isinstance(doc, dict):
        return Result(False, "evidence update request must be a mapping")
    if not doc.get("task_id"):
        return Result(False, "evidence update request missing task_id")
    status = doc.get("status")
    if status not in _REGROUND_STATUSES:
        return Result(False, f"invalid status '{status}' (need one of {sorted(_REGROUND_STATUSES)})")
    if not str(doc.get("reason") or "").strip():
        return Result(False, "evidence update request must explain reason")
    affected = doc.get("affected_evidence")
    if not isinstance(affected, list) or not affected:
        return Result(False, "evidence update request must list non-empty affected_evidence")
    return Result(True)


# Knowledge control-plane gates -------------------------------------------------

_MATERIAL_DECISION_TYPES = {
    "architecture", "public_contract", "business_behavior", "persistence",
    "async_event", "migration", "deletion", "security", "task_decomposition",
    "verification_claim",
}


def _yaml_mapping(text, artifact: str):
    try:
        data = yaml.safe_load(text) or {}
    except yaml.YAMLError as exc:
        return None, Result(False, f"{artifact} is not valid YAML: {exc}")
    if not isinstance(data, dict):
        return None, Result(False, f"{artifact} must be a YAML mapping")
    return data, None


def validate_agent_kernel(text: str) -> Result:
    """Gate `agent-kernel` — kernel contract (agent-facing plan §7.3/§7.4)."""
    sections = (
        "Identity", "Canonical Authority", "Workflow Routing", "Write Boundary",
        "Evidence Honesty", "Verification Honesty", "Learning Boundary",
        "Resume & Bootstrap", "Stop Conditions",
    )
    missing = [name for name in sections if not re.search(rf"^##\s+(?:\d+\.\s+)?{re.escape(name)}\s*$", text, re.MULTILINE)]
    if missing:
        return Result(False, "agent kernel missing sections: " + ", ".join(missing))
    required = (
        "KERNEL_ID: maika-agent-kernel-v1",
        "knowledge-grounded engineering agent", "Không có material decision",
        "procedures/bootstrap.md", "BOOTSTRAP_ENV_REPORT.yaml", "AGENT_BOOTSTRAP_ACK.yaml",
        "artifact-authority.yaml", "STATE.yaml",
    )
    absent = [item for item in required if item.lower() not in text.lower()]
    if absent:
        return Result(False, "agent kernel missing markers: " + ", ".join(absent))
    # §7.2: kernel must not carry legacy active paths, provider doctrine details
    # or a global fixed phase chain.
    forbidden = (
        "knowledge/active/", "REQUIREMENT.md", "EXPLORE_CONTEXT", "AGENT_TRANSPARENCY",
        "TOKEN_LOG", "Understand-Anything", "Codebase Memory",
        "explore → spec → plan",
    )
    present = [item for item in forbidden if item.lower() in text.lower()]
    if present:
        return Result(False, "agent kernel contains forbidden content: " + ", ".join(present))
    lines = len(text.splitlines())
    if lines > 150:
        return Result(False, f"agent kernel must be at most 150 lines, found {lines}")
    return Result(True)


def validate_bootstrap_ack(text: str) -> Result:
    """Gate `bootstrap-ack` — agent acknowledgment structure (plan §14).

    Hash FRESHNESS (ack vs current kernel/router/index) is enforced at runtime
    by cli.commands.bootstrap.verify_ack_freshness; this gate checks shape.
    """
    data, error = _yaml_mapping(text, "bootstrap ack")
    if error:
        return error
    required = ("version", "timestamp", "kernel_hash", "router_hash", "skill_index_hash",
                "env_report_hash", "selected_change", "current_state", "selected_route",
                "rules_loaded", "unresolved_contradictions", "acknowledged_by")
    missing = [key for key in required if key not in data]
    if missing:
        return Result(False, "bootstrap ack missing: " + ", ".join(missing))
    for key in ("kernel_hash", "router_hash", "skill_index_hash", "env_report_hash"):
        value = str(data.get(key) or "")
        if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
            return Result(False, f"bootstrap ack {key} must be a sha256 content hash")
    if not data.get("rules_loaded"):
        return Result(False, "bootstrap ack rules_loaded cannot be empty")
    if not str(data.get("acknowledged_by") or "").strip():
        return Result(False, "bootstrap ack acknowledged_by cannot be empty")
    try:
        datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return Result(False, "bootstrap ack timestamp must be ISO-8601")
    return Result(True)


def validate_bootstrap_complete(text: str) -> Result:
    data, error = _yaml_mapping(text, "bootstrap report")
    if error:
        return error
    required = ("version", "completed", "timestamp", "repository_commit", "entry_point", "rules_present",
                "knowledge_index", "configured_providers", "provider_probes", "episodic_provider_health",
                "active_changes", "resume_state", "degradation")
    missing = [key for key in required if key not in data]
    if missing:
        return Result(False, "bootstrap report missing: " + ", ".join(missing))
    if data.get("completed") is not True:
        return Result(False, "bootstrap report is not completed")
    for key in ("timestamp", "entry_point", "episodic_provider_health", "resume_state"):
        if data.get(key) in (None, "", []):
            return Result(False, f"bootstrap report {key} cannot be empty")
    if data.get("resume_state") not in ("new", "resume", "ambiguous"):
        return Result(False, "bootstrap resume_state must be new|resume|ambiguous")
    try:
        timestamp = datetime.fromisoformat(str(data["timestamp"]).replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - timestamp.astimezone(timezone.utc)
    except (ValueError, TypeError):
        return Result(False, "bootstrap timestamp must be ISO-8601")
    if age.total_seconds() < -300 or age.total_seconds() > 86400:
        return Result(False, "bootstrap report is stale for this session/day")
    if not str(data.get("repository_commit") or "").strip():
        return Result(False, "bootstrap repository_commit cannot be empty")
    rules = set(data.get("rules_present") or [])
    # CORE rules must all be present; JIT files are listed as facts but load on demand.
    required_rules = {"RULES.md", "core/flow.md", "core/evidence.md",
                      "core/write-boundary.md", "core/verification.md"}
    if not required_rules <= rules:
        return Result(False, "bootstrap environment is missing a core rule file")
    index = data.get("knowledge_index") or {}
    if index.get("status") != "loaded" or not isinstance(index.get("entries"), int):
        return Result(False, "bootstrap knowledge_index must be loaded with integer entries")
    configured = set(data.get("configured_providers") or [])
    probes = data.get("provider_probes")
    if not isinstance(probes, list):
        return Result(False, "bootstrap provider_probes must be a list")
    probed = {item.get("provider_id") for item in probes if isinstance(item, dict)}
    if configured != probed:
        return Result(False, "bootstrap must probe every configured provider exactly once")
    for item in probes:
        if not item.get("status") or not item.get("evidence"):
            return Result(False, "bootstrap provider probe requires status and evidence")
        if item.get("status") != "healthy" and not any(
            d.get("provider_id") == item.get("provider_id") for d in data.get("degradation") or []
            if isinstance(d, dict)
        ):
            return Result(False, "unhealthy/unprobed provider requires degradation")
    return Result(True)


def validate_context_package(text: str) -> Result:
    data, error = _yaml_mapping(text, "context package")
    if error:
        return error
    required = ("role", "change_id", "state", "loaded_artifacts", "knowledge_slice",
                "memory_slice", "source_anchors", "database_slice", "missing_context",
                "degradation", "confidence", "freshness")
    missing = [key for key in required if key not in data]
    if missing:
        return Result(False, "context package missing: " + ", ".join(missing))
    if data.get("confidence") not in {"low", "medium", "high"}:
        return Result(False, "context package confidence must be low/medium/high")
    freshness = data.get("freshness") or {}
    if not freshness.get("repository_commit") or not freshness.get("generated_at"):
        return Result(False, "context package missing repository_commit/generated_at freshness")
    if data.get("missing_context") and not data.get("degradation"):
        return Result(False, "missing context requires explicit degradation")
    return Result(True)


def validate_dispatch_kernel(text: str) -> Result:
    required = (
        "KERNEL_ID: maika-knowledge-control-v1", "You are an isolated Maika worker.",
        "Do not rely on parent conversation history.", "current source",
        "EVIDENCE_UPDATE_REQUEST", "evidence IDs", "write boundaries",
        "Return structured result only.",
    )
    missing = [item for item in required if item.lower() not in text.lower()]
    return Result(False, "dispatch kernel missing: " + ", ".join(missing)) if missing else Result(True)


_ASSUMPTION_POLICY = None
_BLOCKING_ASSUMPTION_ACTIONS = {"block", "block_spec", "human_gate"}
# Fallback khi target chưa có config/assumption-policy.yaml (compat window):
# mọi type ngoài fallback bị coi là unknown -> fail, không silently continue.
_ASSUMPTION_POLICY_FALLBACK = {
    "non_material": {"action": "continue", "confidence_cap": "medium", "requires": []},
}


def _assumption_policy() -> dict:
    """Load assumption taxonomy from config/assumption-policy.yaml (plan §16)."""
    global _ASSUMPTION_POLICY
    if _ASSUMPTION_POLICY is None:
        path = Path(__file__).resolve().parents[2] / "config" / "assumption-policy.yaml"
        if path.exists():
            doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
            _ASSUMPTION_POLICY = doc.get("types") or _ASSUMPTION_POLICY_FALLBACK
        else:
            _ASSUMPTION_POLICY = _ASSUMPTION_POLICY_FALLBACK
    return _ASSUMPTION_POLICY


def _validate_assumption_records(assumptions, decision_confidence) -> Result:
    """Assumptions must be typed records; risky types block until human approval."""
    policy = _assumption_policy()
    for item in assumptions:
        if not isinstance(item, dict):
            return Result(False, "assumption must be a typed record "
                                 "(see config/assumption-policy.yaml)")
        atype = item.get("type")
        spec = policy.get(atype)
        if spec is None:
            return Result(False, f"unknown assumption type {atype!r} "
                                 "(see config/assumption-policy.yaml)")
        base = ("id", "statement", "evidence_gap", "expiry_condition")
        missing = [key for key in base if not item.get(key)]
        missing += [key for key in spec.get("requires") or [] if not item.get(key)]
        if missing:
            return Result(False, f"assumption {item.get('id') or atype} missing: "
                                 + ", ".join(missing))
        action = spec.get("action")
        if action in _BLOCKING_ASSUMPTION_ACTIONS and item.get("human_decision") != "approved":
            return Result(False, f"assumption {item['id']} ({atype}) requires a human "
                                 f"decision before proceeding (action: {action})")
        if spec.get("confidence_cap") == "medium" and decision_confidence == "high":
            return Result(False, f"assumption {item['id']} ({atype}) caps decision "
                                 "confidence at medium")
    return Result(True)


def validate_knowledge_trace(text: str, valid_evidence_ids=None) -> Result:
    data, error = _yaml_mapping(text, "Knowledge Trace")
    if error:
        return error
    decision = data.get("decision")
    if not isinstance(decision, dict):
        return Result(False, "Knowledge Trace requires decision mapping")
    required = ("id", "statement", "type", "knowledge_questions", "evidence_ids",
                "authority", "conflicts", "assumptions", "confidence", "freshness", "verdict")
    missing = [key for key in required if key not in decision]
    if missing:
        return Result(False, "Knowledge Trace missing: " + ", ".join(missing))
    if not str(decision.get("id") or "").strip() or not str(decision.get("statement") or "").strip():
        return Result(False, "Knowledge Trace id/statement cannot be empty")
    decision_type = re.sub(r"[-/\s]+", "_", str(decision.get("type") or "").lower())
    if decision_type not in _MATERIAL_DECISION_TYPES:
        return Result(False, "Knowledge Trace has invalid material decision type")
    if not isinstance(decision.get("knowledge_questions"), list) or not decision["knowledge_questions"]:
        return Result(False, "Knowledge Trace requires knowledge_questions")
    if not isinstance(decision.get("evidence_ids"), list) or not decision["evidence_ids"]:
        return Result(False, "Knowledge Trace material decision requires evidence_ids")
    if not all(str(item).strip() for item in decision["evidence_ids"]):
        return Result(False, "Knowledge Trace evidence_ids cannot contain empty values")
    if valid_evidence_ids is not None and not set(decision["evidence_ids"]) <= set(valid_evidence_ids):
        return Result(False, "Knowledge Trace cites evidence IDs absent from assigned manifest/capsule")
    authority = str(decision.get("authority") or "").lower()
    authority_markers = ("runtime", "database", "current source", "business contract",
                         "graph", "durable knowledge", "historical memory")
    if not any(marker in authority for marker in authority_markers):
        return Result(False, "Knowledge Trace authority is outside canonical hierarchy")
    if not isinstance(decision.get("conflicts"), list) or not isinstance(decision.get("assumptions"), list):
        return Result(False, "Knowledge Trace conflicts/assumptions must be lists")
    if decision.get("confidence") not in {"low", "medium", "high"}:
        return Result(False, "Knowledge Trace confidence must be low/medium/high")
    if decision.get("freshness") not in {"fresh", "verified", "degraded"}:
        return Result(False, "Knowledge Trace freshness must be fresh/verified/degraded")
    unresolved = [item for item in decision.get("conflicts") or []
                  if not isinstance(item, dict) or item.get("status") not in {"resolved", "superseded"}]
    if unresolved:
        return Result(False, "Knowledge Trace has unresolved conflicts")
    assumption_result = _validate_assumption_records(
        decision.get("assumptions") or [], decision.get("confidence")
    )
    if not assumption_result.ok:
        return assumption_result
    if str(decision.get("verdict") or "").lower() not in {"accepted", "approved", "verified"}:
        return Result(False, "Knowledge Trace verdict is not accepted")
    if decision.get("confidence") == "low" or decision.get("freshness") == "degraded":
        return Result(False, "accepted material decision requires non-low, non-degraded evidence")
    return Result(True)


def validate_skill_feedback(text: str) -> Result:
    data, error = _yaml_mapping(text, "skill feedback")
    if error:
        return error
    if data.get("version") != 1 or not data.get("change_id") or data.get("verified") is not True:
        return Result(False, "skill feedback requires version 1, change_id and verified: true")
    observations = data.get("observations")
    if not isinstance(observations, list):
        return Result(False, "skill feedback observations must be a list")
    fields = {"id", "skill", "category", "severity", "statement", "evidence",
              "recurrence_key", "recommendation"}
    for item in observations:
        if not isinstance(item, dict) or fields - set(item):
            return Result(False, "skill feedback observation missing required fields")
        if item.get("category") not in {"editorial", "behavioral", "contractual"}:
            return Result(False, "invalid skill feedback category")
        if not item.get("evidence"):
            return Result(False, "skill feedback observation requires evidence")
    return Result(True)


def validate_skill_evolution_candidate(text: str) -> Result:
    data, error = _yaml_mapping(text, "skill evolution candidate")
    if error:
        return error
    top = {"version", "candidate_id", "target_skill", "status", "classification", "problem",
           "evidence", "proposed_change", "expected_effect", "compatibility", "validation",
           "skill_evaluation", "rollback"}
    if top - set(data):
        return Result(False, "skill candidate missing: " + ", ".join(sorted(top - set(data))))
    if data.get("classification") not in {"editorial", "behavioral", "contractual"}:
        return Result(False, "invalid skill candidate classification")
    problem, evidence = data.get("problem") or {}, data.get("evidence") or {}
    count = int(problem.get("occurrences") or 0)
    changes = set(evidence.get("changes") or [])
    if evidence.get("verified") is not True:
        return Result(False, "skill candidate requires verified evidence")
    explicit = bool(evidence.get("critical_incident") or evidence.get("user_directive") or
                    (evidence.get("dogfood_failure") and evidence.get("reproducible")))
    if not explicit and (count < 3 or len(changes) < 2):
        return Result(False, "skill candidate recurrence threshold not met")
    return Result(True)


def validate_skill_evolution_review(text: str) -> Result:
    data, error = _yaml_mapping(text, "skill evolution review")
    if error:
        return error
    required = ("candidate_id", "reviewer", "independent", "guardrails_preserved", "verdict")
    if any(key not in data for key in required):
        return Result(False, "skill evolution review missing required fields")
    if data.get("independent") is not True or data.get("guardrails_preserved") is not True:
        return Result(False, "skill evolution review must be independent and preserve guardrails")
    if data.get("verdict") not in {"approved", "rejected"}:
        return Result(False, "skill evolution review verdict must be approved/rejected")
    return Result(True)


def validate_skill_evolution_promotion(text: str) -> Result:
    data, error = _yaml_mapping(text, "skill evolution promotion")
    if error:
        return error
    required = ("candidate_id", "classification", "old_version", "new_version",
                "independent_review", "tests_passed", "dogfood_passed", "human_approval")
    if any(key not in data for key in required):
        return Result(False, "skill evolution promotion missing required fields")
    def version(value):
        try:
            return tuple(int(part) for part in str(value).split("."))
        except ValueError:
            return ()
    if not version(data.get("new_version")) > version(data.get("old_version")):
        return Result(False, "skill version must increase")
    if data.get("independent_review") != "approved" or data.get("tests_passed") is not True:
        return Result(False, "promotion requires approved review and regression tests")
    if data.get("classification") in {"behavioral", "contractual"} and data.get("dogfood_passed") is not True:
        return Result(False, "behavioral/contractual promotion requires dogfood")
    if data.get("classification") in {"behavioral", "contractual"} and (
        data.get("canary_passed") is not True or not data.get("canary_results")
    ):
        return Result(False, "behavioral/contractual promotion requires canary evidence")
    if data.get("classification") == "contractual" and data.get("human_approval") is not True:
        return Result(False, "contractual promotion requires human approval")
    return Result(True)
