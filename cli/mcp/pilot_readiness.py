"""Mechanical safety/readiness assessment for the constrained provider pilot."""

from __future__ import annotations


def assess_pilot_readiness(registry: dict, provider_statuses: dict) -> dict:
    providers = registry.get("providers") or {}
    blockers: list[str] = []
    degraded: list[str] = []

    authority = registry.get("authority") or {}
    if (authority.get("exact_current_source") or {}).get("authoritative") != "current-source":
        blockers.append("current-source is not authoritative for exact current facts")

    memory = providers.get("agent-memory") or {}
    hooks = memory.get("hooks") or {}
    if any(hooks.get(key) is not False for key in ("auto_capture", "session_injection", "stop_summary")):
        blockers.append("AgentMemory automatic capture/injection is enabled")
    if memory.get("agent_id_semantics") != "retrieval_filter_only":
        blockers.append("AgentMemory agentId is not constrained to retrieval filtering")

    db = (((providers.get("db-access") or {}).get("tool_contract") or {}).get("lanes") or {})
    exploration_db = set((db.get("exploration") or {}).get("tools") or [])
    if exploration_db & {"sql_write", "mongo_write", "sql_execute_script"}:
        blockers.append("DB exploration lane exposes write/script tools")

    for provider_id in ("understand-anything", "agent-memory", "db-access"):
        status = provider_statuses.get(provider_id) or {}
        if not status:
            degraded.append(f"{provider_id}: readiness probe missing")
            continue
        if status.get("status") not in {"ready", "success"}:
            degraded.append(f"{provider_id}: {status.get('status') or 'unverified'}")
        for prop in status.get("unverified") or []:
            degraded.append(f"{provider_id}.{prop}: unverified")

    decision = "blocked" if blockers else ("conditional-pilot" if degraded else "pilot-ready")
    return {
        "contract_version": 1,
        "decision": decision,
        "production_ready": False,
        "blockers": blockers,
        "degraded_or_unverified": degraded,
        "enabled_scope": [
            "current-source inspection", "UA read-only discovery",
            "AgentMemory candidate-only recall", "DB schema/read via read-only principal",
        ],
        "disabled_scope": [
            "unscoped source writes",
            "AgentMemory automatic capture/canonical persistence", "DB write/script",
        ],
    }


def render_pilot_readiness(report: dict) -> str:
    lines = [
        "# Maika Provider Pilot Readiness\n",
        f"- Decision: {report['decision']}",
        "- Production ready: no",
    ]
    for title, key in (("Blockers", "blockers"),
                       ("Degraded or unverified", "degraded_or_unverified"),
                       ("Enabled scope", "enabled_scope"),
                       ("Disabled scope", "disabled_scope")):
        lines.extend(["", f"## {title}", ""])
        values = report.get(key) or []
        lines.extend(f"- {value}" for value in values)
        if not values:
            lines.append("- None")
    return "\n".join(lines) + "\n"
