import json
import subprocess
import sys
from pathlib import Path
import yaml
import pytest

def test_vnext_cli_e2e(tmp_path):
    # Setup fixture
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    # Python script to mock the worker
    mock_worker = tmp_path / "mock_worker.py"
    mock_worker.write_text("""import sys, re
prompt = sys.argv[1]
out_path = re.search(r'^OUTPUT_FILE: (.+)$', prompt, re.M).group(1)
with open(out_path, 'w') as f:
    f.write("VERDICT: APPROVED\\n" if "plan-review" in out_path else "stub result")
""")
    (prof / "execution-mode.yaml").write_text(f"workflow_engine: vnext\nworker_command: '{sys.executable} {mock_worker} {{prompt}}'\n")
    
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]
    
    # Init
    res = subprocess.run(cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "small", "--title", "t"], capture_output=True, text=True)
    assert res.returncode == 0
    ws = ch_root / "demo"
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "INTAKE"
    
    # Need PLAN and SPEC for compile
    (ws / "SPEC.md").write_text("# spec\n")
    import hashlib
    spec_sha = hashlib.sha256((ws / "SPEC.md").read_bytes()).hexdigest()
    
    plan_text = f"""---
change_id: demo
plan_version: 1
base_commit: deadbeef
spec_hash: sha256:{spec_sha}
evidence_hash: sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
---

# Plan

### TASK-001: Demo

```yaml
task:
  id: TASK-001
  implementation_mode: exact
  verification:
    command: pytest
    expected: pass
```

Body
"""
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text)
    
    # Mock base_commit resolve in gates.py
    # Since we can't easily mock git in this E2E test, we'll bypass the git check by initializing a git repo.
    subprocess.run(["git", "init", "-q"], cwd=tmp_path)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path)
    subprocess.run(["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "base"], cwd=tmp_path)
    sha = subprocess.run(["git", "rev-parse", "HEAD"], cwd=tmp_path, capture_output=True, text=True).stdout.strip()
    
    (ws / "IMPLEMENTATION_PLAN.md").write_text(plan_text.replace("deadbeef", sha))
    
    # Compile
    res = subprocess.run(cmd + ["vnext-compile", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "PLAN_REVIEW"
    
    # Review
    res = subprocess.run(cmd + ["vnext-review-plan", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert yaml.safe_load((ws / "STATE.yaml").read_text())["state"] == "PLAN_REVIEW"
    
    # Run
    # The runner stub in orchestrator will just output stub which is invalid result, so it will block.
    res = subprocess.run(cmd + ["vnext-run", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    st = yaml.safe_load((ws / "STATE.yaml").read_text())["state"]
    # state should be EXECUTING because task blocked
    assert st == "EXECUTING"
    
    # Status
    res = subprocess.run(cmd + ["vnext-status", "--workspace", str(ws), "--repo-root", str(tmp_path)], capture_output=True, text=True)
    assert res.returncode == 0
    assert "State: EXECUTING" in res.stdout

def test_refuse_legacy(tmp_path):
    fw_root = tmp_path / ".maika"
    fw_root.mkdir()
    prof = fw_root / "profiles"
    prof.mkdir()
    (prof / "execution-mode.yaml").write_text("workflow_engine: legacy\n")
    
    ch_root = tmp_path / ".maika" / "changes"
    ch_root.mkdir()
    
    orch = Path(__file__).resolve().parents[1] / "orchestrator.py"
    cmd = [sys.executable, str(orch)]
    
    res = subprocess.run(cmd + ["vnext-init", "--changes-root", str(ch_root), "--id", "demo", "--class", "small", "--title", "t"], capture_output=True, text=True)
    assert res.returncode == 2
    assert "Refused" in res.stdout
