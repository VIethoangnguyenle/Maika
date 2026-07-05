import importlib.util
from pathlib import Path

MOD = Path(__file__).resolve().parents[1] / "gates.py"
spec = importlib.util.spec_from_file_location("gates", MOD)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def test_context_request_requires_request_type_and_missing_evidence():
    empty = "node_id: L1\nrequest_type: context\nmissing: []\nsuggested_tools: []\nblocked_reason: \"\"\n"
    filled = (
        "node_id: L1\n"
        "request_type: context\n"
        "missing:\n  - AD_USER column metadata\n"
        "suggested_tools:\n  - db-remote\n"
        "blocked_reason: cannot choose the correct repository method\n"
    )
    assert g.validate_context_request(empty).ok is False
    assert g.validate_context_request(filled).ok is True


def test_context_request_rejects_wrong_request_type():
    wrong = (
        "node_id: L1\n"
        "request_type: integration\n"
        "missing:\n  - something\n"
        "suggested_tools: []\n"
        "blocked_reason: blocked\n"
    )
    assert g.validate_context_request(wrong).ok is False


def test_node_checkpoint_requires_files_evidence_and_verification():
    empty = "# Node Checkpoint\n## Files Changed\n\n"
    filled = (
        "# Node Checkpoint\n"
        "## Files Changed\n- src/App.java\n"
        "## Requirement Satisfied\n- Implements TASK-1\n"
        "## Evidence Used\n- SP-6 from TASK_HANDOFF.node-1.md\n"
        "## Verification\n- pytest cli/tests/test_init.py -v: PASS\n"
    )
    assert g.validate_node_checkpoint(empty).ok is False
    assert g.validate_node_checkpoint(filled).ok is True


def test_knowledge_checkpoint_needs_ruleid_and_evidence():
    bad = "## Applicable DNA/Conventions\n(nothing)\n"
    ok_graph = "## DNA\nSP-6 staircase\n## Codebase\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n"
    ok_degrade = "## DNA\nSP-6\n## Codebase\nKG unavailable — grep fallback, MEDIUM\n"
    assert g.validate_knowledge_checkpoint(bad).ok is False
    assert g.validate_knowledge_checkpoint(ok_graph).ok is True
    assert g.validate_knowledge_checkpoint(ok_degrade).ok is True


def test_knowledge_checkpoint_governance_degrade_passes():
    # No approved DNA/conventions yet (fresh project) → proceed at LOW confidence, no rule-id required.
    gov = "## Applicable DNA/Conventions\nno approved DNA/conventions for this artifact-type — generic patterns, LOW confidence\n"
    assert g.validate_knowledge_checkpoint(gov).ok is True


def test_knowledge_checkpoint_rejects_ruleid_not_in_valid_set():
    text = (
        "## DNA\nISO-9001 mentioned here\n"
        "## Codebase\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n"
    )
    result = g.validate_knowledge_checkpoint(text, valid_rule_ids={"SP-6"})
    assert result.ok is False
    assert "valid rule-id" in result.reason


def test_knowledge_checkpoint_accepts_ruleid_from_valid_set():
    text = (
        "## DNA\nSP-6 staircase\n"
        "## Codebase\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n"
    )
    assert g.validate_knowledge_checkpoint(text, valid_rule_ids={"SP-6"}).ok is True


def test_governance_degrade_requires_no_knowledge_allowed():
    gov = "## Applicable DNA/Conventions\nno approved DNA/conventions for this artifact-type — generic patterns, LOW confidence\n"
    assert g.validate_knowledge_checkpoint(gov, allow_no_knowledge=False).ok is False
    assert g.validate_knowledge_checkpoint(gov, allow_no_knowledge=True).ok is True


def test_knowledge_checkpoint_still_needs_evidence_when_ruleid_present():
    # Regression: citing a rule-id but no evidence and no degrade still fails.
    bad = "## DNA\nSP-6 staircase\n## Codebase\n(no node_id, no blast-radius)\n"
    assert g.validate_knowledge_checkpoint(bad).ok is False


def test_mcp_status_needs_numbers_or_degrade():
    assert g.validate_mcp_status("MCP: Runtime Ready").ok is False
    assert g.validate_mcp_status("KG: nodes=1240 edges=5530 freshness=2026-06-18").ok is True
    assert g.validate_mcp_status("KG unavailable — grep fallback, MEDIUM").ok is True


def test_degrade_line_must_be_compact_not_rambling():
    # P1(a): rambling prose that merely contains both anchors far apart must NOT
    # satisfy the degrade path; the canonical compact line still does.
    rambling = ("KG unavailable, but actually the architecture quality is only "
                "MEDIUM for entirely unrelated documentation reasons")
    assert g.validate_mcp_status(rambling).ok is False
    assert g.validate_mcp_status("KG unavailable — grep fallback, MEDIUM").ok is True


def test_mcp_status_accepts_agent_memory_probe_and_degrade():
    assert g.validate_mcp_status("agent-memory: healthy").ok is True
    assert g.validate_mcp_status(
        "agent-memory unavailable — skip recall/save"
    ).ok is True
    # A bare label with no health word or degrade is still invalid.
    assert g.validate_mcp_status("agent-memory").ok is False
    # Hardening: negated/stale prose must NOT count as a healthy probe.
    assert g.validate_mcp_status("agent-memory is not healthy").ok is False
    # Hardening: rambling prose must NOT satisfy the degrade line.
    assert g.validate_mcp_status(
        "agent-memory unavailable, we decided to skip the recall step but later "
        "did save anyway after extensive debugging"
    ).ok is False


def test_phase_chain_requires_ordered_markers():
    done = "Pha 1 DONE\nPha 2 DONE (spec: openspec/changes/x/)\nPha 3 DONE"
    skipped = "Pha 1 DONE\nPha 3 DONE"
    assert g.validate_phase_chain(done).ok is True
    assert g.validate_phase_chain(skipped).ok is False


def test_handoff_slice_requires_applicable_section_with_ruleids():
    empty = "# Handoff\n## Task\ndo X\n"
    filled = "# Handoff\n## Applicable DNA/Conventions\n- SP-6: staircase\n- IW-05: config-driven\n"
    assert g.validate_handoff_slice(empty).ok is False
    assert g.validate_handoff_slice(filled).ok is True


def test_handoff_slice_ignores_ruleids_outside_its_section():
    # rule-id appears only in a LATER, unrelated section → must NOT pass
    leaky = (
        "# Handoff\n"
        "## Applicable DNA/Conventions\n"
        "\n"
        "## Unrelated Section\n"
        "SP-6 is just mentioned here\n"
    )
    assert g.validate_handoff_slice(leaky).ok is False


def test_implementation_context_requires_dna_evidence_and_allowed_files():
    missing = "# TASK_HANDOFF.x\n## Applicable DNA/Conventions\n- SP-6\n"
    result = g.validate_implementation_context(missing)
    assert result.ok is False
    assert "Evidence" in result.reason

    no_target = (
        "# TASK_HANDOFF.x\n"
        "## Applicable DNA/Conventions\n- SP-6: staircase\n"
        "## Evidence\n- UA evidence: domain_overview=Payment, domain_flow=ApproveTransfer\n"
    )
    result = g.validate_implementation_context(no_target)
    assert result.ok is False
    assert "Allowed Files" in result.reason

    valid = (
        "# TASK_HANDOFF.x\n"
        "## Applicable DNA/Conventions\n- SP-6: staircase\n"
        "## Evidence\n- UA evidence: domain_overview=Payment, domain_flow=ApproveTransfer\n"
        "## Allowed Files\n- src/App.java\n"
    )
    assert g.validate_implementation_context(valid).ok is True


def test_implementation_context_accepts_explicit_ua_degrade_override():
    text = (
        "# TASK_HANDOFF.x\n"
        "## Applicable DNA/Conventions\n- SP-6: staircase\n"
        "## Evidence\n"
        "- UA unavailable — explicit override, MEDIUM\n"
        "- KG unavailable — grep fallback, MEDIUM\n"
        "## Allowed Files\n- src/App.java\n"
    )
    assert g.validate_implementation_context(text).ok is True


def test_cli_returns_nonzero_on_invalid(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec2 = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(cli)
    f = tmp_path / "chk.md"
    f.write_text("nothing useful", encoding="utf-8")
    assert cli.main(["knowledge-checkpoint", str(f)]) == 1


def test_cli_uses_index_to_reject_unknown_ruleid(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec2 = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec2)
    spec2.loader.exec_module(cli)

    checkpoint = tmp_path / "KNOWLEDGE_CHECKPOINT.md"
    checkpoint.write_text(
        "## DNA\nISO-9001\n"
        "## Codebase\nnode_id: svc.UserService#42\nblast-radius: 3 nodes\n",
        encoding="utf-8",
    )
    index = tmp_path / "knowledge-index.yaml"
    index.write_text(
        "entries:\n"
        "  - id: SP-6\n"
        "    store: author-dna\n"
        "    title: staircase\n"
        "    applies_to: [Constructor]\n",
        encoding="utf-8",
    )

    assert cli.main([
        "knowledge-checkpoint", str(checkpoint),
        "--index", str(index),
        "--artifact-type", "Constructor",
    ]) == 1


# ─── Regression fixtures: the historical failures these gates exist to catch ───

def test_c10_handoff_without_sp6_slice_blocks_dispatch():
    # C-10: a subagent was dispatched with only a task description (no knowledge
    # slice) → it violated SP-6. The dispatch-gate must refuse such a handoff.
    handoff = "# Handoff\n## Task\nwrite UnlockUserConfirmExecutor\n"
    assert g.validate_handoff_slice(handoff).ok is False


def test_c22_skipped_spec_blocks_completion():
    # C-22: agent jumped Pha 1 → Pha 3, skipping the spec phase. The phase-chain
    # completion gate must reject a non-contiguous marker chain.
    transparency = "Pha 1 DONE\nPha 3 DONE"
    assert g.validate_phase_chain(transparency).ok is False


def test_apply_gate_passes_with_pha2_and_no_blocker():
    assert g.validate_apply_gate("Pha 1 DONE\nPha 2 DONE\n").ok is True


def test_apply_gate_fails_without_pha2():
    result = g.validate_apply_gate("Pha 1 DONE\n")
    assert result.ok is False
    assert "Pha 2 DONE" in result.reason


def test_apply_gate_fails_with_open_blocker():
    text = "Pha 1 DONE\nPha 2 DONE\n[BLOCKER-ARCH] coupling risk\n"
    assert g.validate_apply_gate(text).ok is False


def test_apply_gate_passes_when_blocker_resolved():
    text = (
        "Pha 1 DONE\nPha 2 DONE\n"
        "[BLOCKER-ARCH] coupling risk\n"
        "[BLOCKER-ARCH RESOLVED] 2026-06-20 user approved approach\n"
    )
    assert g.validate_apply_gate(text).ok is True


def test_cli_apply_gate_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "AGENT_TRANSPARENCY.md"
    f.write_text("Pha 1 DONE\nPha 2 DONE\n", encoding="utf-8")
    assert cli.main(["apply-gate", str(f)]) == 0
    f.write_text("Pha 1 DONE\n", encoding="utf-8")
    assert cli.main(["apply-gate", str(f)]) == 1


def test_cli_implementation_context_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "TASK_HANDOFF.node-1.md"
    f.write_text(
        "# TASK_HANDOFF.node-1\n"
        "## Applicable DNA/Conventions\n- SP-6\n"
        "## Evidence\n- UA evidence: domain_overview=User\n"
        "## Allowed Files\n- src/App.java\n",
        encoding="utf-8",
    )
    assert cli.main(["implementation-context", str(f)]) == 0
    f.write_text("# TASK_HANDOFF.node-1\n", encoding="utf-8")
    assert cli.main(["implementation-context", str(f)]) == 1


def _tm(section_body: str) -> str:
    return "# AGENT_TRANSPARENCY\n\n## Teaching Moment Check\n\n" + section_body + "\n"


def test_tm_pass_none_with_note():
    body = "status: none\nnote: no correction-with-principle observed in this session\ntarget_updates:\nwarn:\nreason:"
    assert g.validate_teaching_moment(_tm(body)).ok is True


def test_tm_pass_captured_with_targets():
    body = "status: captured\nnote: user confirmed split\ntarget_updates:\n  - author-dna.yaml: HP-12\n  - conventions.yaml: CP-3\nwarn:\nreason:"
    assert g.validate_teaching_moment(_tm(body)).ok is True


def test_tm_pass_declined_with_warn_and_reason():
    body = "status: declined\nnote:\ntarget_updates:\nwarn: [R-DNA-7] Teaching moment chua capture: prefer composition.\nreason: user declined capture"
    assert g.validate_teaching_moment(_tm(body)).ok is True


def test_tm_pass_pending_with_warn_and_reason():
    body = "status: pending-confirmation\nnote:\ntarget_updates:\nwarn: [R-DNA-7] Teaching moment chua capture: factory boundary.\nreason: awaiting user confirmation"
    assert g.validate_teaching_moment(_tm(body)).ok is True


def test_tm_fail_missing_section():
    result = g.validate_teaching_moment("# AGENT_TRANSPARENCY\n\n## Phase State\n\nphase_state: applying\n")
    assert result.ok is False
    assert "missing" in result.reason.lower()


def test_tm_fail_blank_status():
    body = "status:\nnote:\ntarget_updates:\nwarn:\nreason:"
    result = g.validate_teaching_moment(_tm(body))
    assert result.ok is False
    assert "status must be one of" in result.reason


def test_tm_fail_invalid_status():
    assert g.validate_teaching_moment(_tm("status: maybe\nnote: x")).ok is False


def test_tm_fail_none_without_note():
    result = g.validate_teaching_moment(_tm("status: none\nnote:\ntarget_updates:\nwarn:\nreason:"))
    assert result.ok is False
    assert "active assertion note" in result.reason


def test_tm_fail_none_with_placeholder_note():
    result = g.validate_teaching_moment(_tm("status: none\nnote: fill before archive"))
    assert result.ok is False


def test_tm_fail_captured_without_targets():
    result = g.validate_teaching_moment(_tm("status: captured\nnote: x\ntarget_updates:\nwarn:\nreason:"))
    assert result.ok is False
    assert "target_updates" in result.reason


def test_tm_fail_declined_without_warn():
    result = g.validate_teaching_moment(_tm("status: declined\nnote:\ntarget_updates:\nwarn:\nreason: user declined"))
    assert result.ok is False


def test_tm_fail_declined_without_reason():
    result = g.validate_teaching_moment(_tm("status: declined\nwarn: [R-DNA-7] x\nreason:"))
    assert result.ok is False


def test_tm_fail_pending_without_warn():
    result = g.validate_teaching_moment(_tm("status: pending-confirmation\nreason: awaiting"))
    assert result.ok is False


def test_tm_fail_pending_without_reason():
    result = g.validate_teaching_moment(_tm("status: pending-confirmation\nwarn: [R-DNA-7] x\nreason:"))
    assert result.ok is False


def test_cli_teaching_moment_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "AGENT_TRANSPARENCY.md"
    f.write_text(_tm("status: none\nnote: nothing to capture this session"), encoding="utf-8")
    assert cli.main(["teaching-moment", str(f)]) == 0
    f.write_text(_tm("status:\nnote:"), encoding="utf-8")
    assert cli.main(["teaching-moment", str(f)]) == 1


def test_seeded_template_fails_teaching_moment_validator():
    tpl = Path(__file__).resolve().parents[3] / "knowledge" / "templates" / "AGENT_TRANSPARENCY.tpl.md"
    content = tpl.read_text(encoding="utf-8")
    assert g.validate_teaching_moment(content).ok is False


def _ps(value: str) -> str:
    return f"# AGENT_TRANSPARENCY\n\n## Phase State\n\n```\nphase_state: {value}\n```\n\n## Next\n\nx\n"


def test_archive_ready_fail_blocked_by_arch():
    result = g.validate_archive_ready(_ps("blocked-by-arch"))
    assert result.ok is False
    assert "blocked-by-arch" in result.reason


def test_archive_ready_fail_blocked_by_data():
    result = g.validate_archive_ready(_ps("blocked-by-data"))
    assert result.ok is False
    assert "blocked-by-data" in result.reason


def test_archive_ready_pass_completed():
    assert g.validate_archive_ready(_ps("completed")).ok is True


def test_archive_ready_pass_applying():
    assert g.validate_archive_ready(_ps("applying")).ok is True


def test_archive_ready_pass_phase2_done():
    assert g.validate_archive_ready(_ps("phase-2-done")).ok is True


def test_archive_ready_pass_when_no_phase_state():
    assert g.validate_archive_ready("# AGENT_TRANSPARENCY\n\nno phase section here\n").ok is True


def test_cli_archive_ready_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "AGENT_TRANSPARENCY.md"
    f.write_text(_ps("applying"), encoding="utf-8")
    assert cli.main(["archive-ready", str(f)]) == 0
    f.write_text(_ps("blocked-by-arch"), encoding="utf-8")
    assert cli.main(["archive-ready", str(f)]) == 1


def _reset_doc(phase_state="completed", teaching_status="none", note="nothing to capture"):
    return (
        "# AGENT_TRANSPARENCY\n\n"
        "## Phase State\n\n"
        "```\n"
        f"phase_state: {phase_state}\n"
        "```\n\n"
        "## Teaching Moment Check\n\n"
        f"status: {teaching_status}\n"
        f"note: {note}\n"
        "target_updates:\n"
        "warn:\n"
        "reason:\n"
    )


def test_reset_ready_passes_completed_cancelled_or_stashed():
    assert g.validate_reset_ready(_reset_doc("completed")).ok is True
    assert g.validate_reset_ready(_reset_doc("cancelled")).ok is True
    assert g.validate_reset_ready(_reset_doc("stashed")).ok is True


def test_reset_ready_blocks_applying_or_blocked_state():
    applying = g.validate_reset_ready(_reset_doc("applying"))
    assert applying.ok is False
    assert "completed, cancelled, or stashed" in applying.reason
    blocked = g.validate_reset_ready(_reset_doc("blocked-by-arch"))
    assert blocked.ok is False
    assert "blocked-by-arch" in blocked.reason


def test_reset_ready_requires_teaching_moment_check():
    text = "# AGENT_TRANSPARENCY\n\n## Phase State\n\nphase_state: completed\n"
    result = g.validate_reset_ready(text)
    assert result.ok is False
    assert "Teaching Moment" in result.reason


def test_cli_reset_ready_exit_codes(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    f = tmp_path / "AGENT_TRANSPARENCY.md"
    f.write_text(_reset_doc("completed"), encoding="utf-8")
    assert cli.main(["reset-ready", str(f)]) == 0
    f.write_text(_reset_doc("applying"), encoding="utf-8")
    assert cli.main(["reset-ready", str(f)]) == 1


REQ_WITH_AC = """# REQUIREMENT

## Acceptance Criteria

- User can export monthly settlement report
- API returns validation error for missing account id
"""

SPEC_COVERS_AC = """# tasks

- Implement monthly settlement report export
- Add validation error when account id is missing
"""

SPEC_MISSES_AC = """# tasks

- Implement monthly settlement report export
"""

REQ_WITH_INTEGRATION = """# REQUIREMENT

## Integrations & Field Mapping

### Integration: Partner KYC API

- endpoint: /kyc/check
"""

SPEC_COVERS_INTEGRATION = """# tasks

- Add Partner KYC API adapter for /kyc/check
"""

SPEC_WITHOUT_INTEGRATION = """# tasks

- Update local validation copy
"""


def test_ac_coverage_passes_when_all_ac_terms_are_in_spec():
    assert g.validate_ac_coverage(REQ_WITH_AC, SPEC_COVERS_AC).ok is True


def test_ac_coverage_fails_when_an_ac_is_uncovered():
    result = g.validate_ac_coverage(REQ_WITH_AC, SPEC_MISSES_AC)
    assert result.ok is False
    assert "missing account id" in result.reason


def test_ac_coverage_skips_when_requirement_has_no_ac_section():
    assert g.validate_ac_coverage("# REQUIREMENT\n\nNo AC here\n", SPEC_MISSES_AC).ok is True


def test_integration_coverage_passes_when_integration_is_in_spec():
    assert g.validate_integration_coverage(REQ_WITH_INTEGRATION, SPEC_COVERS_INTEGRATION).ok is True


def test_integration_coverage_fails_when_integration_is_uncovered():
    result = g.validate_integration_coverage(REQ_WITH_INTEGRATION, SPEC_WITHOUT_INTEGRATION)
    assert result.ok is False
    assert "Partner KYC API" in result.reason


def test_cli_coverage_checks_require_against_file(tmp_path):
    import importlib.util
    cli_mod = Path(__file__).resolve().parents[1] / "cli.py"
    spec = importlib.util.spec_from_file_location("cli", cli_mod)
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)

    req = tmp_path / "REQUIREMENT.md"
    tasks = tmp_path / "tasks.md"
    req.write_text(REQ_WITH_AC, encoding="utf-8")
    tasks.write_text(SPEC_COVERS_AC, encoding="utf-8")
    assert cli.main(["ac-coverage", str(req), "--against", str(tasks)]) == 0
    assert cli.main(["ac-coverage", str(req)]) == 2
