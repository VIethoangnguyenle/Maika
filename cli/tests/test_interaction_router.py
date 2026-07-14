from copy import deepcopy
from pathlib import Path

from cli.agent_content.interaction_router import (
    load_interaction_router, validate_interaction_router,
)

FRAMEWORK = Path(__file__).resolve().parents[2] / ".maika"


def _doc():
    return load_interaction_router(FRAMEWORK)


def test_canonical_interaction_router_is_valid():
    assert validate_interaction_router(_doc()) == []


def test_only_task_route_creates_workspace():
    doc = deepcopy(_doc())
    doc["routes"]["knowledge_query"]["creates_change_workspace"] = True
    assert any("only route" in error for error in validate_interaction_router(doc))


def test_explicit_native_command_has_highest_precedence():
    assert _doc()["precedence"][0] == "explicit_native_command"


def test_unknown_handler_and_mutability_fail():
    doc = deepcopy(_doc())
    doc["routes"]["knowledge_query"].update(handler="mystery", mutability="anything")
    errors = validate_interaction_router(doc)
    assert any("unknown handler" in error for error in errors)
    assert any("unknown mutability" in error for error in errors)


def test_default_to_task_fallback_is_forbidden():
    doc = deepcopy(_doc())
    doc["routes"]["default"] = deepcopy(doc["routes"]["task_change"])
    assert any("fallback" in error for error in validate_interaction_router(doc))
