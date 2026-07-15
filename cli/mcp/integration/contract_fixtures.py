"""Pinned external-provider contract fixture helpers.

Fixtures are test evidence, not runtime discovery.  Every payload must be paired
with a provenance sidecar so a response copied from an upstream provider cannot
silently become an unversioned Maika contract.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import yaml


REQUIRED_PROVENANCE = {
    "provider",
    "repository",
    "revision",
    "captured_at",
    "tool",
    "contract_version",
    "content_sha256",
}


def content_sha256(payload: bytes) -> str:
    return "sha256:" + hashlib.sha256(payload).hexdigest()


def load_contract_fixture(payload_path: Path) -> tuple[object, dict]:
    """Load and validate a JSON fixture plus ``.provenance.yaml`` sidecar."""
    payload_path = Path(payload_path)
    sidecar = payload_path.with_suffix(".provenance.yaml")
    if not payload_path.is_file():
        raise ValueError(f"contract fixture payload not found: {payload_path}")
    if not sidecar.is_file():
        raise ValueError(f"contract fixture provenance not found: {sidecar}")
    raw = payload_path.read_bytes()
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid JSON contract fixture {payload_path}: {exc}") from exc
    provenance = yaml.safe_load(sidecar.read_text(encoding="utf-8"))
    if not isinstance(provenance, dict):
        raise ValueError(f"contract fixture provenance must be a mapping: {sidecar}")
    missing = sorted(REQUIRED_PROVENANCE - set(provenance))
    if missing:
        raise ValueError(f"contract fixture provenance missing {missing}: {sidecar}")
    for field in REQUIRED_PROVENANCE - {"contract_version"}:
        if not str(provenance.get(field) or "").strip():
            raise ValueError(f"contract fixture provenance has empty {field}: {sidecar}")
    if not isinstance(provenance.get("contract_version"), int):
        raise ValueError(f"contract fixture contract_version must be integer: {sidecar}")
    actual = content_sha256(raw)
    if provenance["content_sha256"] != actual:
        raise ValueError(
            f"contract fixture hash mismatch for {payload_path}: "
            f"expected {provenance['content_sha256']}, got {actual}"
        )
    return payload, provenance


def validate_fixture_directory(root: Path) -> list[str]:
    """Return validation errors for every JSON fixture and duplicate identity."""
    root = Path(root)
    errors: list[str] = []
    identities: dict[tuple[str, str, str, int], str] = {}
    for payload_path in sorted(root.rglob("*.json")):
        try:
            _, provenance = load_contract_fixture(payload_path)
        except ValueError as exc:
            errors.append(str(exc))
            continue
        identity = (
            str(provenance["provider"]),
            str(provenance["revision"]),
            str(provenance["tool"]),
            int(provenance["contract_version"]),
        )
        digest = str(provenance["content_sha256"])
        previous = identities.get(identity)
        if previous is not None and previous != digest:
            errors.append(
                "duplicate fixture identity has different content: "
                f"{identity!r} ({previous} != {digest})"
            )
        identities[identity] = digest
    if not list(root.rglob("*.json")):
        errors.append(f"no JSON contract fixtures under {root}")
    return errors
