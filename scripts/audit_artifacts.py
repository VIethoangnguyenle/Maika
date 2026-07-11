"""Command-line entrypoint for the canonical dead-artifact CI gate."""

from pathlib import Path
import sys

from cli.artifact_audit import audit_artifacts


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    findings = audit_artifacts(root)
    if findings:
        for item in findings:
            print(f"[{item['severity'].upper()}] {item['check']}: {item['path']} — {item['message']}")
        return 1
    print("Artifact audit: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
