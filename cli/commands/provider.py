"""maika provider — host-delegated provider invocation evidence (plan §12).

The host platform makes the actual MCP call; the worker then records it here
so the workspace carries hash-bound invocation evidence instead of prose
claims (blocker B3). Record-time checks fail fast on unregistered providers
or tools outside the tested snapshot; full validation is the
provider-invocations gate.
"""

from __future__ import annotations

from pathlib import Path

import yaml

from cli.mcp.integration.base import (
    append_invocation,
    build_invocation_record,
    utc_now,
)
from cli.scaffold import load_resolved_config

INVOCATIONS_REL = "exploration/PROVIDER_INVOCATIONS.jsonl"


def _framework_root(target: Path) -> str:
    resolved = load_resolved_config(target)
    return (resolved or {}).get("framework_root", ".maika")


def run_provider(
    action: str,
    *,
    target_dir: str = ".",
    change_id: str | None = None,
    provider_id: str | None = None,
    tool: str | None = None,
    role: str | None = None,
    request_file: str | None = None,
    response_file: str | None = None,
    status: str = "success",
    started_at: str | None = None,
    ended_at: str | None = None,
    trace_id: str | None = None,
    normalized_artifact: str = "",
    trigger: str = "",
    reason: str = "",
) -> int:
    if action != "record":
        print(f"Unknown provider action: {action}")
        return 2
    missing = [name for name, value in (
        ("--id", change_id), ("--provider", provider_id), ("--tool", tool),
        ("--role", role), ("--request-file", request_file),
        ("--response-file", response_file),
    ) if not value]
    if missing:
        print(f"provider record requires {', '.join(missing)}")
        return 2

    target = Path(target_dir).resolve()
    framework = target / _framework_root(target)
    registry_path = framework / "config" / "provider-registry.yaml"
    if not registry_path.exists():
        print(f"provider registry not found: {registry_path}")
        return 1
    providers = (yaml.safe_load(registry_path.read_text(encoding="utf-8")) or {}).get(
        "providers"
    ) or {}
    spec = providers.get(provider_id)
    if spec is None:
        print(f"unknown provider {provider_id!r}; registered: {sorted(providers)}")
        return 1
    snapshot = set(((spec.get("tool_contract") or {}).get("tools")) or [])
    if snapshot and tool not in snapshot:
        print(f"tool {tool!r} not in {provider_id} tested tool snapshot")
        return 1

    workspace = framework / "changes" / change_id
    if not (workspace / "STATE.yaml").exists() and not (workspace / "CHANGE.yaml").exists():
        print(f"no such change workspace: {workspace}")
        return 1

    for label, payload_file in (("request", request_file), ("response", response_file)):
        if not Path(payload_file).exists():
            print(f"{label} payload file not found: {payload_file}")
            return 1

    now = utc_now()
    record = build_invocation_record(
        change_id=change_id,
        role=role,
        provider_id=provider_id,
        tool=tool,
        request_payload=Path(request_file).read_bytes(),
        response_payload=Path(response_file).read_bytes(),
        status=status,
        started_at=started_at or now,
        ended_at=ended_at or now,
        trace_id=trace_id,
        normalized_artifact=normalized_artifact,
        trigger=trigger,
        reason=reason,
    )
    path = append_invocation(workspace / INVOCATIONS_REL, record)
    print(f"recorded {provider_id}/{tool} -> {path}")
    print(f"request_hash={record['request_hash']}")
    print(f"response_hash={record['response_hash']}")
    return 0
