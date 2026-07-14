from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path

from cli.agent_content.generated_reports import (
    load_report_schema, report_path, validate_report_document, validate_report_schema,
)

FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"


def _valid_report():
    return """---
type: generated-analysis-report
provider: understand-anything
workflow: understand-chat
question: Trace approval flow
generated_at: 2026-07-12T00:00:00Z
repository_commit: abc123
graph_commit: unavailable
freshness: UNKNOWN
confidence: medium
authority: generated_analysis
promotion_status: not_promoted
---
# Approval flow
"""


def test_canonical_schema_is_valid_and_report_passes():
    schema = load_report_schema(FRAMEWORK)
    assert validate_report_schema(schema) == []
    assert validate_report_document(_valid_report(), schema) == []


def test_report_requires_provenance_and_noncanonical_authority():
    schema = load_report_schema(FRAMEWORK)
    text = _valid_report().replace("repository_commit: abc123\n", "")
    text = text.replace("authority: generated_analysis", "authority: official_docs")
    errors = validate_report_document(text, schema)
    assert any("repository_commit" in error for error in errors)
    assert any("authority" in error for error in errors)


def test_standalone_path_is_under_reports_not_repo_root():
    path = report_path(
        "understand-chat", "approval-flow",
        generated_at=datetime(2026, 7, 12, tzinfo=timezone.utc),
    )
    assert path.as_posix() == ".maika/reports/understand-chat/approval-flow-20260712T000000Z.md"


def test_task_attachment_requires_explicit_change_id():
    path = report_path("understand-chat", "approval", active_change_id="C-123")
    assert path.as_posix() == ".maika/changes/C-123/exploration/UNDERSTAND_CHAT_APPROVAL.md"


def test_unsafe_path_parts_are_rejected():
    try:
        report_path("../escape", "report")
    except ValueError:
        pass
    else:
        raise AssertionError("unsafe workflow must fail")


def test_automatic_promotion_value_is_not_accepted():
    schema = deepcopy(load_report_schema(FRAMEWORK))
    text = _valid_report().replace("promotion_status: not_promoted", "promotion_status: automatic")
    assert any("promotion_status" in error for error in validate_report_document(text, schema))
