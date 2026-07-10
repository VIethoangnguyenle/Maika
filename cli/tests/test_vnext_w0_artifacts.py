"""Schema validators for vNext W0 refactor artifacts (mechanical consumer, R1).

Master Plan v2 §5 (ledger), §26 W0 (matrix, maps). These tests ARE the
consumers that make the four YAML deliverables legal to exist.

Snapshot vs registry (v2 §26 W0): the consumer map and skill migration map
are BASELINE SNAPSHOTS pinned to the W0 baseline commit — validated here for
schema + internal consistency only, NEVER compared against the current tree.
The ledger and capability matrix are living registries.
"""
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs" / "refactor" / "maika-vnext"

LEDGER_STATUSES = {"proposed", "active", "deferred", "superseded", "removed"}
LEDGER_CLASSIFICATIONS = {
    "observed_failure",
    "reproducible_litmus",
    "external_requirement",
    "safety_boundary",
}
MIGRATION_CLASSES = {"retain", "merge", "rewrite", "deprecate", "delete"}
PLATFORMS = {"claude-code", "codex", "antigravity"}


def _load(name: str) -> dict:
    path = ART / name
    assert path.exists(), f"missing W0 deliverable: {path}"
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def test_consumer_map_schema():
    data = _load("artifact-consumer-map.yaml")
    assert data["version"] == 1
    assert data.get("baseline_commit"), "snapshot must pin its baseline commit"
    artifacts = data["artifacts"]
    assert artifacts, "consumer map must not be empty"
    for name, entry in artifacts.items():
        assert entry.get("producers"), f"{name}: producers required"
        assert entry.get("consumers") is not None, f"{name}: consumers key required"
        for ref in entry["producers"] + (entry["consumers"] or []):
            assert ref.get("path"), f"{name}: every ref needs a path"


def test_skill_migration_map_schema():
    data = _load("skill-migration-map.yaml")
    assert data["version"] == 1
    assert data.get("baseline_commit"), "snapshot must pin its baseline commit"
    skills = data["skills"]
    names = [e["skill"] for e in skills]
    assert len(names) == len(set(names)), "duplicate skill entries"
    cov = data["coverage"]
    assert cov["mapped_skill_count"] == len(skills)
    assert cov["expected_skill_count"] == cov["mapped_skill_count"]
    assert cov["status"] == "complete"
    for e in skills:
        assert e["classification"] in MIGRATION_CLASSES, e["skill"]
        if e["classification"] in {"deprecate", "delete"}:
            assert "consumers" in e, (
                f"{e['skill']}: deletion requires consumer evidence"
            )
        if e["classification"] in {"merge", "rewrite"}:
            assert e.get("target"), (
                f"{e['skill']}: {e['classification']} requires a target"
            )


def test_enforcement_ledger_schema():
    data = _load("enforcement-ledger.yaml")
    assert data["version"] == 1
    ids = [e["id"] for e in data["entries"]]
    assert len(ids) == len(set(ids)), "duplicate ledger ids"
    for e in data["entries"]:
        assert e["status"] in LEDGER_STATUSES, e["id"]
        assert e.get("mechanism"), e["id"]
        assert e.get("type") in {"gate", "hook", "validator"}, e["id"]
        if e["status"] == "active":
            cls = e["failure"]["classification"]
            assert cls in LEDGER_CLASSIFICATIONS, e["id"]
            assert e["failure"].get("summary"), e["id"]
            assert e.get("implementation", {}).get("files"), e["id"]
        if e["status"] == "deferred":
            assert e.get("activation_condition"), (
                f"{e['id']}: deferred entries need an activation condition (v2 §5)"
            )
        if e["status"] == "proposed":
            assert e.get("scheduled_wave"), f"{e['id']}: proposed needs scheduled_wave"


def test_capability_matrix_schema():
    data = _load("platform-capability-matrix.yaml")
    assert data["version"] == 1
    assert set(data["platforms"]) == PLATFORMS
    for platform, mechanisms in data["platforms"].items():
        assert mechanisms, f"{platform}: at least one mechanism row"
        for mech, row in mechanisms.items():
            assert "supported" in row, f"{platform}.{mech}"
            assert row.get("evidence"), (
                f"{platform}.{mech}: R4 requires file:line or command evidence"
            )
            assert row.get("verified_at"), f"{platform}.{mech}: verified_at date"
