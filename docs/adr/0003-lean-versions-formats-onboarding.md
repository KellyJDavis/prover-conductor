---
id: ADR-0003
title: Supported Lean versions, project formats and onboarding
status: accepted
date: 2026-09-19
summary: >-
  Repositories must use an official leanprover/lean4 stable release or release candidate from
  roughly the last year, exactly one of lakefile.lean and lakefile.toml per package, and the
  leanblueprint layout. prover-conductor adds a missing layout as its first gated commit, with a
  Lake project on the newest supported toolchain when the repository is empty.
applies_to:
  - "src/prover_conductor/envs/**"
  - "src/prover_conductor/blueprint/**"
  - "src/prover_conductor/lean/**"
depends_on:
  - ADR-0001
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0003-1
    text: >-
      A toolchain is accepted only if it is an official leanprover/lean4 stable release or release
      candidate inside the support window; nightlies and other origins are rejected at onboarding.
  - id: INV-0003-2
    text: >-
      Every package, dependencies included, has exactly one of lakefile.lean and lakefile.toml.
  - id: INV-0003-3
    text: >-
      lakefile.lean is evaluated only inside an offline sandbox.
  - id: INV-0003-4
    text: >-
      A repository without the leanblueprint layout is onboarded only through a scaffolding commit
      that passes the gate like any other change.
revisit_when: >-
  A significant share of target repositories track nightlies, or the window excludes projects
  that users need.
---

## Context

Requirement R7: no binding to one Lean or Mathlib version. Mathlib's master branch moves to each
Lean release candidate as it appears (for example, to v4.35.0-rc2 on 2026-09-16), and downstream
projects that follow Mathlib's tags follow release candidates too. The community uses both
`lakefile.lean` and `lakefile.toml`. The most automated level (R8) starts from a repository that
may have neither a blueprint nor a Lean project.

## Decision

- Supported toolchains: official `leanprover/lean4` stable releases and release candidates
  published in roughly the last year. The exact window is configuration, recomputed as releases
  appear. Nightlies and every other origin are rejected at onboarding.
- Each package, dependencies included, has exactly one of `lakefile.lean` and `lakefile.toml`.
  `lakefile.lean` is code, so it is evaluated only inside an offline sandbox (ADR-0008).
- The leanblueprint layout is required. A repository without it is onboarded through a
  scaffolding commit that adds it and passes the gate like any other change. For an empty
  repository, the scaffold includes a Lake project on the newest supported toolchain.

## Consequences

- Roughly one environment fingerprint per release and release candidate in the window (ADR-0009).
- The Lean helper must build on every toolchain in the window; SPIKE-05 measures what that costs.

## Alternatives considered

- Stable releases only: rejects every project that tracks Mathlib master.
- Any toolchain: unverifiable origins and an unbounded version matrix.
