"""Tests for PR9 artifact audit v2: mechanical consumer detection for .maika/tools."""

from datetime import date, timedelta
from pathlib import Path

import yaml

from cli.artifact_audit import audit_artifacts


def _v2_fixture(root: Path, *, extra_registry: dict | None = None,
                manifest_plugins: list | None = None,
                dynamic_consumers: list | None = None) -> None:
    """Create a minimal fake project tree with registry + manifest + history."""
    registry = root / ".maika/config/artifact-registry.yaml"
    registry.parent.mkdir(parents=True, exist_ok=True)
    reg_data = {
        "version": 1,
        "manifest_consumer_defaults": {"tool": "runtime-dispatch"},
        "artifact_groups": [
            {"path_glob": "cli/*.py", "type": "runtime", "ownership": "framework",
             "producer": "source", "consumers": ["cli-registration-or-production-import"],
             "runtime_authority": False, "status": "active"},
            {"path_glob": "cli/**/*.py", "type": "runtime", "ownership": "framework",
             "producer": "source", "consumers": ["cli-registration-or-production-import"],
             "runtime_authority": False, "status": "active",
             "exclude": ["cli/tests/**"]},
            {"path_glob": ".maika/**/*.py", "type": "runtime", "ownership": "framework",
             "producer": "source", "consumers": ["scaffolded-runtime-or-file-dispatch"],
             "runtime_authority": False, "status": "active",
             "exclude": [".maika/**/tests/**"]},
            {"path_glob": "scripts/*.py", "type": "runtime", "ownership": "framework",
             "producer": "source", "consumers": ["developer-cli-or-ci"],
             "runtime_authority": False, "status": "active"},
            {"path_glob": "docs/**/*.md", "type": "documentation", "ownership": "framework",
             "producer": "development-process", "consumers": ["developer-documentation"],
             "runtime_authority": False, "status": "active"},
        ],
        "artifacts": [],
    }
    if dynamic_consumers:
        reg_data["dynamic_consumers"] = dynamic_consumers
    if extra_registry:
        reg_data.update(extra_registry)
    registry.write_text(yaml.safe_dump(reg_data), encoding="utf-8")

    manifest = root / "cli/plugin-manifest.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(yaml.safe_dump({
        "version": "3.0",
        "plugins": manifest_plugins or [],
    }), encoding="utf-8")

    history = root / "docs/archive/implemented/index.yaml"
    history.parent.mkdir(parents=True, exist_ok=True)
    history.write_text("runtime_authority: false\ndefault_retrieval: exclude\n",
                       encoding="utf-8")


def test_dead_tool_module_fails(tmp_path):
    """A .maika/tools module with NO consumer triggers a dead-tool-module finding."""
    dead = tmp_path / ".maika/tools/example-tool/dead_module.py"
    dead.parent.mkdir(parents=True)
    dead.write_text("VALUE = 42\n", encoding="utf-8")
    _v2_fixture(tmp_path)
    findings = audit_artifacts(tmp_path)
    dead_findings = [f for f in findings if f["check"] == "dead-tool-module"]
    assert len(dead_findings) == 1
    assert ".maika/tools/example-tool/dead_module.py" in dead_findings[0]["path"]


def test_file_dispatched_module_passes(tmp_path):
    """A .maika/tools module that is file-dispatched by a production .py → no finding."""
    # Create the tool module
    tool = tmp_path / ".maika/tools/myloop/loop_state.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("STATE = 'idle'\n", encoding="utf-8")
    # Create a production file that dispatches it
    dispatcher = tmp_path / "cli/commands/loop.py"
    dispatcher.parent.mkdir(parents=True, exist_ok=True)
    dispatcher.write_text(
        'import importlib.util\n'
        'def _load_module(target, fr, name):\n'
        '    spec = importlib.util.spec_from_file_location(f"maika_{name}", "loop_state.py")\n'
        '    return spec\n'
        'mod = _load_module(None, None, "loop_state")\n',
        encoding="utf-8",
    )
    _v2_fixture(tmp_path)
    findings = audit_artifacts(tmp_path)
    assert not any(f["check"] == "dead-tool-module" for f in findings)


def test_consumer_report_uses_deterministic_source_order(tmp_path):
    """The checked report must not depend on filesystem traversal order."""
    tool = tmp_path / ".maika/tools/example/helper.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("VALUE = 1\n", encoding="utf-8")
    for name in ("z_consumer.py", "a_consumer.py"):
        consumer = tmp_path / "cli" / name
        consumer.parent.mkdir(parents=True, exist_ok=True)
        consumer.write_text("import helper\n", encoding="utf-8")
    _v2_fixture(tmp_path)

    audit_artifacts(tmp_path, write_report=True)

    report = yaml.safe_load(
        (tmp_path / "docs/refactor/master-v2/artifact-consumer-audit-v2.yaml").read_text()
    )
    helper = next(item for item in report["modules"] if item["path"].endswith("helper.py"))
    assert helper["consumed_by"] == "python-import:cli/a_consumer.py"


def test_manifest_plugin_module_without_consumer_fails(tmp_path):
    """Manifest membership is producer evidence, never consumer evidence."""
    tool = tmp_path / ".maika/tools/gate-check/gates.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("def validate(): pass\n", encoding="utf-8")
    _v2_fixture(tmp_path, manifest_plugins=[{
        "name": "gate-check", "type": "tool",
        "source": "tools/gate-check/", "template": False,
        "output": "{{ platform.framework_root }}/tools/gate-check/",
        "copy_dir": True,
    }])
    findings = audit_artifacts(tmp_path)
    assert any(f["check"] == "dead-tool-module" for f in findings)


def test_test_only_module_fails(tmp_path):
    """A .maika/tools module consumed only by test files → dead-tool-module finding."""
    tool = tmp_path / ".maika/tools/example-tool/helper.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("def do_thing(): return 1\n", encoding="utf-8")
    # Only a test file imports it
    test_file = tmp_path / ".maika/tools/example-tool/tests/test_helper.py"
    test_file.parent.mkdir(parents=True)
    test_file.write_text("import helper\n\ndef test_it(): assert helper.do_thing() == 1\n",
                         encoding="utf-8")
    _v2_fixture(tmp_path)
    findings = audit_artifacts(tmp_path)
    dead = [f for f in findings if f["check"] == "dead-tool-module"]
    assert len(dead) == 1
    assert "helper.py" in dead[0]["path"]


def test_compatibility_expiry_future_passes(tmp_path):
    """A compatibility artifact with a future expires_after → no finding."""
    _v2_fixture(tmp_path, extra_registry={
        "artifacts": [{
            "path": "config#old_key", "type": "config", "ownership": "framework",
            "producer": "legacy", "consumers": ["repair"], "runtime_authority": False,
            "status": "compatibility",
            "expires_after": (date.today() + timedelta(days=30)).isoformat(),
        }],
    })
    findings = audit_artifacts(tmp_path)
    assert not any(f["check"] == "compatibility-expiry" for f in findings)


def test_compatibility_expiry_past_fails(tmp_path):
    """A compatibility artifact with a past expires_after → finding."""
    _v2_fixture(tmp_path, extra_registry={
        "artifacts": [{
            "path": "config#old_key", "type": "config", "ownership": "framework",
            "producer": "legacy", "consumers": ["repair"], "runtime_authority": False,
            "status": "compatibility",
            "expires_after": (date.today() - timedelta(days=1)).isoformat(),
        }],
    })
    findings = audit_artifacts(tmp_path)
    assert any(f["check"] == "compatibility-expiry" for f in findings)


def test_dynamic_consumer_passes(tmp_path):
    """A .maika/tools module matching a dynamic_consumers entry → no finding."""
    tool = tmp_path / ".maika/tools/my-tool/runner.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("if __name__ == '__main__': print('hi')\n", encoding="utf-8")
    # Create the loader file
    loader = tmp_path / "scripts/run_ci.py"
    loader.parent.mkdir(parents=True, exist_ok=True)
    loader.write_text("# CI runner\n", encoding="utf-8")
    _v2_fixture(tmp_path, dynamic_consumers=[{
        "loader": "scripts/run_ci.py",
        "pattern": ".maika/tools/my-tool/runner.py",
        "reason": "CI pipeline tool",
    }])
    findings = audit_artifacts(tmp_path)
    assert not any(f["check"] == "dead-tool-module" for f in findings)


def test_cli_entrypoint_in_procedure_passes(tmp_path):
    """A tool module with __main__ referenced in procedures → no finding."""
    tool = tmp_path / ".maika/tools/my-tool/cli.py"
    tool.parent.mkdir(parents=True)
    tool.write_text("import sys\nif __name__ == '__main__': sys.exit(0)\n",
                    encoding="utf-8")
    # Reference it in a procedure
    proc = tmp_path / ".maika/procedures/bootstrap.md"
    proc.parent.mkdir(parents=True, exist_ok=True)
    proc.write_text("Run: `python3 .maika/tools/my-tool/cli.py`\n", encoding="utf-8")
    _v2_fixture(tmp_path)
    findings = audit_artifacts(tmp_path)
    assert not any(f["check"] == "dead-tool-module" for f in findings)
