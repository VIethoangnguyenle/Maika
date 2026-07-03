"""Static guards for GitHub Actions workflow portability."""

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parent.parent.parent
CI = REPO_ROOT / ".github" / "workflows" / "ci.yml"


def test_ci_workflow_forces_utf8_python_output():
    workflow = yaml.safe_load(CI.read_text(encoding="utf-8"))
    assert workflow["env"]["PYTHONIOENCODING"] == "utf-8"
