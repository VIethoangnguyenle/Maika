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
