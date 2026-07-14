"""maika doctor - diagnostics for Maika runtime dependencies."""

import json
from pathlib import Path
from typing import List, Optional

from cli.mcp.doctor import apply_fix, build_doctor_status, write_report


def run_doctor_mcp(
    target_dir: str,
    fix: bool = False,
    assume_yes: bool = False,
    home: Optional[Path] = None,
) -> None:
    target = Path(target_dir).resolve()
    home_path = home or Path.home()
    maika_root = Path(__file__).resolve().parent.parent.parent
    try:
        status = build_doctor_status(target, home_path, maika_root=maika_root)
    except ValueError as exc:
        print(f"\n  {exc}")
        print("  Run `maika init` first, or point --target at an Maika project.")
        return
    report = write_report(target, status)
    print(f"\n  MCP doctor report: {report}")
    print(f"  native: {status.native_state} | bridge: {status.bridge_state}")
    if status.memory_daemon != "not-selected":
        print(f"  agent-memory daemon: {status.memory_daemon} ({status.memory_daemon_url})")
    if fix:
        fixed = apply_fix(target, home_path, assume_yes)
        if fixed is None:
            print("  no safe automatic fix available")
        else:
            print(f"  fixed config: {fixed}")
            status = build_doctor_status(target, home_path, maika_root=maika_root)
            report = write_report(target, status)
            print(f"  refreshed report: {report}")


# ─── setup doctor ───────────────────────────────────────────────────────────
# Whole-adapter installation health. Each check reuses an existing subsystem
# (W1 assets, W3 canonical config, W4 detection/workers, MCP doctor) and emits a
# machine-readable finding: {id, severity, ok, evidence, remediation}.

def _finding(fid: str, severity: str, ok: bool, evidence: str, remediation: str = "") -> dict:
    return {"id": fid, "severity": severity, "ok": ok,
            "evidence": evidence, "remediation": remediation}


def _check_canonical_core(target: Path) -> dict:
    from cli.config import project as project_cfg

    core_dir = target / project_cfg.CORE_ROOT
    config_file = project_cfg.config_path(target)
    cfg = project_cfg.load(target)
    version_ok = cfg.get("version") == 1
    ok = core_dir.is_dir() and config_file.is_file() and version_ok
    evidence = (
        f"core={project_cfg.CORE_ROOT}:{'present' if core_dir.is_dir() else 'missing'}, "
        f"project.yaml:{'present' if config_file.is_file() else 'missing'}, version={cfg.get('version')}"
    )
    return _finding("canonical-core", "error", ok, evidence,
                    "" if ok else f"run `maika init --target {target}`")


def _check_managed_entrypoint(target: Path) -> dict:
    from cli.config import project as project_cfg
    from cli.platforms import get_platform
    from cli.scaffold import MANAGED_BLOCK_BEGIN, MANAGED_BLOCK_END

    primary = project_cfg.load(target)["platforms"]["primary"]
    if primary is None:
        return _finding("managed-entrypoint", "error", False,
                        "no configured primary platform",
                        f"run `maika init --target {target}`")
    entry = get_platform(primary).config_entry_point
    path = target / entry
    if not path.is_file():
        return _finding("managed-entrypoint", "error", False,
                        f"{entry} missing for primary {primary}",
                        f"run `maika init --target {target}`")
    text = path.read_text(encoding="utf-8")
    begin, end = text.count(MANAGED_BLOCK_BEGIN), text.count(MANAGED_BLOCK_END)
    ok = begin == 1 and end == 1
    return _finding("managed-entrypoint", "error", ok,
                    f"{entry}: begin={begin} end={end}",
                    "" if ok else f"run `maika update --target {target}` to restore the Maika block")


def _check_native_hook(target: Path) -> dict:
    from cli.config import platforms as platforms_cfg
    from cli.config import project as project_cfg
    from cli.install.json_merge import ManagedJsonError, contains_maika_json_entry

    enabled = project_cfg.load(target)["platforms"]["enabled"]
    checked, broken = [], []
    for key in enabled:
        hook_config = platforms_cfg.adapter_descriptor(key)["hook_config"]
        if hook_config is None:
            continue
        path = target / hook_config
        present = False
        if path.is_file():
            try:
                present = contains_maika_json_entry(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError, ManagedJsonError):
                present = False
        checked.append(f"{key}:{hook_config}:{'wired' if present else 'missing'}")
        if not present:
            broken.append(key)
    if not checked:
        return _finding("native-hook", "info", True, "no enabled adapters with native hooks")
    ok = not broken
    return _finding("native-hook", "error", ok, ", ".join(checked),
                    "" if ok else f"run `maika platform enable {broken[0]}` to reinstall its hook")


def _check_host_binaries(target: Path) -> dict:
    from cli.config import project as project_cfg
    from cli.platforms.probe import probe_platform

    enabled = project_cfg.load(target)["platforms"]["enabled"]
    lines, missing = [], []
    for key in enabled:
        result = probe_platform(key, target, verify=False)
        binary = result.binary
        if binary.name is None:
            lines.append(f"{key}: no worker binary")
            continue
        if binary.found:
            version = binary.version.splitlines()[0] if binary.version else "?"
            lines.append(f"{key}: {binary.name} @ {binary.path} ({version})")
        else:
            lines.append(f"{key}: {binary.name} not on PATH")
            missing.append(key)
    if not lines:
        return _finding("host-binaries", "info", True, "no enabled adapters")
    ok = not missing
    return _finding("host-binaries", "warning", ok, "; ".join(lines),
                    "" if ok else "install the host CLI, then run maika platform verify")


def _check_worker_strategy(target: Path) -> dict:
    from cli.config import project as project_cfg
    from cli.runtime.worker_resolver import WorkerResolutionError, resolve_worker_profile

    primary = project_cfg.load(target)["platforms"]["primary"]
    if primary is None:
        return _finding("worker-strategy", "info", True, "no primary platform")
    try:
        profile = resolve_worker_profile(target, primary)
    except WorkerResolutionError as exc:
        return _finding("worker-strategy", "error", False, str(exc),
                        f"run maika platform enable {primary} or maika repair --all-safe")
    from cli.runtime.executor import strategy_executes
    if strategy_executes(profile.strategy):
        return _finding("worker-strategy", "info", True,
                        f"primary {primary}: {profile.strategy} ({profile.reason})")
    # Advisory (never a non-zero exit) but not ok: no dispatchable worker yet.
    return _finding("worker-strategy", "warning", False,
                    f"primary {primary}: {profile.strategy} — not dispatchable ({profile.reason})",
                    f"run maika platform verify {primary}")


def _check_asset_bundle(maika_root: Optional[str]) -> dict:
    from cli.assets import asset_root, validate_asset_bundle

    try:
        root = asset_root(maika_root)
    except FileNotFoundError as exc:
        return _finding("asset-bundle", "error", False, str(exc),
                        "reinstall the maika package or pass a complete --source")
    missing = validate_asset_bundle(root)
    ok = not missing
    return _finding("asset-bundle", "error", ok,
                    f"root={root}" + ("" if ok else f"; missing: {', '.join(missing)}"),
                    "" if ok else "reinstall the maika package with complete assets")


def _check_legacy_roots(target: Path) -> dict:
    legacy = [rel for rel in (".agents/resolved-config.yaml", ".claude/resolved-config.yaml")
              if (target / rel).is_file()]
    ok = not legacy
    return _finding("legacy-root-conflict", "warning", ok,
                    "none" if ok else f"legacy resolved-config: {', '.join(legacy)}",
                    "" if ok else "run `maika migrate` to consolidate onto the canonical .maika core")


def _check_deprecated_config(target: Path) -> dict:
    from cli.scaffold import load_resolved_config
    resolved = load_resolved_config(target) or {}
    deprecated = [key for key in ("hook_python",) if key in resolved]
    return _finding(
        "deprecated-config", "warning", not deprecated,
        "none" if not deprecated else f"deprecated keys: {', '.join(deprecated)}",
        "run `maika repair --finding deprecated-config`" if deprecated else "",
    )


def _check_mcp_health(target: Path, home: Path, maika_root: Optional[str]) -> dict:
    from cli.scaffold import load_resolved_config

    resolved = load_resolved_config(target) or {}
    selected = list(resolved.get("mcps") or [])
    if not selected:
        return _finding("mcp-health", "info", True, "no MCPs selected")
    try:
        status = build_doctor_status(target, home, maika_root=Path(maika_root) if maika_root else None)
    except ValueError as exc:
        return _finding("mcp-health", "warning", False, str(exc),
                        "run `maika doctor mcp --target <target> --fix`")
    ok = status.native_state == "configured"
    return _finding("mcp-health", "warning", ok,
                    f"native={status.native_state}, matched={status.matched}, missing={status.missing}",
                    "" if ok else "run `maika doctor mcp --target <target> --fix`")


def build_setup_findings(target, home: Optional[Path] = None,
                         maika_root: Optional[str] = None) -> List[dict]:
    target = Path(target).resolve()
    home = home or Path.home()
    return [
        _check_canonical_core(target),
        _check_managed_entrypoint(target),
        _check_native_hook(target),
        _check_host_binaries(target),
        _check_worker_strategy(target),
        _check_asset_bundle(maika_root),
        _check_legacy_roots(target),
        _check_deprecated_config(target),
        _check_mcp_health(target, home, maika_root),
    ]


_LABEL = {"error": "FAIL", "warning": "WARN", "info": "INFO"}


def run_doctor_setup(target_dir: str, as_json: bool = False,
                     maika_root: Optional[str] = None) -> int:
    target = Path(target_dir).resolve()
    findings = build_setup_findings(target, maika_root=maika_root)
    if as_json:
        print(json.dumps({"target": str(target), "findings": findings},
                         ensure_ascii=False, indent=2))
    else:
        print(f"\n  maika doctor setup — {target}\n")
        for f in findings:
            label = "OK" if f["ok"] else _LABEL[f["severity"]]
            print(f"  [{label:4s}] {f['id']}: {f['evidence']}")
            if not f["ok"] and f["remediation"]:
                print(f"          ↳ {f['remediation']}")
        print()
    return 1 if any(f["severity"] == "error" and not f["ok"] for f in findings) else 0


def run_doctor_platform(target_dir: str, platform_key: Optional[str] = None,
                        verify: bool = False) -> int:
    from cli.config import project as project_cfg
    from cli.platforms.probe import probe_and_persist

    target = Path(target_dir).resolve()
    keys = [platform_key] if platform_key else project_cfg.load(target)["platforms"]["enabled"]
    if not keys:
        print("No enabled platforms.")
        return 0
    failed = False
    for key in keys:
        try:
            result = probe_and_persist(target, key, verify=verify)
        except (OSError, ValueError) as exc:
            print(f"{key}: unavailable ({exc})")
            failed = True
            continue
        print(f"{key}: tier {result.support_tier}; binary={'detected' if result.binary.found else 'missing'}; "
              f"hook={result.verification['hook']}; worker={result.verification['worker']}")
        if verify and result.support_tier < 2:
            failed = True
    return 1 if failed else 0


def run_doctor_artifacts(target_dir: str = ".") -> int:
    from cli.artifact_audit import audit_artifacts

    target = Path(target_dir).resolve()
    if (target / ".maika/config/artifact-registry.yaml").is_file() \
            and (target / "cli/plugin-manifest.yaml").is_file():
        root = target
    else:
        from cli.assets import asset_root
        root = asset_root()
    findings = audit_artifacts(root)
    if not findings:
        print("Artifact hygiene: clean (no Critical/High findings)")
        return 0
    for item in findings:
        print(f"[{item['severity'].upper()}] {item['check']}: {item['path']} — {item['message']}")
    return 1
