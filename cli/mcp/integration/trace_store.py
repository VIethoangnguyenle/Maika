"""TRACE_EVIDENCE.yaml store — mechanical sections only (plan §7).

`maika provider` writes the machine-produced sections (provider_observations,
support_calls, source_verifications, graph) through this store. The worker
authors anchors/traversals/impact/limitations/confidence/complete in the same
file, binding every claim to a recorded response hash; the trace-evidence gate
validates that linkage.
"""

from __future__ import annotations

from pathlib import Path

import yaml

TRACE_EVIDENCE_REL = "exploration/TRACE_EVIDENCE.yaml"

_SKELETON = {
    "version": 1,
    "authority_policy_version": 1,
    "change_id": None,
    "provider_observations": [],
    "graph": {},
    "anchors": [],
    "traversals": [],
    "impact": [],
    "support_calls": [],
    "source_verifications": [],
    "conflicts": [],
    "refresh_boundaries": [],
    "limitations": [],
    "confidence": None,
    "complete": False,
}


def load_trace_evidence(workspace: Path, change_id: str) -> tuple[Path, dict]:
    path = Path(workspace) / TRACE_EVIDENCE_REL
    if path.exists():
        doc = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    else:
        doc = {}
    merged = {**_SKELETON, **doc}
    merged["change_id"] = merged.get("change_id") or change_id
    return path, merged


def save_trace_evidence(path: Path, doc: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(doc, sort_keys=False, allow_unicode=True), encoding="utf-8"
    )


def add_observation(workspace: Path, change_id: str, observation: dict) -> Path:
    path, doc = load_trace_evidence(workspace, change_id)
    observation = dict(observation)
    graph = observation.pop("graph", None)
    doc["provider_observations"] = list(doc.get("provider_observations") or []) + [observation]
    if graph:
        # Bind the graph claim to the probe observation that produced it —
        # a hand-written graph block cannot survive the trace-evidence gate
        # (mutation #4: fresh-graph claim without response hash).
        doc["graph"] = {
            **(doc.get("graph") or {}),
            **graph,
            "observation": observation["response_hash"],
        }
    save_trace_evidence(path, doc)
    return path


def add_support_call(workspace: Path, change_id: str, support_call: dict) -> Path:
    path, doc = load_trace_evidence(workspace, change_id)
    doc["support_calls"] = list(doc.get("support_calls") or []) + [support_call]
    save_trace_evidence(path, doc)
    return path


def add_source_verification(workspace: Path, change_id: str, entry: dict) -> Path:
    path, doc = load_trace_evidence(workspace, change_id)
    doc["source_verifications"] = list(doc.get("source_verifications") or []) + [entry]
    save_trace_evidence(path, doc)
    return path
