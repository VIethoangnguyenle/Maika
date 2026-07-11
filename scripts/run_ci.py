"""Run Maika's repository test columns.

This is intentionally small: GitHub Actions and local development should share
the same list of test surfaces instead of duplicating paths in YAML.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


TEST_GROUPS = [
    {"name": "cli", "paths": ["cli/tests"]},
    {"name": "gate-check", "paths": [".maika/tools/gate-check/tests"]},
    {"name": "microloop-orchestrator", "paths": [".maika/tools/microloop-orchestrator/tests"]},
    {"name": "write-gate", "paths": [".maika/hooks/write-gate/tests"]},
    {"name": "knowledge-index", "paths": [".maika/tools/knowledge-index/tests"]},
    {"name": "rule-projector", "paths": [".maika/tools/rule-projector/tests"]},
]


def _existing_paths(repo: Path, paths: list[str]) -> list[str]:
    return [path for path in paths if (repo / path).exists()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Maika CI test columns.")
    parser.add_argument(
        "--group",
        choices=[group["name"] for group in TEST_GROUPS],
        action="append",
        help="Run only the named group. May be passed more than once.",
    )
    args = parser.parse_args(argv)

    repo = Path(__file__).resolve().parents[1]
    audit = subprocess.run(
        [sys.executable, "scripts/audit_artifacts.py", "--check"], cwd=repo, check=False,
    )
    if audit.returncode != 0:
        return audit.returncode
    selected = [group for group in TEST_GROUPS if not args.group or group["name"] in args.group]
    for group in selected:
        paths = _existing_paths(repo, group["paths"])
        if not paths:
            print(f"[skip] {group['name']}: no paths found")
            continue
        print(f"[run] {group['name']}: {' '.join(paths)}")
        code = subprocess.run(
            [sys.executable, "-m", "pytest", *paths, "-q"],
            cwd=repo,
            check=False,
        ).returncode
        if code != 0:
            return code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
