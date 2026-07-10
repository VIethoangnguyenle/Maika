---
name: author-dna-builder
version: '1.0'
description: >
  Build and maintain Author DNA for Maika vNext by turning recurring confirmed
  engineering philosophy into durable guidance used by planning and review.
---

# Author DNA Builder

## Purpose
Capture durable author philosophy that affects engineering judgment.

## Triggers
Use during onboarding, after repeated review findings, or when the user confirms
a recurring philosophy that should guide future changes.

## Inputs
- Existing `knowledge/long-term/author-dna.yaml`.
- Verified examples from source or reviews.
- Capability IDs: `exact_source_inspection`, `convention_retrieval`.

## Required outcomes
- Draft Author DNA entries with scope, intent, enforcement, and evidence.
- Confirmed entries are marked durable.
- Rejected hypotheses are recorded when useful.

## Invariants
- Do not infer philosophy from code alone.
- Do not duplicate concrete conventions.
- Do not add one-off preferences.

## Evidence requirements
Confirmed entries cite user confirmation and at least one source or review
example when available.

## Process
1. Collect candidate recurring principles.
2. Separate philosophy from convention.
3. Ask for confirmation when needed.
4. Write or update Author DNA.
5. Regenerate knowledge index.

## Stop conditions
- The principle is not recurring.
- The user has not confirmed a philosophy claim.
- The entry belongs in conventions instead.

## Output contract
Write `knowledge/long-term/author-dna.yaml` updates and index changes.

## Next handoff
`convention-intelligence-builder` when concrete conventions are discovered.
