"""Canonical cross-provider evidence envelope.

The envelope is deliberately honest about unavailable upstream properties:
missing runtime versions, revisions, and immutable snapshots are recorded as
``unverified`` and degrade the observation instead of being inferred.
"""

from __future__ import annotations

import hashlib
import json


CONTRACT_VERSION = 1
UNVERIFIED = "unverified"


def _hash_mapping(value: dict) -> str:
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def build_evidence_envelope(
    *,
    record: dict,
    tool_contract: dict,
    normalized: dict | None = None,
) -> dict:
    """Bind adapter output to the invocation and tested tool contract."""
    normalized = dict(normalized or {})
    graph = normalized.pop("graph", None)
    snapshot = normalized.pop("provider_snapshot", None) or {}
    reasons = list(normalized.pop("degradation_reasons", None) or [])
    runtime_version = normalized.pop("provider_runtime_version", None) or UNVERIFIED
    project = normalized.pop("project", None) or (graph or {}).get("project") or UNVERIFIED
    source_revision = (
        normalized.pop("source_revision", None)
        or (graph or {}).get("repository_head")
        or snapshot.get("source_revision")
        or UNVERIFIED
    )
    working_tree_state = normalized.pop("working_tree_state", None) or UNVERIFIED
    status = normalized.pop("status", None) or record.get("status") or "degraded"
    if record.get("status") != "success":
        status = record.get("status") or "error"

    unavailable = []
    for key, value in (
        ("provider_runtime_version", runtime_version),
        ("project", project),
        ("source_revision", source_revision),
        ("working_tree_state", working_tree_state),
    ):
        if value == UNVERIFIED:
            unavailable.append(f"{key} unverified")
    if unavailable and status == "success":
        status = "degraded"
    reasons.extend(reason for reason in unavailable if reason not in reasons)

    envelope = {
        "contract_version": CONTRACT_VERSION,
        "provider_id": record["provider_id"],
        "provider_runtime_version": runtime_version,
        "tool": record["tool"],
        "tool_contract_hash": _hash_mapping(tool_contract or {}),
        "request_hash": record["request_hash"],
        "response_hash": record["response_hash"],
        "project": project,
        "source_revision": source_revision,
        "working_tree_state": working_tree_state,
        "provider_snapshot": snapshot,
        "observed_at": record["ended_at"],
        "status": status,
        "degradation_reasons": reasons,
        **normalized,
    }
    if graph:
        envelope["graph"] = graph
    return envelope


def validate_evidence_envelope(observation: dict) -> list[str]:
    required = {
        "contract_version", "provider_id", "provider_runtime_version", "tool",
        "tool_contract_hash", "request_hash", "response_hash", "project",
        "source_revision", "working_tree_state", "provider_snapshot", "observed_at",
        "status", "degradation_reasons",
    }
    errors = [f"missing {key}" for key in sorted(required - set(observation))]
    if observation.get("contract_version") != CONTRACT_VERSION:
        errors.append("unsupported contract_version")
    if observation.get("status") not in {"success", "error", "degraded"}:
        errors.append("invalid status")
    for key in ("tool_contract_hash", "request_hash", "response_hash"):
        value = str(observation.get(key) or "")
        if not value.startswith("sha256:") or len(value) != 71:
            errors.append(f"invalid {key}")
    if not isinstance(observation.get("provider_snapshot"), dict):
        errors.append("provider_snapshot must be a mapping")
    if not isinstance(observation.get("degradation_reasons"), list):
        errors.append("degradation_reasons must be a list")
    return errors
