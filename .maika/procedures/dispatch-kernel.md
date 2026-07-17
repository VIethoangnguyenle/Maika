# Shared Dispatch Kernel

`KERNEL_ID: maika-knowledge-control-v1`

Đây là canonical prompt fragment. Mọi isolated worker prompt phải inject nguyên khối
này trước role-specific instruction; runtime không được duy trì bản sao khác.

```text
You are an isolated Maika worker.

- Read the assigned role artifacts and Knowledge Capsule.
- Do not rely on parent conversation history.
- Treat current source as authority for exact code facts.
- Do not invent architecture, behavior, schema or conventions.
- Use the required capability when its provider is healthy.
- Do not silently degrade; record provider failure, fallback and confidence.
- If source conflicts with evidence, emit EVIDENCE_UPDATE_REQUEST.
- Record evidence IDs and knowledge IDs actually used.
- Respect role and write boundaries.
- Do not invoke side-effecting external workflows unless EXTERNAL_WORKFLOWS grants
  them. For request-only workflows, emit EXTERNAL_WORKFLOW_REQUEST.yaml and stop.
- Return structured result only.
```

Runtime consumer: `tools/microloop-orchestrator/vnext_dispatch.py:build_prompt`.
Gate `dispatch-kernel` so sánh mọi dispatch path với `KERNEL_ID` này.

## Handoff Contract

Mỗi handoff truyền: role, change/task ID, state, assigned artifact paths, immutable
Knowledge Capsule path/hash, evidence IDs, source anchors, allowed writes, required
verification, missing context, degradation và expected structured output.

Worker phải record knowledge/evidence IDs thực sự dùng; conflict với source phải emit
`EVIDENCE_UPDATE_REQUEST`; result thiếu contract hoặc vượt write scope bị reject.

## External Workflow Request

Default dispatch contract:

```yaml
external_workflows:
  allowed: []
  request_only: [understand, understand-domain]
```

Worker không tự chạy request-only workflow. Khi cần, ghi request cạnh result:

```yaml
request_type: external_workflow
workflow: understand
reason:
required_for: [Q-...]
observed_freshness:
affected_claims: []
resume_role:
```

Parent validate workflow qua `config/external-workflows.yaml`, block với remediation,
refresh provider state chỉ sau execution thật, rồi mới redispatch. Unknown workflow bị
reject; không được claim refresh nếu command chưa thực thi.
