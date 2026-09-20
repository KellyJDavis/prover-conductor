---
id: ADR-0000
title: Record decisions as ADRs with enforced invariants
status: accepted
date: 2026-09-20
summary: >-
  Decisions live in docs/adr as ADRs with machine-readable frontmatter. Accepted ADRs are
  immutable, and only the owner changes an ADR's status. What enforces each invariant is recorded
  in docs/adr/enforcement.yaml, which stays editable and can give an invariant a scope in which
  real code makes its enforcement mandatory. Path-scoped Claude Code rules are generated from the
  ADRs.
applies_to:
  - "docs/adr/**"
  - "scripts/**"
  - ".claude/**"
depends_on: []
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0000-1
    text: >-
      Every enforcement reference in docs/adr/enforcement.yaml exists and names its invariant, and
      every entry names an invariant that an ADR defines.
  - id: INV-0000-2
    text: >-
      The files in .claude/rules/adr/ are exactly what scripts/gen_adr_rules.py generates from the
      ADRs.
  - id: INV-0000-3
    text: >-
      Claude Code's file tools cannot modify an accepted ADR, change an ADR's status, or edit a
      generated rule, in the main checkout or in any git worktree of it.
  - id: INV-0000-4
    text: >-
      Changes under docs/adr/, the enforcement file included, need the code owner's review.
  - id: INV-0000-5
    text: >-
      Once real code exists in an enforcement entry's scope, the invariant of an accepted ADR must
      be enforced.
revisit_when: >-
  The checks cost more friction than the drift they prevent, or scoped enforcement proves too weak
  to make tasks write their tests.
---

## Context

This repository is developed with Claude Code, which starts every session without the design
conversation that produced it. Claude Code treats CLAUDE.md and `.claude/rules/` as guidance, not
enforcement; hooks, permission rules, tests and CI are what constrain changes. Prose-only decision
records drift from the code, and nothing notices.

A first version of this setup, since discarded, taught three things. Recording enforcement inside
immutable ADRs meant nobody could record a new test for an accepted ADR. Using an ADR's
`applies_to` as the scope of mandatory enforcement made unrelated invariants block the first code
in an area. And sessions drafting ADRs on different branches took the same numbers.

## Decision

- Decisions are ADRs in `docs/adr/`, following `template.md` and the lifecycle in `README.md`.
  Accepted ADRs are immutable, and only the owner changes a status. A changed decision is a new ADR
  that supersedes the old one.
- Each invariant is a checkable statement. What enforces it lives in `docs/adr/enforcement.yaml`,
  which anyone, Claude Code included, may edit: references to tests, import-linter contracts,
  hooks, CI steps or CODEOWNERS entries, and an optional `scope`. ADRs carry no enforcement fields.
- An invariant without enforcement is debt, reported as a warning. It is an error only when its
  ADR is accepted, its entry declares a scope, and real code exists in that scope. A scope is added
  when a task starts implementing the invariant, so CI holds the task until the enforcing test
  exists. `scripts/check_invariants.py` checks all of this and fails CI on errors.
- `scripts/gen_adr_rules.py` turns each active ADR's `applies_to` into a path-scoped rule under
  `.claude/rules/adr/`, so Claude Code sees an ADR's decision and invariants when it reads code the
  ADR governs.
- ADR numbers come from `scripts/next_adr_number.py`, which checks every branch.
- A PreToolUse hook stops Claude Code's file tools from editing accepted ADRs, changing statuses or
  editing generated rules, in the main checkout and in any worktree. A Stop hook reruns the checks
  at the end of every turn. CODEOWNERS requires the owner's review for `docs/adr/`, `.claude/` and
  `.github/`.

## Consequences

- Claude Code can still change files through shell commands. The Stop hook reports working-tree
  changes to accepted ADRs, and code-owner review is the backstop.
- Branch protection on `main` must require the `ci` workflow and code-owner review. That setting
  lives in GitHub, not in the repository.
- The forcing function is opt-in per invariant. The adr-auditor subagent and review flag new code
  that an accepted invariant governs when it has neither enforcement nor a scope.

## Alternatives considered

- Prose-only ADRs: no mechanical link between decisions and code.
- Hand-written rules: they drift from the ADRs they summarize.
- All constraints in CLAUDE.md: loaded in every session whether relevant or not, and not enforced.
- Enforcement recorded inside ADRs and scoped by `applies_to`: tried and discarded, for the
  reasons under Context.
