# check_spec emission guide (producer side of SP1a contract)

When generating author-dna.yaml, for each principle that is mechanically checkable,
emit `mechanically_checkable: true` + `check_spec`. Supported ir_rules (SP1a):

| Principle pattern | ir_rule | params |
|---|---|---|
| "no/zero nested for" | max_for_nesting | { max: 0 } |
| "no/zero nested if beyond depth N" | max_if_nesting | { max: N, guard_exception: true } |
| "no else / guard clause only" | forbid_else | { severity_override: warning } |
| "method must be <= N lines" | (covered by complexity_thresholds.max_lines_per_method) | — |
| "max N branches/cyclomatic" | (covered by complexity_thresholds.max_method_branches) | — |
| "javadoc must have @author/@since" | require_javadoc_tag | { tags: [...], scope: [public, protected] } |
| naming rules | KHÔNG emit từ DNA builder — naming thuộc conventions.yaml. Nếu rule là global regex: convention-intelligence-builder ghi vào section `naming_patterns` (machine lane); nếu theo layer/suffix: section `naming` (human lane) | — |

Principles WITHOUT a clean mechanical mapping (CoR, Template Method, Strategy, Factory
boundary, SOLID, config-driven, extraction) → set `mechanically_checkable: false`.
These stay semantic and are enforced by SP1b (subagent), not the linter.

After writing/updating approved DNA, regenerate the ruleset (see SP1a design §3.2):
`python3 {{ platform.framework_root }}/tools/rule-projector/projector.py --dna <dna> --conventions <conv> --out generated/`
then the checkstyle backend:
`python3 {{ platform.framework_root }}/tools/rule-projector/backends/checkstyle.py --ir generated/rules.json --out generated/checkstyle.generated.xml`
