"""Root-cause → single specialist role routing (Loop Engineer, W6).

The Loop Engineer diagnoses a root cause and routes to exactly one existing
specialist role. It does not itself write spec, plan, application code, or a
shared skill — it only names who should.
"""

from __future__ import annotations

ROUTES = {
    "spec_gap": "spec_writer",
    "plan_gap": "planner",
    "implementation_gap": "implementer",
    "verification_gap": "verification-specialist",
    "knowledge_gap": "knowledge_curator",
}


def route(root_cause: str) -> str:
    """Map a diagnosed root cause to its specialist role (raises on unknown)."""
    try:
        return ROUTES[root_cause]
    except KeyError:
        raise ValueError(f"no specialist role for root cause {root_cause!r}") from None
