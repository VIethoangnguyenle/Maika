#!/usr/bin/env python3
"""Convert skill/workflow files to Jinja2 templates.

Replaces hardcoded tool references with {{ tools.X }} Jinja2 variables
and adds conditional blocks for platform capabilities.

Usage:
    python cli/tools/templatize.py --scan          # Show what would change
    python cli/tools/templatize.py --apply          # Apply conversions
    python cli/tools/templatize.py --apply --file X # Apply to single file
"""

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# ─── Abstract operation → Jinja2 variable mapping ───
# Two patterns to replace:
#   1. SP3-style: code_exploration.search_code → {{ tools.search_code }}
#   2. Hardcoded: semantic_query → {{ tools.semantic_search }}

ABSTRACT_TO_JINJA = {
    # SP3 abstract refs → Jinja2
    "code_exploration.check_availability": "{{ tools.code_status }}",
    "code_exploration.search_code": "{{ tools.search_code }}",
    "code_exploration.get_source": "{{ tools.read_file }}",
    "code_exploration.get_detail": "{{ tools.get_symbol }}",
    "code_exploration.get_dependencies": "{{ tools.get_dependencies }}",
    "code_exploration.trace_flow": "{{ tools.trace_flow }}",
    "code_exploration.find_blast_radius": "{{ tools.find_blast_radius }}",
}

HARDCODED_UA = {
    # UA Knowledge Graph hardcoded refs → Jinja2
    "query_nodes": "{{ tools.search_code }}",
    "get_node_detail": "{{ tools.get_symbol }}",
    "get_node_source": "{{ tools.read_file }}",
    "get_relationships": "{{ tools.get_dependencies }}",
    "find_impact": "{{ tools.find_blast_radius }}",
    "trace_call_chain": "{{ tools.trace_flow }}",
    "get_graph_stats": "{{ tools.graph_stats }}",
    "get_domain_detail": "{{ tools.get_symbol }}",
}

HARDCODED_CONFLUENCE = {
    "confluence_search": "{{ tools.search_docs }}",
    "confluence_get_page": "{{ tools.get_page }}",
    "confluence_list_spaces": "{{ tools.list_spaces }}",
}

# Files/patterns to SKIP (don't templatize)
SKIP_PATTERNS = [
    "plugin-manifest.yaml",
    "templatize.py",
    "registry.yaml",
    "capabilities.yaml",
    "providers/",
]


def find_replaceable_files(root: Path) -> List[Path]:
    """Find .md files in skills/, workflows/, procedures/ that have tool refs."""
    targets = []
    search_dirs = [
        root / ".maika" / "skills",
        root / ".maika" / "workflows",
        root / ".maika" / "procedures",
    ]

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for md_file in search_dir.rglob("*.md"):
            # Skip already-templatized files
            if md_file.suffix == ".j2":
                continue
            if any(skip in str(md_file) for skip in SKIP_PATTERNS):
                continue
            targets.append(md_file)

    return sorted(targets)


def scan_file(filepath: Path) -> List[Tuple[int, str, str, str]]:
    """Scan a file for tool references. Returns [(line_num, original, replacement, category)]."""
    findings = []
    content = filepath.read_text(encoding="utf-8")
    lines = content.split("\n")

    all_mappings = [
        (ABSTRACT_TO_JINJA, "SP3 abstract"),
        (HARDCODED_UA, "UA hardcoded"),
        (HARDCODED_CONFLUENCE, "Confluence hardcoded"),
    ]

    for line_num, line in enumerate(lines, 1):
        for mapping, category in all_mappings:
            for old, new in mapping.items():
                # Match the tool name as a word (not part of a larger word)
                # But be careful with code_exploration.X patterns (contain dots)
                if "." in old:
                    # Exact match for dotted names
                    pattern = re.escape(old)
                else:
                    # Word boundary for simple names
                    pattern = r'(?<![a-zA-Z_])' + re.escape(old) + r'(?![a-zA-Z_])'

                if re.search(pattern, line):
                    findings.append((line_num, old, new, category))

    return findings


def apply_replacements(filepath: Path) -> Tuple[str, int]:
    """Apply all tool reference replacements to a file. Returns (new_content, count)."""
    content = filepath.read_text(encoding="utf-8")
    count = 0

    all_mappings = [
        ABSTRACT_TO_JINJA,
        HARDCODED_UA,
        HARDCODED_CONFLUENCE,
    ]

    for mapping in all_mappings:
        for old, new in mapping.items():
            if "." in old:
                pattern = re.escape(old)
            else:
                pattern = r'(?<![a-zA-Z_])' + re.escape(old) + r'(?![a-zA-Z_])'

            matches = re.findall(pattern, content)
            if matches:
                content = re.sub(pattern, new, content)
                count += len(matches)

    return content, count


def main():
    parser = argparse.ArgumentParser(description="Convert tool refs to Jinja2 templates")
    parser.add_argument("--scan", action="store_true", help="Scan only, show findings")
    parser.add_argument("--apply", action="store_true", help="Apply replacements")
    parser.add_argument("--file", type=str, help="Process single file only")
    parser.add_argument("--root", type=str, default=".", help="Project root")
    args = parser.parse_args()

    if not args.scan and not args.apply:
        parser.print_help()
        return

    root = Path(args.root).resolve()

    if args.file:
        files = [Path(args.file).resolve()]
    else:
        files = find_replaceable_files(root)

    if args.scan:
        total_findings = 0
        for filepath in files:
            findings = scan_file(filepath)
            if findings:
                rel = filepath.relative_to(root)
                print(f"\n📄 {rel} ({len(findings)} refs)")
                for line_num, old, new, category in findings:
                    print(f"  L{line_num:3d}: {old:45s} → {new:30s} [{category}]")
                total_findings += len(findings)

        print(f"\n{'═' * 60}")
        print(f"Total: {total_findings} tool references in {len([f for f in files if scan_file(f)])} files")
        print(f"Run with --apply to convert.")

    if args.apply:
        total_changes = 0
        changed_files = 0
        for filepath in files:
            new_content, count = apply_replacements(filepath)
            if count > 0:
                filepath.write_text(new_content, encoding="utf-8")
                rel = filepath.relative_to(root)
                print(f"  ✅ {rel} ({count} replacements)")
                total_changes += count
                changed_files += 1

        print(f"\n{'═' * 60}")
        print(f"Applied: {total_changes} replacements in {changed_files} files")


if __name__ == "__main__":
    main()
