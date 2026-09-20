---
id: ADR-NNNN
title: A short statement of the decision
status: proposed
date: YYYY-MM-DD
summary: >-
  One to three sentences stating the decision. The rule generator copies this into
  .claude/rules/adr/, so it must stand on its own.
applies_to:
  - "src/prover_conductor/<area>/**"
depends_on: []
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-NNNN-1
    text: >-
      A statement a test, contract, hook, CI step or reviewer can check.
revisit_when: >-
  A condition that would make this decision wrong.
---

<!--
status: proposed | accepted | superseded | rejected (only the owner changes it)
applies_to: globs relative to the repository root; they become the generated rule's `paths:`
invariants: record what enforces each one in docs/adr/enforcement.yaml, not here (ADR-0000)
settled_by: SPIKE-NN ids whose results accept or amend this ADR
-->

## Context

What forces the decision: requirements, constraints, evidence.

## Decision

What we do. Specific enough that the invariants follow from it.

## Consequences

What becomes easier, harder, or newly required.

## Alternatives considered

What else was on the table and why it lost.
