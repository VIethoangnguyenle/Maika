# ASCII Diagram Guidance for Explore and Spec Extract

## Context

Maika's `/task` pipeline already separates requirement extraction, exploration, OpenSpec proposal, and implementation. The current guidance leaves a gap: `openspec-explore` mentions ASCII diagrams, but `spec-extract` and the knowledge templates do not require diagrams to be captured when a document or exploration contains a business flow, state transition, integration, callback, job, or data path.

The result is that an agent can understand a flow in chat, yet downstream artifacts can still lose the sequence, boundary, and branching structure that made the requirement clear.

This design adopts the useful part of upstream OpenSpec's explore stance from `Fission-AI/openspec`: explore is a thinking stance, not a rigid workflow; it should read code when relevant, compare options, visualize freely, and hand off to propose when the picture is clear. Maika adds a stronger artifact discipline: important ASCII diagrams should be captured in the active knowledge layer so later phases can reuse them.

Relevant upstream references:

- https://github.com/Fission-AI/openspec
- https://github.com/Fission-AI/openspec/blob/main/docs/explore.md
- https://github.com/Fission-AI/openspec/blob/main/src/core/templates/workflows/explore.ts

## Goals

- Make ASCII diagrams a required part of `spec-extract` output whenever the source material contains flow, state, integration, callback, job, or data-path structure.
- Preserve upstream OpenSpec's flexible explore stance while making Maika's `/opsx:explore` guidance more explicit about visual reasoning.
- Add template anchors so `REQUIREMENT.md` and `EXPLORE_CONTEXT.md` naturally retain diagrams instead of leaving them only in chat.
- Keep diagrams plain-text ASCII so they survive Markdown, code review, terminal output, and long-context handoff without renderer dependencies.

## Non-Goals

- Do not introduce Mermaid, DOT, image generation, or a diagram renderer.
- Do not require diagrams for trivial tasks with no meaningful sequence, state, branch, or integration boundary.
- Do not change runtime code or command execution behavior.
- Do not replace acceptance criteria, source links, field mapping, or architecture notes with diagrams.

## Architecture

The change lives entirely in skill guidance and knowledge templates.

```text
user input / source document
  -> spec-extract or openspec-explore
  -> detect flow / state / data path / integration boundary
  -> draw ASCII diagram
  -> capture in REQUIREMENT.md or EXPLORE_CONTEXT.md
  -> openspec-propose reads clearer phase-1 context
```

Files expected to change during implementation:

- `.maika/skills/openspec-explore/SKILL.md`
- `.maika/skills/openspec-explore/references/explore-patterns.md`
- `.maika/skills/spec-extract/SKILL.md`
- `.maika/skills/spec-extract/references/quy-trinh-chi-tiet.md`
- `.maika/skills/spec-extract/references/output-schema.md`
- `.maika/knowledge/templates/REQUIREMENT.tpl.md`
- `.maika/knowledge/templates/EXPLORE_CONTEXT.tpl.md`

## Behavior

### Diagram Trigger

The agent should create an ASCII diagram when the explored or extracted material includes at least one of these structures:

- A main flow with multiple ordered steps.
- Alternate flow, error branch, retry, fallback, or cancellation path.
- State transition or lifecycle.
- Integration boundary between internal and external systems.
- Callback, webhook, scheduled job, queue, event, or async handoff.
- Data path across modules, services, tables, DTOs, or third-party fields.
- Option branching where a visual comparison is clearer than prose alone.

The agent should not create a diagram merely to decorate a simple bullet list.

### `spec-extract`

`spec-extract` should add a required `#### ASCII Flow / State Diagram` block when the source document contains any trigger above.

Suggested placement:

```text
### Yêu cầu nghiệp vụ trích từ tài liệu
  -> Bối cảnh & mục tiêu
  -> Actor & Use Case
  -> ASCII Flow / State Diagram
  -> Luồng chính
  -> Luồng lỗi / ngoại lệ
  -> Quy tắc nghiệp vụ
```

If the document has multiple flows, `spec-extract` should draw one overview diagram first. Smaller diagrams are only needed for branches that are complex enough to be ambiguous without a picture.

If evidence is incomplete, the diagram must label the uncertain part as `unknown`, `assumption`, or `needs BA/PO confirmation`.

### `openspec-explore`

`openspec-explore` should borrow the upstream stance:

- Explore is a thinking stance, not a fixed workflow.
- The agent may read files, search code, investigate the codebase, compare options, and visualize freely.
- The agent must not implement code.
- The agent should offer to transition into proposal creation when the thinking crystallizes.

Maika-specific addition:

- When an explore conversation uses a diagram to clarify an important insight, the agent should offer to capture that insight into `EXPLORE_CONTEXT.md`, an OpenSpec artifact, or the appropriate active knowledge file.
- If the explore starts from a new task with uncertain flow, the agent should sketch a compact map:

```text
user problem
  -> current behavior / unknown
  -> code or document probe
  -> options
  -> recommended next step
```

### Templates

`REQUIREMENT.tpl.md` should include a dedicated diagram anchor near As-is/To-be and the extracted-document section.

`EXPLORE_CONTEXT.tpl.md` should replace the soft placeholder "Sơ đồ hoặc danh sách module" with explicit guidance: when a flow, state, or data path exists, include an ASCII diagram. A plain list remains acceptable only when there is no meaningful sequence or boundary.

## Error Handling and Guardrails

- Diagrams must distinguish evidence from inference.
- Diagrams must not invent actors, systems, fields, or states that are absent from the source or code evidence.
- Diagrams must include external boundary labels when integrations are involved.
- Diagrams must remain concise. If a diagram becomes too dense, split it into overview plus one branch-specific diagram.
- Explore mode remains non-implementation. Updating OpenSpec or knowledge artifacts is allowed only as capture of thinking, not application code changes.

## Acceptance Criteria

- When `spec-extract` processes a document containing a process flow, `REQUIREMENT.md` includes `#### ASCII Flow / State Diagram`.
- When `spec-extract` processes a document containing a state lifecycle, the diagram shows states and transitions.
- When `spec-extract` processes integration, callback, job, event, or data-path material, the diagram labels internal and external boundaries.
- When evidence is incomplete, diagrams mark uncertain nodes or edges explicitly instead of presenting assumptions as facts.
- `openspec-explore` guidance clearly preserves upstream OpenSpec's "stance, not workflow" behavior and "do not implement" guardrail.
- `openspec-explore` guidance tells the agent to use ASCII diagrams when they clarify code, architecture, data flow, state, or option branching.
- `openspec-explore` guidance tells the agent to offer capture into Maika/OpenSpec artifacts once an important diagram-backed insight crystallizes.
- `REQUIREMENT.tpl.md` and `EXPLORE_CONTEXT.tpl.md` provide diagram anchors that downstream `openspec-propose` can read without relying on chat history.

## Verification Plan

- Run the skill/template lint tests if available.
- Run a repository search for the new section title to confirm guidance and templates are aligned.
- Manually review the changed Markdown to ensure it has no placeholder text, no renderer dependency, and no contradiction with existing phase gates.
