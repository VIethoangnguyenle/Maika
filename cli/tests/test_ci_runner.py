import importlib.util
from pathlib import Path


def _load_runner():
    runner = Path(__file__).resolve().parents[2] / "scripts" / "run_ci.py"
    spec = importlib.util.spec_from_file_location("run_ci", runner)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_ci_runner_covers_vnext_enforcement_columns():
    run_ci = _load_runner()

    paths = {path for group in run_ci.TEST_GROUPS for path in group["paths"]}

    assert "cli/tests" in paths
    assert ".maika/tools/gate-check/tests" in paths
    assert ".maika/tools/microloop-orchestrator/tests" in paths
    assert ".maika/hooks/write-gate/tests" in paths
    assert ".maika/tools/knowledge-index/tests" in paths
    assert ".maika/tools/rule-projector/tests" in paths


def test_ci_runner_covers_session_interaction_content_checks():
    run_ci = _load_runner()

    assert run_ci.CONTENT_CHECKS == [
        "validate-interactions",
        "validate-external-workflows",
        "validate-generated-reports",
        "validate-provider-capabilities",
        "validate-system-model",
    ]
