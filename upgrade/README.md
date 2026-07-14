# Maika upgrade workspace

Thư mục này chứa assessment và kế hoạch hardening hệ sinh thái provider trên branch
`master-v2`. Implementation thuộc Maika đã được chuyển thành code, fixture và test;
thay đổi cho repository external chỉ là coordination plan, không được áp dụng từ repo
này.

## Tài liệu

- `MAIKA_FRAMEWORK_ECOSYSTEM_BRAINSTORM.md`: adversarial assessment và phân loại finding.
- `MAIKA_FRAMEWORK_ECOSYSTEM_UPGRADE_PLAN.md`: kế hoạch Maika M0–M5 và exit gates.
- `EXTERNAL_PROVIDER_CONTRACT_HARDENING_PLAN.md`: E0–E5 do từng provider upstream sở hữu.
- `answer/maika-framework-ecosystem-pilot-readiness.md`: readiness baseline sau triển khai.

## Kiểm tra implementation

```bash
pytest cli/tests .maika/tools/gate-check/tests \
  .maika/tools/microloop-orchestrator/tests .maika/hooks/write-gate/tests -q
python3 -m cli.maika content validate-provider-capabilities --target .
python3 -m cli.maika content validate-system-model --target .
git diff --check
```

Fixture provider nằm tại `cli/tests/fixtures/provider_contracts/`; mỗi payload có
sidecar provenance pin repository, audited revision và SHA-256.
