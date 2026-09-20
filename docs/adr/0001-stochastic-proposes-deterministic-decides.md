---
id: ADR-0001
title: The stochastic layer proposes; the deterministic layer decides
status: accepted
date: 2026-09-19
summary: >-
  Agents and models only propose patches against worktrees in the internal git store. The commit
  gate is the only component that writes to GitHub, and only after its checks pass on a hermetic
  build of the exact commit. The same gate runs as a required check in target repositories.
applies_to:
  - "src/prover_conductor/gate/**"
  - "src/prover_conductor/vcs/**"
  - "src/prover_conductor/agents/**"
  - "src/prover_conductor/models/**"
depends_on: []
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0001-1
    text: >-
      Only prover_conductor.gate imports prover_conductor.vcs.github_write, the sole client of
      GitHub write APIs.
  - id: INV-0001-2
    text: >-
      The deterministic layer (core, vcs, gate, lean, sandbox, envs, blueprint, search, traces,
      data) never imports the stochastic layer (agents, models).
  - id: INV-0001-3
    text: >-
      Nothing is pushed to GitHub unless the gate passed on the exact commit being pushed; work in
      progress stays in the internal git store.
  - id: INV-0001-4
    text: >-
      Platform writes to tenant repositories are pull requests. Merging happens in GitHub, with
      auto-merge only in autonomy presets that allow it, so branch protection stays authoritative.
  - id: INV-0001-5
    text: >-
      Every gate run yields an attestation that states its tier: gate-passed (checks ran in the
      tenant's environment) or certified (Comparator replay on platform binaries against a
      published challenge).
revisit_when: >-
  A class of acceptance decision turns out to need judgment that no deterministic check can
  express, and human review cannot keep up with it.
---

## Context

Requirement R15: nothing with errors, lint failures or deviations from the repository's coding
standards may be committed. Model output is stochastic and can be steered by untrusted input;
the Lean kernel and deterministic checks are neither.

## Decision

- Agents, the orchestrator included, produce patches against worktrees in prover-conductor's
  internal git store. They hold no GitHub credentials.
- The commit gate is the only component that writes to GitHub, as a GitHub App, and only after a
  fixed pipeline of checks passes on a hermetic build of the exact commit (stages in ADR-0011,
  locks in ADR-0010).
- Work in progress never leaves the internal store, so nothing unverified reaches GitHub even
  under the strict reading in which pushing a branch counts as committing.
- Platform writes are pull requests; merging happens in GitHub, with auto-merge in autonomy presets
  that allow it.
- The same gate ships as a GitHub Action that branch protection makes a required check, so a
  compromised or misconfigured deployment still cannot merge what the gate rejects.
- Attestations state their tier: gate-passed, or certified (ADR-0010).

## What the gate can and cannot establish

The gate enforces what is mechanically decidable: a clean build under the repository's linter
profile, `sorry` only where authorized, axioms within an allowlist, locked statements and
definitions unchanged, kernel replay, and agreement between the blueprint and Lean. It cannot
establish that names follow Mathlib's naming conventions, that a lemma has the right generality,
or that a formal statement means what its informal counterpart means. Reviewer agents and human
approval of intent locks cover those; the autonomy policy decides where a human signature is
required.

## Consequences

- Bugs in the gate's own checks are the main residual risk. The gate gets an adversarial test
  suite: statement weakening, hidden axioms, `debug.skipKernelTC`, instance hijacking, notation
  shadowing, elaboration-time I/O, hostile lakefiles, spoofed toolchains and dependencies.
- A merge queue re-runs the gate on each patch rebased onto the current head.

## Alternatives considered

- Agents push branches and rely on CI: unverified code reaches GitHub, and CI runs in an
  environment the tenant controls.
- Human review only: does not scale to parallel agents, and misses mechanical errors.
