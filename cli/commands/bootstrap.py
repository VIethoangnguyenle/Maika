"""Produce and validate the machine-readable Maika bootstrap report."""

from __future__ import annotations

import importlib.util
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.mcp.doctor import build_doctor_status, write_report
from cli.platforms import get_platform
from cli.scaffold import generate_knowledge_index, load_resolved_config


def run_bootstrap(target_dir: str = ".", home: Path | None = None) -> int:
    target = Path(target_dir).resolve()
    resolved = load_resolved_config(target)
    if resolved is None:
        print("Refused: Maika is not initialized")
        return 2
    framework_root = resolved.get("framework_root", ".maika")
    framework = target / framework_root
    maika_root = Path(__file__).resolve().parents[2]
    generate_knowledge_index(maika_root, target, framework_root)
    index_path = framework / "knowledge" / "long-term" / "knowledge-index.yaml"
    index = yaml.safe_load(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    status = build_doctor_status(target, home or Path.home(), maika_root=maika_root)
    write_report(target, status)
    probes, degradation = [], []
    for provider_id in status.selected_mcps:
        if provider_id == "agent-memory":
            healthy = status.memory_daemon == "running"
            probe_status = "healthy" if healthy else "unavailable"
            evidence = f"daemon:{status.memory_daemon} url:{status.memory_daemon_url}"
        else:
            healthy = False  # config discovery is not a native MCP tool probe
            probe_status = "configured-unprobed" if provider_id in status.matched else "unavailable"
            evidence = f"native_config:{status.native_state}; bridge:{status.bridge_state}"
        probes.append({"provider_id": provider_id, "status": probe_status, "evidence": evidence})
        if not healthy:
            degradation.append({"provider_id": provider_id, "status": probe_status,
                                "fallback": "current-source/read-only local evidence"})
    rule_names = ["RULES.md", "rules-flow.md", "rules-tool.md", "rules-exec.md",
                  "rules-knowledge.md", "rules-skill-evolution.md", "rules-guard.md"]
    rules_loaded = [name for name in rule_names if (
        framework / "rules" / name if name != "RULES.md" else framework / "rules" / "RULES.md"
    ).exists()]
    changes = framework / "changes"
    active = sorted(path.parent.name for path in changes.glob("*/STATE.yaml")) if changes.exists() else []
    commit_probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target,
                                  capture_output=True, text=True, check=False)
    repository_commit = commit_probe.stdout.strip() if commit_probe.returncode == 0 else "unavailable"
    report = {
        "version": 1, "completed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository_commit": repository_commit,
        "entry_point": get_platform(resolved.get("platform", "generic")).config_entry_point,
        "rules_loaded": rules_loaded,
        "knowledge_index": {"status": "loaded" if index_path.exists() else "missing",
                            "entries": len((index or {}).get("entries") or [])},
        "configured_providers": status.selected_mcps,
        "provider_probes": probes,
        "episodic_provider_health": status.memory_daemon,
        "active_state": active or "empty",
        "resume_state": "resume" if active else "new",
        "degradation": degradation,
    }
    report_path = framework / "knowledge" / "active" / "BOOTSTRAP_REPORT.yaml"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding="utf-8")
    gate_path = framework / "tools" / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("maika_bootstrap_gate", gate_path)
    gates = importlib.util.module_from_spec(spec); spec.loader.exec_module(gates)
    result = gates.validate_bootstrap_complete(report_path.read_text(encoding="utf-8"))
    if not result.ok:
        print(f"Refused: bootstrap-complete failed: {result.reason}")
        return 1
    print(f"Bootstrap complete: {report_path}")
    return 0
