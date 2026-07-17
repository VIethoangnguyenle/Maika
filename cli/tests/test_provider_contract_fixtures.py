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
PROJECT_ROOT = Path(__file__).parents[2]

SERENA_READ_TOOLS = [
    "get_symbols_overview",
    "find_symbol",
    "find_referencing_symbols",
    "find_implementations",
    "find_declaration",
    "get_diagnostics_for_file",
    "get_diagnostics_for_symbol",
    "restart_language_server",
]


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


def test_serena_context_is_runnable_fixed_readonly_surface():
    path = PROJECT_ROOT / ".maika" / "config" / "serena-context.yml"
    context = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert context["fixed_tools"] == SERENA_READ_TOOLS
    assert "structured_tool_output" not in context


def test_serena_fixture_pins_release_provenance():
    path = FIXTURES / "serena" / "tools-list-readonly-v1.json"
    fixture, provenance = load_contract_fixture(path)
    assert provenance == {
        "provider": "serena",
        "repository": "oraios/serena",
        "revision": "2449313c0d7427275c4c66aedff7d4881782f713",
        "captured_at": "2026-07-16T00:00:00Z",
        "tool": "tools/list",
        "contract_version": 1,
        "content_sha256": "sha256:9a93c0321b48aa5b4fc1e40a3e2a4f13503c5e1f30341d4ea6cb57eb9c2f6a0c",
    }
    assert {tool["name"] for tool in fixture["tools"]} == set(SERENA_READ_TOOLS)
