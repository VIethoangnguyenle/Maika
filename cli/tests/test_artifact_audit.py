from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

import yaml

from cli.artifact_audit import audit_artifacts


ROOT = Path(__file__).resolve().parents[2]


def test_repository_artifact_audit_is_clean():
    assert audit_artifacts(ROOT) == []


def _fixture(root: Path, artifact: dict) -> None:
    registry = root / ".maika/config/artifact-registry.yaml"
    registry.parent.mkdir(parents=True)
    registry.write_text(yaml.safe_dump({
        "version": 1, "manifest_consumer_defaults": {}, "artifacts": [artifact],
    }), encoding="utf-8")
    manifest = root / "cli/plugin-manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text("version: 1\nplugins: []\n", encoding="utf-8")
    history = root / "docs/archive/implemented/index.yaml"
    history.parent.mkdir(parents=True)
    history.write_text("runtime_authority: false\ndefault_retrieval: exclude\n", encoding="utf-8")


def test_production_module_imported_only_by_tests_fails(tmp_path):
    shadow = tmp_path / "cli/shadow.py"
    shadow.parent.mkdir(parents=True)
    shadow.write_text("VALUE = 1\n", encoding="utf-8")
    (tmp_path / "cli/tests").mkdir()
    (tmp_path / "cli/tests/test_shadow.py").write_text("from cli import shadow\n", encoding="utf-8")
    _fixture(tmp_path, {
        "path": "cli/shadow.py", "type": "runtime", "ownership": "framework",
        "producer": "source", "consumers": ["test-shadow"], "runtime_authority": True,
        "policy_domain": "shadow", "status": "active",
    })
    assert any(item["check"] == "production-import" for item in audit_artifacts(tmp_path))


def test_duplicate_policy_owner_fails(tmp_path):
    one = {"path": "cli/one.py", "type": "runtime", "ownership": "framework",
           "producer": "source", "consumers": ["runtime"], "runtime_authority": True,
           "policy_domain": "same", "status": "active"}
    for name in ("one.py", "two.py"):
        path = tmp_path / "cli" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("# runtime\n", encoding="utf-8")
    _fixture(tmp_path, one)
    registry = yaml.safe_load((tmp_path / ".maika/config/artifact-registry.yaml").read_text())
    two = deepcopy(one); two["path"] = "cli/two.py"
    registry["artifacts"].append(two)
    (tmp_path / ".maika/config/artifact-registry.yaml").write_text(yaml.safe_dump(registry))
    assert any(item["check"] == "duplicate-policy" for item in audit_artifacts(tmp_path))


def test_compatibility_expiry_is_enforced(tmp_path):
    _fixture(tmp_path, {
        "path": "config#old", "type": "config", "ownership": "framework",
        "producer": "legacy", "consumers": ["repair"], "runtime_authority": False,
        "status": "compatibility",
        "expires_after": (date.today() - timedelta(days=1)).isoformat(),
    })
    assert any(item["check"] == "compatibility-expiry" for item in audit_artifacts(tmp_path))
