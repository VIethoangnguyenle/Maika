"""Capability probes for gate-check (impure — shells out to knowledge-tool CLIs).

Kept OUT of gates.py so the validators stay deterministic/hermetic. The caller
(cli.py) runs the probe and passes the result into the pure validator, mirroring
the existing --index pattern. Fail-open: any probe error → empty list, so a
missing/broken probe never blocks (the validator treats empty as "nothing to
use → grep OK").
"""
import json
import os
import subprocess


def _parse_list_projects(stdout: str):
    """Extract [{"name","root_path"}] from `codebase-memory-mcp cli list_projects`
    output. cbm prints a log line before the JSON, so scan lines from the end for
    the first that parses as an object."""
    for line in reversed(stdout.splitlines()):
        s = line.strip()
        if not s.startswith("{"):
            continue
        try:
            data = json.loads(s)
        except json.JSONDecodeError:
            continue
        return [
            {"name": p.get("name", ""), "root_path": p.get("root_path", "")}
            for p in data.get("projects", [])
            if p.get("root_path")
        ]
    return []


def cbm_indexed_projects(timeout: int = 8):
    """Projects indexed in codebase-memory-mcp. [] on any failure (fail-open)."""
    try:
        proc = subprocess.run(
            ["codebase-memory-mcp", "cli", "list_projects", "{}"],
            capture_output=True, text=True, timeout=timeout,
        )
    except (OSError, subprocess.SubprocessError):
        return []
    return _parse_list_projects(proc.stdout)


def ua_indexed_projects(candidate_roots):
    """Roots that have a UA knowledge-graph.json (UA can serve them)."""
    out = []
    for root in candidate_roots:
        if root and os.path.isfile(
            os.path.join(root, ".understand-anything", "knowledge-graph.json")
        ):
            out.append({"name": os.path.basename(root.rstrip("/")), "root_path": root})
    return out


def indexed_projects(repo_root: str | None = None, timeout: int = 8):
    """Union of projects any knowledge tool can serve (cbm ∪ UA-graph-present)."""
    projs = cbm_indexed_projects(timeout=timeout)
    roots = {p["root_path"] for p in projs}
    if repo_root:
        roots.add(repo_root)
    known = {p["root_path"] for p in projs}
    ua = [p for p in ua_indexed_projects(roots) if p["root_path"] not in known]
    return projs + ua
