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
    from cli.scaffold import _is_maika_json

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
                present = _is_maika_json(json.loads(path.read_text(encoding="utf-8")))
            except (json.JSONDecodeError, OSError):
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
    from cli.platforms import get_platform
    from cli.platforms.detection import detect_platform

    enabled = project_cfg.load(target)["platforms"]["enabled"]
    lines, missing = [], []
    for key in enabled:
        result = detect_platform(get_platform(key))
        binary = result["binary"]
        if binary["name"] is None:
            lines.append(f"{key}: no worker binary")
            continue
        if binary["found"]:
            version = result["version"]["raw"].splitlines()[0] if result["version"]["raw"] else "?"
            lines.append(f"{key}: {binary['name']} @ {binary['path']} ({version})")
        else:
            lines.append(f"{key}: {binary['name']} not on PATH")
            missing.append(key)
    if not lines:
        return _finding("host-binaries", "info", True, "no enabled adapters")
    ok = not missing
    return _finding("host-binaries", "warning", ok, "; ".join(lines),
                    "" if ok else "install the host CLI, or workers fall back to inline")


def _check_worker_strategy(target: Path) -> dict:
    from cli.config import project as project_cfg
    from cli.platforms import get_platform
    from cli.platforms.detection import detect_platform
    from cli.workers import select_worker_strategy

    primary = project_cfg.load(target)["platforms"]["primary"]
    if primary is None:
        return _finding("worker-strategy", "info", True, "no primary platform")
    platform = get_platform(primary)
    profile = select_worker_strategy(platform, detect_platform(platform))
    return _finding("worker-strategy", "info", True,
                    f"primary {primary}: {profile['strategy']} ({profile['reason']})")


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
