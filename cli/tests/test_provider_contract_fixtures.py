from __future__ import annotations

import json
from pathlib import Path

import yaml

from cli.mcp.integration.contract_fixtures import (
    content_sha256,
    load_contract_fixture,
    validate_fixture_directory,
)


FIXTURES = Path(__file__).parent / "fixtures" / "provider_contracts"


def test_pinned_provider_contract_fixture_directory_is_valid():
    assert validate_fixture_directory(FIXTURES) == []


def test_fixture_hash_is_deterministic():
    path = FIXTURES / "understand-anything" / "graph-metadata-v1.json"
    first, provenance = load_contract_fixture(path)
    second, _ = load_contract_fixture(path)
    assert first == second
    assert provenance["content_sha256"] == content_sha256(path.read_bytes())


def test_missing_provenance_is_rejected(tmp_path):
    path = tmp_path / "response.json"
    path.write_text("{}\n", encoding="utf-8")
    try:
        load_contract_fixture(path)
    except ValueError as exc:
        assert "provenance not found" in str(exc)
    else:
        raise AssertionError("missing provenance must be rejected")


def test_hash_mismatch_is_rejected(tmp_path):
    path = tmp_path / "response.json"
    path.write_text(json.dumps({"ok": True}) + "\n", encoding="utf-8")
    path.with_suffix(".provenance.yaml").write_text(
        yaml.safe_dump({
            "provider": "fixture",
            "repository": "owner/repo",
            "revision": "abc",
            "captured_at": "2026-07-15T00:00:00Z",
            "tool": "probe",
            "contract_version": 1,
            "content_sha256": "sha256:wrong",
        }),
        encoding="utf-8",
    )
    try:
        load_contract_fixture(path)
    except ValueError as exc:
        assert "hash mismatch" in str(exc)
    else:
        raise AssertionError("hash mismatch must be rejected")
