"""Command-line entrypoint for the canonical dead-artifact CI gate."""

from pathlib import Path
import argparse
import sys

from cli.artifact_audit import audit_artifacts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true")
    modes.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    findings = audit_artifacts(root, write_report=args.write_report,
                               check_report=args.check)
    if findings:
        for item in findings:
            print(f"[{item['severity'].upper()}] {item['check']}: {item['path']} — {item['message']}")
        return 1
    print("Artifact audit: clean")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
