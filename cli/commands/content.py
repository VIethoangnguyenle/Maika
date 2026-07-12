"""maika content — agent-facing content validation commands."""

from __future__ import annotations

from pathlib import Path

from cli.agent_content.authority import load_registry, validate_registry
from cli.agent_content.router import load_router, validate_router
from cli.scaffold import load_resolved_config


def _framework_dir(target: Path) -> Path:
    resolved = load_resolved_config(target)
    if resolved is not None:
        return target / resolved.get("framework_root", ".maika")
    # Framework checkout (not an initialized target): validate the source tree.
    return target / ".maika"


def run_content(action: str, target_dir: str = ".", apply: bool = False) -> int:
    target = Path(target_dir).resolve()
    if action == "scan-legacy":
        from cli.agent_content.legacy import scan_legacy_references
        framework = _framework_dir(target)
        findings = scan_legacy_references(framework)
        if findings:
            for item in findings:
                print(f"legacy-reference: {item['file']}:{item['line']} → {item['token']}")
            return 1
        print("legacy-clean: no deprecated active-memory references in agent-facing content")
        return 0
    if action == "migrate-legacy":
        from cli.agent_content.legacy import apply_legacy_migration, plan_legacy_migration
        framework = _framework_dir(target)
        moves = plan_legacy_migration(framework)
        if not moves:
            print("migrate-legacy: nothing to migrate")
            return 0
        for move in moves:
            print(f"{'apply' if apply else 'dry-run'}: {move['source']} -> {move['target']}"
                  f" ({move['note']})")
        if apply:
            apply_legacy_migration(moves)
            print(f"migrated {len(moves)} legacy artifacts")
        else:
            print("re-run with --apply to perform the moves")
        return 0
    if action == "validate-authority":
        framework = _framework_dir(target)
        try:
            doc = load_registry(framework)
        except FileNotFoundError as exc:
            print(f"Refused: no artifact authority registry at {exc}")
            return 2
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        errors = validate_registry(doc)
        if errors:
            for error in errors:
                print(f"authority: {error}")
            return 1
        print(f"authority registry valid: {len(doc.get('authorities') or {})} decisions, "
              f"{len(doc.get('deprecated') or [])} deprecated paths")
        return 0
    if action == "behavior-static":
        from cli.behavior.harness import run_suite
        framework = _framework_dir(target)
        try:
            report = run_suite(framework)
        except FileNotFoundError as exc:
            print(f"Refused: missing behavior surface: {exc}")
            return 2
        for fixture in report["fixtures"]:
            print(f"{fixture['verdict']}: {fixture['fixture_id']} — {fixture['title']}")
            for violation in fixture["violations"]:
                print(f"  ! {violation}")
        print(f"behavior-static verdict: {report['verdict']}")
        return 0 if report["verdict"] == "PASS" else 1
    if action == "validate-skills":
        framework = _framework_dir(target)
        from cli.agent_content.skill_contract import validate_skill_contracts
        try:
            errors = validate_skill_contracts(framework)
        except FileNotFoundError as exc:
            print(f"Refused: missing contract surface: {exc}")
            return 2
        if errors:
            for error in errors:
                print(f"skill-contract: {error}")
            return 1
        print("skill contracts valid")
        return 0
    if action == "validate-router":
        framework = _framework_dir(target)
        try:
            doc = load_router(framework)
        except FileNotFoundError as exc:
            print(f"Refused: no workflow router at {exc}")
            return 2
        except ValueError as exc:
            print(f"Refused: {exc}")
            return 1
        errors = validate_router(doc, framework)
        if errors:
            for error in errors:
                print(f"router: {error}")
            return 1
        print(f"workflow router valid: {len(doc.get('actions') or {})} actions")
        return 0
    if action == "validate-interactions":
        from cli.agent_content.interaction_router import (
            load_interaction_router, validate_interaction_router,
        )
        framework = _framework_dir(target)
        try:
            doc = load_interaction_router(framework)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Refused: {exc}")
            return 2 if isinstance(exc, FileNotFoundError) else 1
        errors = validate_interaction_router(doc)
        if errors:
            for error in errors:
                print(f"interaction-router: {error}")
            return 1
        print(f"interaction router valid: {len(doc.get('routes') or {})} routes")
        return 0
    if action == "validate-external-workflows":
        from cli.agent_content.external_workflows import (
            load_external_workflows, validate_external_workflows,
        )
        framework = _framework_dir(target)
        try:
            doc = load_external_workflows(framework)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Refused: {exc}")
            return 2 if isinstance(exc, FileNotFoundError) else 1
        errors = validate_external_workflows(doc)
        if errors:
            for error in errors:
                print(f"external-workflow: {error}")
            return 1
        print(f"external workflows valid: {len(doc.get('workflows') or {})} workflows")
        return 0
    if action == "validate-generated-reports":
        from cli.agent_content.generated_reports import validate_report_files
        framework = _framework_dir(target)
        try:
            errors = validate_report_files(framework)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Refused: {exc}")
            return 2 if isinstance(exc, FileNotFoundError) else 1
        if errors:
            for error in errors:
                print(f"generated-report: {error}")
            return 1
        print("generated report schema and documents valid")
        return 0
    if action == "validate-provider-capabilities":
        from cli.agent_content.provider_capabilities import (
            load_capability_registry, load_provider_capabilities,
            validate_provider_capabilities,
        )
        framework = _framework_dir(target)
        try:
            mapping = load_provider_capabilities(framework)
            registry = load_capability_registry(framework)
        except (FileNotFoundError, ValueError) as exc:
            print(f"Refused: {exc}")
            return 2 if isinstance(exc, FileNotFoundError) else 1
        errors = validate_provider_capabilities(mapping, registry)
        if errors:
            for error in errors:
                print(f"provider-capability: {error}")
            return 1
        print(f"provider capabilities valid: {len(mapping.get('providers') or {})} providers")
        return 0
    print(f"Unknown content action: {action}")
    return 2
