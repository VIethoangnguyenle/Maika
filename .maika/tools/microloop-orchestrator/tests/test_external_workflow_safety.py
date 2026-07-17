from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import vnext_dispatch as vd


def _request(workflow="understand"):
    return f"""request_type: external_workflow
workflow: {workflow}
reason: graph is stale for the approval flow
required_for: [Q-001]
observed_freshness: STALE_RELEVANT
affected_claims: [CLAIM-001]
resume_role: grounding
"""


def test_isolated_worker_default_contract_allows_no_execution():
    contract = vd.external_workflow_contract()
    assert contract["allowed"] == []
    assert set(contract["request_only"]) == {
        "understand", "understand-domain",
    }


def test_prompt_exposes_request_only_contract():
    prompt = vd.build_prompt("grounding", Path("/tmp/ws"), "INTENT.md", "GROUNDING.yaml")
    assert 'EXTERNAL_WORKFLOWS: {"allowed": []' in prompt
    assert "emit EXTERNAL_WORKFLOW_REQUEST.yaml" in prompt


def test_structured_request_is_accepted_but_not_executed():
    ok, reason, doc = vd.validate_external_workflow_request(_request())
    assert ok is True
    assert reason is None
    assert doc["workflow"] == "understand"


def test_unknown_workflow_request_is_rejected():
    ok, reason, _ = vd.validate_external_workflow_request(_request("invented-refresh"))
    assert ok is False
    assert "unknown external workflow" in reason


def test_ungranted_known_workflow_is_rejected():
    contract = {"allowed": [], "request_only": ["understand"]}
    ok, reason, _ = vd.validate_external_workflow_request(
        _request("understand-domain"), contract,
    )
    assert ok is False
    assert "not granted" in reason


def test_request_requires_freshness_and_resume_role():
    text = _request().replace("observed_freshness: STALE_RELEVANT\n", "")
    ok, reason, _ = vd.validate_external_workflow_request(text)
    assert ok is False
    assert "observed_freshness" in reason
