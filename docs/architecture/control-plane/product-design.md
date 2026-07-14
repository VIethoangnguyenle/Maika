# Maika Control Plane — Product & UX Design

## 0. Executive direction

**Product thesis**

Maika Control Plane is not a generic AI workflow builder.

It is a **local-first operations control plane for governed coding-agent workflows**:

- observe what is running;
- understand why each action happened;
- verify which evidence supports a decision;
- inspect agent/provider/tool activity;
- handle blockers and approvals safely;
- resume or retry durable work;
- audit the entire change lifecycle.

The core object is not a chat message. It is a **Change Run**.

The core visual is not a prompt box. It is a **workflow timeline + evidence graph + control surface**.

---

# 1. Open-source benchmark

## 1.1 Langfuse

### What it does well

- Trace tree and nested span navigation.
- Timeline with duration and latency.
- Right-side inspector for input, output, metadata and scores.
- Session-level debugging.
- Observability is the default mental model, not an afterthought.

### What Maika should borrow

- Nested trace tree.
- Persistent inspector.
- Search/filter by provider, tool, status and duration.
- Direct relationship between event and raw/normalized evidence.
- Compact timing indicators.

### What Maika should not copy

- LLM-call-centric information architecture.
- Cost/token metrics as the primary dashboard.
- Generic trace names without change/workflow context.

Maika should place **workflow state, governance and evidence** above model call details.

---

## 1.2 Temporal UI

### What it does well

- Durable workflow execution as a first-class object.
- Complete execution history.
- Clear pending/running/completed/failed states.
- Safe operational actions.
- Workflow metadata is separated from event history.

### What Maika should borrow

- Durable event history.
- State transition timeline.
- Explicit retry/resume/cancel semantics.
- Parent-child workflow relationships.
- “Current state” and “how we got here” shown together.

### What Maika should not copy

- Infrastructure-oriented terminology without developer context.
- A long raw event list as the only detailed view.

Maika must add **why the agent made the decision**, the evidence used and the files affected.

---

## 1.3 Hatchet

### What it does well

- Real-time monitoring of background tasks and AI agents.
- Durable task workflows.
- DAGs, retries and pause/resume.
- Worker-level assignment and capacity.
- Operational monitoring and logging.

### What Maika should borrow

- Run status list.
- Worker health and heartbeat.
- Retry history.
- Queue and dependency visibility.
- Clear distinction between task definition and task execution.

### What Maika should not copy

- High-throughput queue management as the product center.
- Generic worker infrastructure controls in the MVP.

Maika workers are engineering roles, not anonymous queue consumers.

---

## 1.4 Kestra

### What it does well

- “Everything as code and from the UI.”
- Visual workflow plus declarative source.
- Built-in code editor.
- Inputs, outputs and artifacts are visible.
- Strong distinction between definition and execution.

### What Maika should borrow

- Source-of-truth artifacts remain files.
- UI is a projection over declarative workflow state.
- Side-by-side visual and source/artifact view.
- Artifacts are first-class outputs.

### What Maika should not copy

- Editing Maika workflow policy directly on a visual canvas in the first version.
- Turning the UI into a generic YAML workflow authoring product.

The Control Plane should inspect Maika workflow policy, not casually mutate it.

---

## 1.5 Dify

### What it does well

- Friendly node canvas.
- Clear node types and ports.
- Node-level debugging.
- Last-run input/output inspection.
- Easy visual branch comprehension.

### What Maika should borrow

- Visual clarity of nodes and edges.
- Node inspector.
- Minimap and focus controls.
- Node-level status and elapsed time.

### What Maika should not copy

- Drag-and-drop workflow authoring as the primary experience.
- Oversized cards containing too much runtime content.
- Treating workflow execution and workflow design as the same mode.

Maika canvas is **read-first**. Editing workflow policy belongs in source and reviewed PRs.

---

## 1.6 OpenHands Agent Canvas

### What it does well

- A developer control center for coding agents.
- Supports local, remote and cloud agent backends.
- Multiple backend environments in one frontend.
- Agent conversations and automations share one operational surface.
- Self-hosted and always-on mental model.

### What Maika should borrow

- Multi-host/backend switcher.
- A clear “where is this agent running?” indicator.
- Project/repository selection.
- Always-on local control plane.
- Automation/run history separated from active conversations.

### What Maika should improve beyond it

- Stronger workflow governance view.
- Evidence and gate visualization.
- Provider trigger explanations.
- File-write boundaries and security audit.

---

## 1.7 Awesome DESIGN.md

### What it contributes

A plain-text design constitution that agents can read and use consistently.

For Maika:

- `AGENTS.md` defines how the project is built.
- `DESIGN.md` defines how the Control Plane looks and behaves.
- Component contracts and executable tokens prevent visual drift.
- Screenshot regression closes the feedback loop.

---

# 2. Unique product positioning

## 2.1 The product metaphor

**A flight deck for coding agents.**

The user should feel:

- I can see every active mission.
- I know which phase it is in.
- I know which worker is responsible.
- I know what external provider it is using.
- I know why that provider was called.
- I know which evidence supports the current decision.
- I can intervene safely without opening raw YAML.
- I can audit the full history later.

## 2.2 The three product layers

### Observe

- runs;
- workers;
- state transitions;
- provider calls;
- gates;
- artifacts;
- duration;
- failures.

### Understand

- why a capability was required;
- why a provider was selected;
- what evidence was produced;
- what source verification supports a claim;
- why a gate passed or failed;
- why a task is blocked.

### Control

- approve an external workflow;
- re-probe a provider;
- retry a worker;
- resume a blocked role;
- cancel a run;
- acknowledge a risk;
- open the exact artifact or diff.

---

# 3. Primary users

## 3.1 Solo developer

Needs:

- understand what the agent is doing;
- detect stuck or wasteful behavior;
- resume after context loss;
- inspect evidence without reading all artifacts;
- control local and remote agents.

## 3.2 Tech lead / reviewer

Needs:

- audit a change;
- inspect task DAG;
- verify tests, evidence and gates;
- find unresolved risk;
- compare agent behavior;
- approve sensitive actions.

## 3.3 Framework maintainer

Needs:

- identify recurring workflow failures;
- inspect capability/provider routing;
- verify cross-host behavior;
- improve rules and gates;
- compare Maika versions.

---

# 4. Information architecture

```text
Maika Control Plane
├── Overview
├── Runs
│   ├── Active
│   ├── Blocked
│   ├── Completed
│   └── Run Detail
├── Agents
│   ├── Active Workers
│   ├── Hosts / Backends
│   └── Worker History
├── Providers
│   ├── Understand-Anything
│   ├── Codebase Memory
│   ├── DB Access
│   ├── Agent Memory
│   └── Invocation History
├── Evidence
│   ├── Claims
│   ├── Source Verifications
│   ├── Database Contexts
│   └── Freshness
├── Gates & Blockers
├── Artifacts
├── Analytics
└── Settings
```

## MVP navigation

Keep the MVP compact:

```text
Overview
Runs
Agents
Providers
Blocked
Settings
```

Evidence, artifacts and gates are tabs inside Run Detail first. They can become global pages later.

---

# 5. Application shell

## 5.1 Desktop layout

```text
┌──────────────────┬────────────────────────────────────────────┬───────────────────────┐
│ Global nav       │ Main workspace                             │ Context inspector     │
│ 224px            │ flexible                                   │ 360–440px             │
│                  │                                            │                       │
│ Workspace        │ Run header                                 │ Selected event/node   │
│ Overview         │ View switcher                              │ Evidence               │
│ Runs             │ Timeline / DAG / Trace / Artifacts         │ Inputs/outputs         │
│ Agents           │                                            │ Gate details           │
│ Providers        │ Main content                               │ Safe actions          │
│ Blocked          │                                            │                       │
└──────────────────┴────────────────────────────────────────────┴───────────────────────┘
```

## 5.2 Responsive behavior

### >= 1440px

- Three persistent columns.
- Inspector width 400px.
- Dense timeline and DAG.

### 1024–1439px

- Sidebar collapsible.
- Inspector opens as a sheet.
- Main area remains full-featured.

### 768–1023px

- Icon rail.
- One main view.
- Inspector uses full-height drawer.
- DAG defaults to fit-to-screen.

### < 768px

- Read-only monitoring focus.
- Timeline as the default view.
- Controls are grouped in a bottom sheet.
- Complex DAG editing is not supported.

---

# 6. Page designs

# 6.1 Overview

## Purpose

Answer in ten seconds:

- What is running?
- What is blocked?
- Which providers are unhealthy?
- What needs my attention?
- What changed recently?

## Layout

```text
┌──────────────────────────────────────────────────────────────────────────────┐
│ Good morning, Hoang                              Workspace: Maika / master-v2 │
│ 3 active runs · 1 blocked · all critical providers available               │
├──────────────────────────────────────────────────────────────────────────────┤
│ Attention queue                                                             │
│ [BLOCKED] C-142 Needs /understand refresh     [Review] C-139 2 findings     │
├───────────────────────────────┬──────────────────────────────────────────────┤
│ Active runs                   │ Live activity                               │
│ C-142 Grounding  08:42        │ UA trace_call_chain completed  1.8s         │
│ C-141 Executing  03:15        │ reviewer-02 started                         │
│ C-140 Verifying  01:02        │ gate source-verification passed             │
├───────────────────────────────┼──────────────────────────────────────────────┤
│ Provider health               │ Recent outcomes                             │
│ UA        Ready · fresh       │ 7 completed · 1 changes-required            │
│ CBM       Ready               │ Median run: 18m                              │
│ DB Access Configured          │ Retry rate: 6%                               │
└───────────────────────────────┴──────────────────────────────────────────────┘
```

## Rules

- No wall of KPI cards.
- Attention queue always appears above analytics.
- Active runs show phase, duration, last observable action and owner worker.
- Provider status must distinguish:
  - configured;
  - ready;
  - degraded;
  - unavailable;
  - stale.

---

# 6.2 Runs list

## Columns

- status;
- change ID;
- title;
- repository/branch;
- current phase;
- active worker;
- blockers;
- elapsed;
- last activity;
- host;
- risk badges.

## Filters

- active / blocked / completed;
- repository;
- phase;
- provider;
- risk;
- host;
- date;
- user.

## Saved views

- Needs attention.
- Persistence-sensitive.
- Provider degraded.
- Cross-host qualification.
- Long running.
- Failed gates.

---

# 6.3 Run Detail — the core screen

## Header

```text
C-142 · Provider convergence M2
master-v2 · standard · persistence risk: no
RUNNING · Grounding · 08:42

[Pause] [Cancel] [Open workspace] [...]
```

## Primary tabs

```text
Timeline
Workflow
Trace
Evidence
Artifacts
Diff
```

### Timeline — default

A human-readable chronological view.

```text
10:22:01  Run started
10:22:02  intent-analysis completed
10:22:04  Grounding worker dispatched
10:22:08  UA get_graph_metadata → READY
10:22:10  UA query_nodes → 3 anchors
10:22:12  UA trace_call_chain → 14 nodes
10:22:13  Current source verified 5 claims
10:22:14  Gate trace-evidence passed
```

Events are grouped by phase and worker.

### Workflow

Read-only React Flow canvas:

```text
INTAKE → EXPLORING → RECONCILING → BRAINSTORMING → SPEC → PLAN → EXECUTING → REVIEW → VERIFY
```

Each node shows:

- phase name;
- status;
- duration;
- worker;
- gate count;
- blocker indicator.

Clicking a node updates the inspector.

### Trace

Nested tree:

```text
Grounding worker
├── capability.compile
├── provider.ua.get_graph_metadata
├── provider.ua.query_nodes
├── provider.ua.trace_call_chain
├── source.verify
└── gate.trace-evidence
```

This is where Langfuse-like patterns are strongest.

### Evidence

Claims on the left, sources on the right.

```text
Claim: Approve flow begins in InitApproveHandler
Confidence: high
Verified by:
- UA node n-183
- source file hash sha256:...
- source range 42–87
```

### Artifacts

File tree grouped by phase:

```text
CHANGE.yaml
INTENT.md
exploration/
  QUERY_PLAN.yaml
  TRACE_EVIDENCE.yaml
  DATABASE_CONTEXT.yaml
reviews/
verification/
```

Preview Markdown/YAML/JSON with semantic rendering before raw text.

### Diff

- files changed;
- risk badges;
- owning task;
- worker;
- review status;
- test coverage;
- source verification links.

---

# 6.4 Agent Monitor

## Worker card

```text
grounding-01
Grounding Explorer
RUNNING · 01:42

Current observable action:
Calling understand-anything / trace_call_chain

Allowed writes:
exploration/**

Provider lane:
UA structured trace

Heartbeat:
4 seconds ago
```

## Worker detail tabs

- Activity.
- Assigned context.
- Allowed scope.
- Provider calls.
- Artifacts.
- Retries.
- Logs.

## Important privacy rule

Do not show private chain-of-thought.

Show only:

- assigned objective;
- observable action category;
- tool calls;
- files accessed;
- artifacts produced;
- structured summaries;
- gate feedback.

Never label a panel “Thoughts.”

Use:

```text
Current objective
Current action
Decision summary
Evidence used
```

---

# 6.5 Provider Center

## Provider cards

### Understand-Anything

- connection state;
- project;
- graph commit;
- repository HEAD;
- freshness;
- health;
- last call;
- latency;
- calls this run.

### Codebase Memory

- index state;
- last call;
- trigger for every call;
- unnecessary-call warnings.

### DB Access

- client key;
- selected source;
- database/environment;
- active lane;
- used tools;
- denied tool attempts;
- last probe.

## Invocation table

Columns:

- time;
- run;
- role;
- provider;
- tool;
- trigger;
- duration;
- status;
- evidence produced.

A provider call without a trigger should be visually flagged.

---

# 6.6 Blocker Center

## Blocker card

```text
BLOCKED · C-142
Reason: Relevant UA graph is stale
Role: grounding
Required action: Run /understand
Affected claims: Q-CODE-001, Q-CODE-003
Created: 3 minutes ago

[Approve workflow] [Open request] [Cancel run]
```

## Safe action flow

1. User clicks action.
2. Confirmation dialog explains effect.
3. Control API validates current state.
4. Action is recorded in audit log.
5. UI shows pending execution.
6. New evidence must be received.
7. Resume becomes available.

No button should execute arbitrary shell text.

---

# 6.7 Gate Inspector

## Gate result

```text
trace-evidence · PASSED
Duration: 82ms

Checks
✓ Required structured trace capability satisfied
✓ UA invocation evidence exists
✓ Source verification present
✓ No hidden truncation
✓ CBM was not required
```

Failure:

```text
conditional-provider-use · FAILED

Codebase Memory was called without an activated trigger.

Invocation:
semantic_search
Role:
grounding

Expected trigger:
unresolved_anchor | graph_gap | hidden_consumer_risk | ...
```

This page turns governance into a comprehensible product feature.

---

# 7. Signature Maika interactions

## 7.1 Why was this called?

Every provider/tool event has a “Why?” chip.

Example:

```text
Codebase Memory · semantic_search
Why: unresolved_anchor
Question: “Where is approval assembled?”
```

This is a distinctive Maika feature.

## 7.2 Evidence chain

Click a claim to highlight:

```text
claim
→ provider observation
→ source verification
→ gate
→ consuming plan/task
```

## 7.3 State replay

A scrubber replays the run:

```text
00:00 Intake
00:12 Grounding
02:44 Reconciliation
...
```

The workflow graph and event timeline update to the selected moment.

## 7.4 Trust mode

Toggle:

```text
Normal
Trust / Governance
```

Trust mode overlays:

- stale evidence;
- inferred claims;
- missing hashes;
- out-of-lane tool calls;
- unresolved conflicts;
- user approvals.

## 7.5 Command palette

Examples:

```text
Open active run
Show blocked runs
Re-probe UA
Open latest failed gate
Compare host behavior
Open artifact
```

---

# 8. Visual language

## 8.1 Design blend

```text
40% Vercel precision
25% Linear density and interaction
15% Claude warmth
15% Sentry operational clarity
5% VoltAgent agent identity
```

## 8.2 Product character

- Calm.
- Precise.
- Technical.
- Trustworthy.
- Warm enough for long sessions.
- Never “sci-fi dashboard.”
- Never decorative AI neon.

## 8.3 Light-first

Default is light mode:

- warm neutral background;
- white/sand surfaces;
- subtle borders;
- dark graphite text;
- terracotta primary accent.

Dark mode:

- charcoal, not pure black;
- restrained accent;
- status colors adjusted for contrast.

## 8.4 Typography

- UI: Geist Sans or Inter.
- Technical: Geist Mono or IBM Plex Mono.
- No serif in operational screens.
- Numeric values use tabular figures.
- Body size 13–14px for dense desktop UI.

## 8.5 Density

Three density modes:

```text
Comfortable
Compact
Auto
```

Default desktop: compact but readable.

## 8.6 Status semantics

| State | Color family | Icon |
|---|---|---|
| Running | blue | activity/spinner |
| Waiting | amber | clock |
| Blocked | orange | octagon/pause |
| Failed | red | x-circle |
| Passed | green | check-circle |
| Stale | violet | history |
| Degraded | yellow-brown | warning |
| Cancelled | gray | slash |

Color is never the only signal.

---

# 9. Component system

## Core components

- `RunStatusBadge`
- `PhaseStepper`
- `WorkflowNode`
- `TaskDAGNode`
- `WorkerCard`
- `ProviderBadge`
- `ProviderInvocationRow`
- `CapabilityChip`
- `TriggerChip`
- `EvidenceClaim`
- `SourceVerification`
- `GateResultCard`
- `BlockerBanner`
- `ArtifactTree`
- `ArtifactPreview`
- `DiffRiskBadge`
- `StateTimeline`
- `AuditEvent`
- `SafeActionDialog`
- `FreshnessIndicator`

## Component anatomy rule

Every operational component must answer at least three:

```text
What?
Status?
When?
Who?
Why?
Evidence?
Next action?
```

---

# 10. Technical architecture

## 10.1 Recommended stack

```text
Frontend:
React + TypeScript + Vite
TanStack Router
TanStack Query
TanStack Table
Zustand
React Flow
shadcn/ui + Radix UI
Tailwind CSS

Backend:
Python FastAPI
SSE for live events
SQLite for local projection/event index

Canonical state:
Maika artifacts and append-only runtime events
```

Why Vite instead of Next.js for the initial version:

- local-first dashboard;
- no SEO;
- easier static packaging;
- clearer separation from Python runtime;
- can later be wrapped as desktop or served remotely.

## 10.2 Event pipeline

```text
Maika runtime
→ append-only events
→ local event index / projection
→ Control Plane API
→ SSE
→ React UI
```

## 10.3 Canonical vs projection

Canonical:

- Maika artifacts;
- state files;
- provider invocation records;
- gate outputs;
- audit records.

Projection:

- dashboard lists;
- status summaries;
- analytics;
- search index.

The UI must never become the sole source of truth.

---

# 11. Data model

## Workspace

```yaml
id:
name:
root_path:
repository:
branch:
host_connections:
```

## ChangeRun

```yaml
id:
workspace_id:
title:
class:
status:
current_state:
started_at:
updated_at:
risk_signals:
```

## WorkerExecution

```yaml
id:
run_id:
role:
host:
status:
started_at:
heartbeat_at:
completed_at:
attempt:
allowed_scope:
```

## ProviderInvocation

```yaml
id:
run_id:
worker_id:
provider_id:
tool:
trigger:
reason:
request_hash:
response_hash:
status:
duration_ms:
```

## GateResult

```yaml
id:
run_id:
gate:
status:
checks:
artifact_refs:
timestamp:
```

## Artifact

```yaml
path:
kind:
phase:
hash:
producer:
validation_status:
```

## HumanRequest

```yaml
id:
run_id:
type:
status:
reason:
remediation:
resume_role:
```

## AuditAction

```yaml
actor:
action:
target:
before:
after:
timestamp:
```

---

# 12. Event vocabulary

```text
workspace.connected
run.created
run.state_changed
run.blocked
run.resumed
run.cancelled
worker.dispatched
worker.started
worker.heartbeat
worker.completed
worker.failed
provider.call_requested
provider.call_started
provider.call_completed
provider.call_failed
artifact.read
artifact.written
artifact.validated
gate.started
gate.passed
gate.failed
human.requested
human.approved
human.declined
control.retry_requested
control.cancel_requested
```

---

# 13. Security and governance

## Default mode

Read-only.

## Control permissions

- retry worker;
- resume run;
- approve registered external workflow;
- cancel run;
- re-probe provider.

## Sensitive controls

- DB data probe;
- DB write/script;
- scope expansion;
- destructive operation.

Require:

- explicit user intent;
- environment confirmation;
- audit record;
- provider safety confirmation where applicable.

## Never expose

- raw credentials;
- connection strings;
- confirmation tokens;
- private chain-of-thought;
- unrestricted shell input.

---

# 14. MVP roadmap

## Phase 0 — Telemetry contract

Deliver:

- event schema;
- trace IDs;
- worker heartbeat;
- provider invocation events;
- gate events;
- state transition events;
- SQLite projection.

No UI before this contract is stable.

## Phase 1 — Read-only Control Plane

Pages:

- Overview.
- Runs.
- Run Detail Timeline.
- Workflow view.
- Agents.
- Providers.
- Blocked.
- Artifact inspector.

## Phase 2 — Trust and evidence

- Evidence chain.
- Gate inspector.
- Freshness.
- Source verification.
- DB context.
- Trust mode.

## Phase 3 — Safe controls

- Retry.
- Resume.
- Cancel.
- Approve external workflow.
- Re-probe provider.
- Audit trail.

## Phase 4 — Multi-host

- Claude/Codex/Antigravity hosts.
- Local/remote backend status.
- Host switcher.
- Cross-host qualification comparison.

## Phase 5 — Analytics

- failure clusters;
- gate failure trends;
- provider latency/reliability;
- unnecessary CBM calls;
- run duration;
- retry rate;
- stale evidence patterns.

---

# 15. MVP acceptance criteria

1. User sees all active runs.
2. User identifies the current phase in under five seconds.
3. User identifies the active worker and last observable action.
4. User sees every provider call and its reason.
5. User can inspect gate failures without opening YAML.
6. User can inspect source verification for a claim.
7. User can see why a run is blocked.
8. User can open the required remediation.
9. User can resume only after valid new evidence.
10. No private reasoning is displayed.
11. UI works with local and remote agent hosts.
12. Refresh updates reach the browser through SSE.
13. All controls create audit events.
14. The UI remains useful in read-only mode.
15. Canonical artifacts remain authoritative.

---

# 16. Anti-patterns

Do not:

- make chat the homepage;
- use a giant workflow canvas for everything;
- hide execution history behind logs;
- show raw JSON as the default inspector;
- use “AI thinking” animations;
- present chain-of-thought;
- show color without labels/icons;
- create twenty KPI cards;
- make write/script actions one-click;
- infer provider health from configuration;
- mix workflow definition and execution editing;
- use glassmorphism, heavy gradients or neon;
- build UI before event semantics are stable.

---

# 17. Recommended first prototype

Build one high-fidelity vertical slice:

```text
Overview
→ open active run
→ Timeline
→ select UA invocation
→ inspect trigger and evidence
→ open failed gate
→ see blocker
→ approve /understand request
→ new evidence arrives
→ run resumes
```

This prototype tests the full product thesis better than building ten shallow pages.
