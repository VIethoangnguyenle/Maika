# Maika Control Plane DESIGN.md

## 1. Product character

Maika Control Plane is a calm, precise and trustworthy operations interface for governed coding-agent workflows.

It should feel like:

- a professional engineering control room;
- a workflow debugger;
- a source-aware evidence explorer;
- a safe operational console.

It must not feel like:

- a chatbot;
- a no-code toy;
- a cyberpunk monitoring screen;
- an analytics landing page;
- a generic admin template.

---

## 2. Design principles

### 2.1 Operational truth first

The interface prioritizes:

1. status;
2. blocker;
3. current action;
4. evidence;
5. next safe action.

Decorative visuals are secondary.

### 2.2 Calm density

Display a large amount of technical information without visual noise.

Use:

- compact rows;
- subtle separators;
- consistent hierarchy;
- progressive disclosure;
- persistent context.

### 2.3 Explain every automation

Every provider or tool call should expose:

- capability;
- trigger;
- reason;
- result;
- evidence produced.

### 2.4 Read-first, control-second

All pages are useful without write permissions.

Control actions are explicit, guarded and audited.

### 2.5 Source-aware

Artifacts, file paths, hashes and diffs are first-class UI objects.

### 2.6 No hidden reasoning theater

Never display private chain-of-thought or fake “thinking” text.

Display observable actions and structured decision summaries.

---

## 3. Visual inspiration

Blend:

```text
Vercel:
precision, typography, application shell

Linear:
density, keyboard interaction, restrained chrome

Claude:
warm neutrals and human tone

Sentry:
operational hierarchy and error inspection

VoltAgent:
small amount of agent/terminal identity
```

Do not reproduce any product branding.

---

## 4. Color tokens

### Light

```css
--bg-canvas: #F6F4F0;
--bg-surface: #FFFFFF;
--bg-subtle: #F1EFEB;
--bg-elevated: #FFFFFF;

--text-primary: #20201E;
--text-secondary: #66645F;
--text-muted: #8C8982;
--text-inverse: #FFFFFF;

--border-subtle: #E4E0D9;
--border-strong: #CFC9BF;

--accent-primary: #C35F3E;
--accent-primary-hover: #AB4F33;
--accent-soft: #F5E5DF;

--status-running: #2E6DD8;
--status-success: #218A54;
--status-waiting: #B37816;
--status-blocked: #D46A1F;
--status-failed: #C53B3B;
--status-stale: #7656C8;
--status-degraded: #98702B;
--status-neutral: #77736C;
```

### Dark

```css
--bg-canvas: #171716;
--bg-surface: #1E1E1C;
--bg-subtle: #252522;
--bg-elevated: #292926;

--text-primary: #F1EFEA;
--text-secondary: #B9B5AD;
--text-muted: #88847D;

--border-subtle: #343430;
--border-strong: #4A4943;

--accent-primary: #E17A58;
--accent-primary-hover: #EC8D6D;
--accent-soft: #3A2721;
```

Status colors must meet WCAG contrast and include icon/text.

---

## 5. Typography

```text
Primary UI:
Geist Sans or Inter

Technical:
Geist Mono or IBM Plex Mono
```

Scale:

```text
Display: 28/34, 600
Page title: 22/28, 600
Section title: 15/22, 600
Body: 14/20, 400
Compact body: 13/18, 400
Label: 12/16, 500
Code: 12.5/18, 400
```

Use tabular numbers for:

- duration;
- token count;
- latency;
- timestamps;
- retries.

---

## 6. Spacing

4px base grid.

```text
4, 8, 12, 16, 20, 24, 32, 40, 48
```

Application spacing:

- page padding: 20–24px;
- panel padding: 16px;
- dense row: 36px;
- comfortable row: 44px;
- card gap: 12px.

---

## 7. Radius and shadow

```text
small controls: 6px
cards/panels: 8px
dialogs/sheets: 10px
pills: full
```

Shadows are rare.

Use borders and surface contrast before shadow.

---

## 8. Application shell

### Sidebar

- 224px expanded.
- 56px collapsed.
- Workspace switcher at top.
- Primary navigation in middle.
- Host and user controls at bottom.

### Main workspace

- flexible width;
- minimum useful width 640px;
- contains page header and view tabs.

### Inspector

- 400px default;
- resizable 340–520px;
- sheet on smaller screens;
- keeps selected object context.

---

## 9. Navigation

Primary items:

```text
Overview
Runs
Agents
Providers
Blocked
Settings
```

Navigation item anatomy:

- icon;
- label;
- optional count;
- active indicator;
- tooltip when collapsed.

Blocked count uses an orange badge.

---

## 10. Surfaces

Use three surface levels:

```text
Canvas:
page background

Surface:
tables, cards and panels

Elevated:
popover, dialog, selected inspector
```

Avoid nested cards deeper than two levels.

---

## 11. Status presentation

Every status includes:

- icon;
- text;
- color;
- optional timestamp/duration.

Never use a colored dot alone.

Running status may use a subtle 1.4s pulse on a 6px dot. No large looping animation.

---

## 12. Workflow canvas

### Node size

- width: 180–220px;
- height: content-driven, normally 76–96px.

### Node anatomy

```text
[status icon] PHASE
worker / role
duration · gate summary
```

### Node states

- pending: muted;
- active: blue border and subtle surface;
- passed: green check;
- blocked: orange left rail;
- failed: red left rail;
- skipped: dashed border.

### Edges

- neutral gray by default;
- active path blue;
- failed path red;
- conditional edge includes a compact label.

No animated flowing particles.

---

## 13. Timeline

Event row:

```text
timestamp | icon | title | metadata | duration/status
```

Group by phase.

Expandable detail displays:

- provider/tool;
- trigger;
- request/response hashes;
- artifact links;
- gate results.

Use virtualized lists for long runs.

---

## 14. Trace tree

Use indentation and connector lines.

Each span shows:

- operation;
- provider/tool;
- duration;
- status;
- evidence count.

Selected span opens in inspector.

Do not show raw payload until the user chooses “Raw.”

---

## 15. Tables

- sticky header;
- zebra striping only when necessary;
- row hover;
- keyboard selection;
- compact density;
- column visibility menu;
- saved filters.

Statuses appear near the left edge for fast scanning.

---

## 16. Inspector

Inspector header:

- selected object type;
- title;
- status;
- copy/open controls.

Tabs:

```text
Summary
Evidence
Input / Output
Metadata
Raw
```

Summary is always human-readable.

Raw is last.

---

## 17. Provider invocation

Invocation row must show:

```text
provider icon/name
tool
trigger chip
duration
status
timestamp
```

Trigger chip examples:

```text
unresolved_anchor
graph_gap
persistence_change
reviewer_counter_evidence
```

Missing trigger uses a red governance warning.

---

## 18. Evidence

Claim card:

```text
Claim
Confidence
Freshness
Evidence sources
Source verification
Consumers
```

Inference is visually distinct from verified fact.

Use:

```text
Verified
Corroborated
Inferred
Conflicted
Stale
```

---

## 19. Gates

Passed gate:

- compact green check;
- checks collapsed by default.

Failed gate:

- red/orange banner;
- failed check expanded;
- remediation visible;
- related artifacts linked.

Gate language should be specific and actionable.

Bad:

```text
Validation failed.
```

Good:

```text
Codebase Memory was called without an activated conditional trigger.
```

---

## 20. Blockers

Blocked runs use an orange status, not red.

Red is reserved for actual failure.

Blocker cards expose:

- reason;
- affected role;
- required action;
- affected claims/tasks;
- resume condition;
- safe controls.

---

## 21. Controls

Primary safe actions:

- retry;
- resume;
- approve registered workflow;
- re-probe;
- cancel.

Destructive or privileged actions:

- use explicit dialog;
- show environment and scope;
- require typed confirmation when appropriate;
- create an audit event.

No unrestricted terminal input.

---

## 22. Artifacts

Artifact tree uses type icons:

- Markdown;
- YAML;
- JSON;
- diff;
- report;
- source.

Preview modes:

```text
Semantic
Source
Diff
```

Semantic is default.

---

## 23. Logs

Logs are secondary to structured events.

Features:

- monospace;
- level filtering;
- worker/provider filters;
- search;
- wrap toggle;
- copy;
- download.

Avoid green-on-black terminal styling as the default.

---

## 24. Empty states

Empty states are concise and useful.

Example:

```text
No active runs

Start a Maika task from your CLI or connect another workspace.
```

Do not use large illustrations in operational pages.

---

## 25. Loading

Use skeletons for list/page loading.

Use inline progress for:

- provider call;
- worker start;
- gate execution.

Do not block the whole page unless changing workspace.

---

## 26. Motion

Duration:

```text
micro interaction: 120–160ms
panel/sheet: 180–220ms
canvas focus: 220–280ms
```

Use ease-out.

Respect `prefers-reduced-motion`.

---

## 27. Accessibility

- keyboard navigable;
- visible focus ring;
- status not color-only;
- minimum 4.5:1 text contrast;
- ARIA labels for status and graph controls;
- skip-to-content;
- inspector focus management;
- reduced-motion support.

---

## 28. Responsive

Mobile prioritizes:

1. attention queue;
2. active run status;
3. timeline;
4. blocker actions.

Workflow canvas is view-only and opens full screen.

Inspector becomes a bottom/full-screen sheet.

---

## 29. Component reuse rules

Before creating a new component:

1. inspect the component catalog;
2. reuse an existing primitive;
3. extend variants;
4. create a new component only for a recurring Maika domain concept.

Domain components must be documented.

---

## 30. Anti-patterns

Never:

- use glassmorphism;
- use decorative gradients across panels;
- use neon status colors;
- show private chain-of-thought;
- call observable events “thoughts”;
- make chat the default landing page;
- use giant cards for simple values;
- hide gate remediation;
- display raw JSON by default;
- combine definition editing and execution inspection;
- place write/script actions beside read actions without separation;
- animate every running item;
- copy Claude, Vercel, Linear or Sentry branding;
- use inconsistent status vocabulary.

---

## 31. Visual QA checklist

For every page:

- hierarchy is clear at 100% zoom;
- no horizontal overflow at 1280px;
- compact and comfortable density work;
- light and dark themes pass contrast;
- keyboard flow is complete;
- selected object remains clear;
- status is understandable without color;
- raw data is not the default;
- actions are safe and explicit;
- screenshot regression passes.
