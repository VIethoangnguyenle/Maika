"""Bootstrap artifacts: environment report + agent acknowledgment (plan §14).

Two artifacts with different owners:

- ``runtime/BOOTSTRAP_ENV_REPORT.yaml`` — environment FACTS produced by
  ``maika bootstrap``: files present (``rules_present``, never "loaded"),
  repository commit, provider probes, active changes, degradation.
- ``runtime/AGENT_BOOTSTRAP_ACK.yaml`` — the agent's acknowledgment produced by
  ``maika bootstrap --ack`` AFTER it has read kernel/router/skill-index: content
  hashes pin exactly what was acknowledged; a later hash mismatch forces reload.
"""

from __future__ import annotations

import getpass
import hashlib
import importlib.util
import subprocess
from datetime import datetime, timezone
from pathlib import Path

import yaml

from cli.mcp.doctor import build_doctor_status, write_report
from cli.platforms import get_platform
from cli.scaffold import generate_knowledge_index, load_resolved_config

ENV_REPORT_REL = "runtime/BOOTSTRAP_ENV_REPORT.yaml"
ACK_REL = "runtime/AGENT_BOOTSTRAP_ACK.yaml"
_ACK_SURFACES = {
    "kernel_hash": "agent/KERNEL.md",
    "router_hash": "config/workflow-router.yaml",
    "skill_index_hash": "skills/skill-index.yaml",
    # Mutation #11 (harness plan §21): provider/capability contracts changed
    # after acknowledgment must block dispatch until re-ack.
    "provider_registry_hash": "config/provider-registry.yaml",
    "capability_registry_hash": "profiles/capability-registry.yaml",
}


def _sha256(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def content_hashes(framework: Path) -> dict[str, str]:
    """Hashes of the always-on agent surfaces an acknowledgment pins."""
    hashes = {}
    for key, rel in _ACK_SURFACES.items():
        path = Path(framework) / rel
        hashes[key] = _sha256(path) if path.exists() else "missing"
    return hashes


def _active_changes(framework: Path) -> list[str]:
    changes = Path(framework) / "changes"
    if not changes.exists():
        return []
    return sorted(path.parent.name for path in changes.glob("*/STATE.yaml"))


def _load_gates(framework: Path):
    gate_path = Path(framework) / "tools" / "gate-check" / "gates.py"
    spec = importlib.util.spec_from_file_location("maika_bootstrap_gate", gate_path)
    gates = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gates)
    return gates


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
        elif provider_id == "serena":
            healthy = status.health_state == "ready" and provider_id in status.matched
            probe_status = "healthy" if healthy else "degraded"
            evidence = (
                f"all_enabled_platforms:{status.health_state}; "
                f"native_config:{status.native_state}; bridge:{status.bridge_state}"
            )
        else:
            healthy = False  # config discovery is not a native MCP tool probe
            probe_status = "configured-unprobed" if provider_id in status.matched else "unavailable"
            evidence = f"native_config:{status.native_state}; bridge:{status.bridge_state}"
        probes.append({"provider_id": provider_id, "status": probe_status, "evidence": evidence})
        if not healthy:
            degradation.append({"provider_id": provider_id, "status": probe_status,
                                "fallback": "current-source/read-only local evidence"})
    rules_dir = framework / "rules"
    rules_present = sorted(
        path.relative_to(rules_dir).as_posix()
        for path in rules_dir.rglob("*.md")
    ) if rules_dir.exists() else []
    active = _active_changes(framework)
    if not active:
        resume_state = "new"
    elif len(active) == 1:
        resume_state = "resume"
    else:
        resume_state = "ambiguous"  # >1 active: require explicit --id
    commit_probe = subprocess.run(["git", "rev-parse", "HEAD"], cwd=target,
                                  capture_output=True, text=True, check=False)
    repository_commit = commit_probe.stdout.strip() if commit_probe.returncode == 0 else "unavailable"
    report = {
        "version": 2, "completed": True,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "repository_commit": repository_commit,
        "entry_point": get_platform(resolved.get("platform", "generic")).config_entry_point,
        "rules_present": rules_present,
        "knowledge_index": {"status": "loaded" if index_path.exists() else "missing",
                            "entries": len((index or {}).get("entries") or [])},
        "configured_providers": status.selected_mcps,
        "provider_probes": probes,
        "episodic_provider_health": status.memory_daemon,
        "active_changes": active,
        "resume_state": resume_state,
        "degradation": degradation,
    }
    report_path = framework / ENV_REPORT_REL
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(yaml.safe_dump(report, sort_keys=False, allow_unicode=True), encoding="utf-8")
    gates = _load_gates(framework)
    result = gates.validate_bootstrap_complete(report_path.read_text(encoding="utf-8"))
    if not result.ok:
        print(f"Refused: bootstrap-complete failed: {result.reason}")
        return 1
    print(f"Bootstrap environment report: {report_path}")
    print("Acknowledge after reading kernel/rules: maika bootstrap --ack")
    return 0


def run_bootstrap_ack(target_dir: str = ".", change_id: str | None = None) -> int:
    """Write the agent acknowledgment. Run AFTER reading kernel/router/index."""
    target = Path(target_dir).resolve()
    resolved = load_resolved_config(target)
    if resolved is None:
        print("Refused: Maika is not initialized")
        return 2
    framework = target / resolved.get("framework_root", ".maika")
    env_path = framework / ENV_REPORT_REL
    if not env_path.exists():
        print("Refused: run `maika bootstrap` first (no environment report)")
        return 1
    env = yaml.safe_load(env_path.read_text(encoding="utf-8")) or {}
    active = env.get("active_changes") or []
    if change_id is None and len(active) == 1:
        change_id = active[0]
    if len(active) > 1 and change_id is None:
        print(f"Refused: {len(active)} active changes {active} — pass --id explicitly")
        return 1
    if change_id is not None and change_id not in active:
        print(f"Refused: unknown active change {change_id} (active: {active or 'none'})")
        return 1
    current_state = None
    selected_route = []
    if change_id is not None:
        state_doc = yaml.safe_load(
            (framework / "changes" / change_id / "STATE.yaml").read_text(encoding="utf-8")
        ) or {}
        change_doc = yaml.safe_load(
            (framework / "changes" / change_id / "CHANGE.yaml").read_text(encoding="utf-8")
        ) or {}
        current_state = state_doc.get("state")
        klass = change_doc.get("effective_class") or change_doc.get("class")
        try:
            from cli.agent_content.router import load_router
            router = load_router(framework)
            for action, spec in (router.get("actions") or {}).items():
                if klass in (spec.get("classes") or []) and current_state in (spec.get("allowed_from") or []):
                    selected_route.append(action)
        except (FileNotFoundError, ValueError):
            selected_route = []
    ack = {
        "version": 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        **content_hashes(framework),
        "env_report_hash": _sha256(env_path),
        "selected_change": change_id,
        "current_state": current_state,
        "selected_route": sorted(selected_route),
        "rules_loaded": env.get("rules_present") or [],
        "unresolved_contradictions": [],
        "acknowledged_by": getpass.getuser(),
    }
    ack_path = framework / ACK_REL
    ack_path.parent.mkdir(parents=True, exist_ok=True)
    ack_path.write_text(yaml.safe_dump(ack, sort_keys=False, allow_unicode=True), encoding="utf-8")
    gates = _load_gates(framework)
    result = gates.validate_bootstrap_ack(ack_path.read_text(encoding="utf-8"))
    if not result.ok:
        print(f"Refused: bootstrap-ack failed: {result.reason}")
        return 1
    print(f"Agent bootstrap acknowledgment: {ack_path}")
    return 0


def verify_ack_freshness(framework: Path) -> tuple[bool, str]:
    """Hash-compare the acknowledgment against current surfaces (SSOT §14.4)."""
    framework = Path(framework)
    ack_path = framework / ACK_REL
    if not ack_path.exists():
        return False, "missing runtime/AGENT_BOOTSTRAP_ACK.yaml (run `maika bootstrap --ack`)"
    ack = yaml.safe_load(ack_path.read_text(encoding="utf-8")) or {}
    current = content_hashes(framework)
    for key, value in current.items():
        if ack.get(key) != value:
            return False, (f"stale acknowledgment: {key} changed since ack — "
                           "re-run `maika bootstrap && maika bootstrap --ack`")
    return True, ""
