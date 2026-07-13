"""Provider invocation evidence — host-delegated MCP call records (plan §7/§12).

Maika does not own MCP connections: the host platform calls the MCP tool, then
the raw request/response payloads are passed through here so every record
carries content hashes. The mechanical guarantee is linkage only — the call
was recorded against a registered provider/tool and the hashes bind the record
to concrete payloads. Hashing cannot prove the semantic truth of a text
response (execution errata E6); gates validate linkage and coverage, not
content truth. Validation lives in tools/gate-check (validate_provider_invocations)
— this module only produces records.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

INVOCATION_MODE = "host_mcp"
STATUSES = ("success", "error", "timeout")
REQUIRED_FIELDS = (
    "trace_id", "change_id", "role", "provider_id", "tool", "invocation_mode",
    "request_hash", "response_hash", "started_at", "ended_at", "status",
)


def hash_payload(payload: bytes | str) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return "sha256:" + hashlib.sha256(data).hexdigest()


def new_trace_id() -> str:
    return uuid.uuid4().hex


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def build_invocation_record(
    *,
    change_id: str,
    role: str,
    provider_id: str,
    tool: str,
    request_payload: bytes | str,
    response_payload: bytes | str,
    status: str,
    started_at: str,
    ended_at: str,
    trace_id: str | None = None,
    normalized_artifact: str = "",
    trigger: str = "",
    reason: str = "",
) -> dict:
    if status not in STATUSES:
        raise ValueError(f"status must be one of {STATUSES}: {status!r}")
    record = {
        "trace_id": trace_id or new_trace_id(),
        "change_id": change_id,
        "role": role,
        "provider_id": provider_id,
        "tool": tool,
        "invocation_mode": INVOCATION_MODE,
        "request_hash": hash_payload(request_payload),
        "response_hash": hash_payload(response_payload),
        "started_at": started_at,
        "ended_at": ended_at,
        "status": status,
        "normalized_artifact": normalized_artifact,
        "trigger": trigger,
        "reason": reason,
    }
    missing = [field for field in REQUIRED_FIELDS if not record.get(field)]
    if missing:
        raise ValueError(f"invocation record missing required fields: {missing}")
    return record


def append_invocation(path: Path, record: dict) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    return path
