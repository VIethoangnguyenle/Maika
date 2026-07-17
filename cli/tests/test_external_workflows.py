from copy import deepcopy
from pathlib import Path

from cli.agent_content.external_workflows import (
    load_external_workflows, validate_external_workflows,
)

FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"


def _doc():
    return load_external_workflows(FRAMEWORK)


def test_canonical_external_workflows_are_valid():
    assert validate_external_workflows(_doc()) == []


def test_read_only_workflow_cannot_declare_writes():
    doc = deepcopy(_doc())
    doc["workflows"]["sample-query"] = {
        "owner": "understand-anything",
        "invocation_type": "provider_query",
        "kind": "knowledge_query",
        "task_workspace": "not_required",
        "mutability": "read_only",
        "allowed_writes": [".maika/reports/sample/**"],
    }
    errors = validate_external_workflows(doc)
    assert any("read-only" in error for error in errors)


def test_report_workflow_cannot_write_source_or_auto_promote():
    doc = deepcopy(_doc())
    chat = doc["workflows"]["understand-chat"]
    chat["allowed_report_paths"].append("src/**")
    chat["promotion"]["automatic"] = True
    errors = validate_external_workflows(doc)
    assert any("application source" in error for error in errors)
    assert any("auto-promote" in error for error in errors)


def test_maintenance_workflow_must_declare_outputs_and_freshness():
    doc = deepcopy(_doc())
    understand = doc["workflows"]["understand"]
    understand["produces"] = []
    understand["freshness"] = {}
    errors = validate_external_workflows(doc)
    assert any("declare outputs" in error for error in errors)
    assert any("bind freshness" in error for error in errors)


def test_native_commands_are_passthrough_and_taskless():
    workflows = _doc()["workflows"]
    for name in ("understand", "understand-domain", "understand-chat"):
        assert workflows[name]["invocation_type"] == "native_passthrough"
        assert workflows[name]["task_workspace"] in {"forbidden", "not_required"}
