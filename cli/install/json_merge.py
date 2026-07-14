"""Identity-based structural merge for Maika-owned host JSON nodes."""

from __future__ import annotations

from copy import deepcopy
from typing import Any


MAIKA_WRITE_GATE_ID = "maika.write-gate.v1"


class ManagedJsonError(ValueError):
    pass


def _managed_id(item: Any) -> str | None:
    if not isinstance(item, dict):
        return None
    identity = item.get("id")
    if isinstance(identity, str) and identity.startswith("maika.write-gate.") \
            and identity != MAIKA_WRITE_GATE_ID:
        raise ManagedJsonError(f"unknown Maika hook schema version: {identity}")
    return identity if identity == MAIKA_WRITE_GATE_ID else None


def _legacy_write_gate(item: Any) -> bool:
    """Narrow compatibility match on the command leaf, never a subtree dump."""
    if not isinstance(item, dict) or item.get("id") is not None:
        return False
    command = item.get("command")
    if not isinstance(command, str):
        return False
    normalized = " ".join(command.split()).lower()
    return normalized.startswith("maika hook write-gate ") or \
        "hooks/write-gate/write_gate.py" in normalized.replace("\\", "/")


def _validate_unique_ids(items: list) -> None:
    found = []
    for item in items:
        identity = _managed_id(item)
        if identity:
            found.append(identity)
    if len(found) != len(set(found)):
        raise ManagedJsonError(f"duplicate managed hook id: {MAIKA_WRITE_GATE_ID}")


def merge_managed_json(existing: Any, managed: Any) -> Any:
    if isinstance(existing, dict) and isinstance(managed, dict):
        result = deepcopy(existing)
        for key, value in managed.items():
            result[key] = merge_managed_json(result[key], value) if key in result else deepcopy(value)
        return result
    if isinstance(existing, list) and isinstance(managed, list):
        _validate_unique_ids(existing)
        _validate_unique_ids(managed)
        result = deepcopy(existing)
        for incoming in managed:
            identity = _managed_id(incoming)
            if identity:
                matches = [i for i, item in enumerate(result)
                           if _managed_id(item) == identity or _legacy_write_gate(item)]
                if len(matches) > 1:
                    raise ManagedJsonError(f"duplicate managed hook id: {identity}")
                if matches:
                    result[matches[0]] = merge_managed_json(result[matches[0]], incoming)
                else:
                    result.append(deepcopy(incoming))
                continue
            if isinstance(incoming, dict) and "matcher" in incoming and "hooks" in incoming:
                matches = [i for i, item in enumerate(result)
                           if isinstance(item, dict) and item.get("matcher") == incoming.get("matcher")]
                if len(matches) > 1:
                    raise ManagedJsonError(f"duplicate hook matcher: {incoming.get('matcher')}")
                if matches:
                    result[matches[0]] = merge_managed_json(result[matches[0]], incoming)
                else:
                    result.append(deepcopy(incoming))
            elif incoming not in result:
                result.append(deepcopy(incoming))
        return result
    return deepcopy(managed)


def remove_maika_json_entry(value: Any) -> Any:
    if isinstance(value, dict):
        _managed_id(value)  # unknown schema fails closed
        return {key: remove_maika_json_entry(item) for key, item in value.items()}
    if isinstance(value, list):
        _validate_unique_ids(value)
        return [remove_maika_json_entry(item) for item in value
                if _managed_id(item) is None and not _legacy_write_gate(item)]
    return value


def contains_maika_json_entry(value: Any) -> bool:
    if isinstance(value, dict):
        if _managed_id(value) == MAIKA_WRITE_GATE_ID or _legacy_write_gate(value):
            return True
        return any(contains_maika_json_entry(item) for item in value.values())
    if isinstance(value, list):
        _validate_unique_ids(value)
        return any(contains_maika_json_entry(item) for item in value)
    return False
