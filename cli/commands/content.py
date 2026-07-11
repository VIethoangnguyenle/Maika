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


def run_content(action: str, target_dir: str = ".") -> int:
    target = Path(target_dir).resolve()
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
    print(f"Unknown content action: {action}")
    return 2
