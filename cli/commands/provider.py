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

from cli.mcp.integration import codebase_memory, current_source, understand_anything
from cli.mcp.integration.base import (
    append_invocation,
    build_invocation_record,
    utc_now,
)
from cli.mcp.integration.trace_store import (
    add_observation,
    add_source_verification,
    add_support_call,
)
from cli.scaffold import load_resolved_config

INVOCATIONS_REL = "exploration/PROVIDER_INVOCATIONS.jsonl"


def _framework_root(target: Path) -> str:
    resolved = load_resolved_config(target)
    return (resolved or {}).get("framework_root", ".maika")


def _verify_source_action(target: Path, framework: Path, change_id: str,
                          file: str, symbol: str) -> int:
    workspace = framework / "changes" / change_id
    if not (workspace / "STATE.yaml").exists() and not (workspace / "CHANGE.yaml").exists():
        print(f"no such change workspace: {workspace}")
        return 1
    try:
        entry = current_source.verify_source(target, file, symbol or None)
    except (FileNotFoundError, ValueError) as exc:
        print(f"source verification failed: {exc}")
        return 1
    path = add_source_verification(workspace, change_id, entry)
    print(f"verified {file} -> {path}")
    print(f"sha256={entry['sha256']}")
    return 0


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
    file: str | None = None,
    symbol: str = "",
) -> int:
    if action == "verify-source":
        if not change_id or not file:
            print("provider verify-source requires --id and --file")
            return 2
        target = Path(target_dir).resolve()
        return _verify_source_action(
            target, target / _framework_root(target), change_id, file, symbol
        )
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

    # DB lane safety boundary (plan §11, M7): task-workspace recording only
    # accepts exploration-lane tools; data-probe tools additionally require an
    # explicit data_probe_required: true in DATABASE_REQUEST.yaml. Write and
    # script tools are never task-workspace evidence (R-Tool-9).
    lanes = (spec.get("tool_contract") or {}).get("lanes") or {}
    if lanes:
        exploration = set((lanes.get("exploration") or {}).get("tools") or [])
        data_probe = set((lanes.get("data_probe") or {}).get("tools") or [])
        if tool not in exploration:
            if tool in data_probe:
                request_path = workspace / "exploration" / "DATABASE_REQUEST.yaml"
                request = (yaml.safe_load(request_path.read_text(encoding="utf-8"))
                           if request_path.exists() else None) or {}
                if request.get("data_probe_required") is not True:
                    print(f"tool {tool!r} is data-probe lane; DATABASE_REQUEST.yaml "
                          "must declare data_probe_required: true (explicit runtime "
                          "data question)")
                    return 1
            else:
                print(f"tool {tool!r} is outside the exploration lane "
                      f"(write/script tools are never exploration evidence)")
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

    # Adapter normalization (plan §13): machine-produced TRACE_EVIDENCE sections.
    response_bytes = Path(response_file).read_bytes()
    if provider_id == understand_anything.PROVIDER_ID:
        observation = understand_anything.normalize_response(tool, response_bytes)
        add_observation(workspace, change_id, observation)
    elif provider_id == codebase_memory.PROVIDER_ID:
        if trigger:
            try:
                support = codebase_memory.build_support_call(
                    tool=tool, trigger=trigger, reason=reason, raw=response_bytes,
                )
            except ValueError as exc:
                print(f"support call rejected: {exc}")
                return 1
            add_support_call(workspace, change_id, support)
        else:
            print("warning: CBM call recorded without --trigger; the trace-evidence "
                  "gate rejects conditional support without trigger + reason")

    print(f"recorded {provider_id}/{tool} -> {path}")
    print(f"request_hash={record['request_hash']}")
    print(f"response_hash={record['response_hash']}")
    return 0
