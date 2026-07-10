"""Human-controlled skill candidate promotion/rejection commands."""

from pathlib import Path
import subprocess

import yaml

from cli.knowledge_control import promote_skill_candidate, reject_skill_candidate
from cli.scaffold import load_resolved_config


def _run_checks(target: Path, checks: list) -> tuple[bool, list[dict]]:
    results = []
    for raw in checks or []:
        item = raw if isinstance(raw, dict) else {"command": str(raw)}
        command = item.get("command")
        if not command:
            results.append({"command": "", "exit_code": 2, "passed": False, "output": "missing command"})
            continue
        proc = subprocess.run(command, cwd=target, shell=True, capture_output=True, text=True)
        output = ((proc.stdout or "") + (proc.stderr or "")).strip()
        expected = str(item.get("expected") or "")
        passed = proc.returncode == 0 and (not expected or expected in output)
        results.append({"command": command, "exit_code": proc.returncode,
                        "passed": passed, "output": output[-2000:]})
    return bool(results) and all(item["passed"] for item in results), results


def run_skill(action: str, target_dir: str, candidate_id: str,
              review_path: str, promotion_path: str | None = None) -> int:
    target = Path(target_dir).resolve()
    resolved = load_resolved_config(target)
    if resolved is None:
        print("Refused: Maika is not initialized")
        return 2
    framework_root = resolved.get("framework_root", ".maika")
    candidate = target / framework_root / "knowledge" / "skill-evolution" / "candidates" / f"{candidate_id}.yaml"
    if not candidate.exists():
        print(f"Refused: candidate not found: {candidate_id}")
        return 1
    review = yaml.safe_load(Path(review_path).read_text(encoding="utf-8")) or {}
    try:
        if action == "promote":
            if not promotion_path:
                print("Refused: promote requires --promotion")
                return 2
            promotion = yaml.safe_load(Path(promotion_path).read_text(encoding="utf-8")) or {}
            candidate_doc = yaml.safe_load(candidate.read_text(encoding="utf-8")) or {}
            validation = candidate_doc.get("validation") or {}
            tests_passed, test_results = _run_checks(target, validation.get("required_tests") or [])
            dogfood_items = validation.get("dogfood_scenarios") or []
            dogfood_passed, dogfood_results = _run_checks(target, dogfood_items)
            if candidate_doc.get("classification") == "editorial" and not dogfood_items:
                dogfood_passed = True
            promotion.update(tests_passed=tests_passed, dogfood_passed=dogfood_passed,
                             test_results=test_results, dogfood_results=dogfood_results)
            result = promote_skill_candidate(target, framework_root, candidate, review, promotion)
        else:
            result = reject_skill_candidate(target, framework_root, candidate, review)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"Refused: {exc}")
        return 1
    print(f"Skill candidate {candidate_id}: {result['status']}")
    return 0
