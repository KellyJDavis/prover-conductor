---
id: ADR-0009
title: Environment fingerprints and Lake-free fetch
status: proposed
date: 2026-09-19
summary: >-
  An environment fingerprint hashes lean-toolchain, the resolved lake-manifest.json and the
  lakefile options that affect elaboration; each fingerprint maps to a platform-built image and
  to pools of Lean workers. Dependencies are fetched by platform code from the manifest, with plain
  git at pinned revisions, so Lake never runs while networked.
applies_to:
  - "src/prover_conductor/envs/**"
  - "src/prover_conductor/lean/**"
  - "src/prover_conductor/search/**"
depends_on:
  - ADR-0003
  - ADR-0008
open_questions:
  - fingerprint-lakefile-options
  - mathlib-artifact-source
  - helper-version-cost
settled_by:
  - SPIKE-01
  - SPIKE-05
superseded_by: null
invariants:
  - id: INV-0009-1
    text: >-
      The fingerprint changes exactly when the toolchain, a resolved dependency revision, or an
      elaboration-affecting option changes.
  - id: INV-0009-2
    text: >-
      Every Lean request is served by a pool pinned to the requesting worktree's fingerprint.
  - id: INV-0009-3
    text: >-
      Search candidates are checked in the requesting environment before a prover sees them.
  - id: INV-0009-4
    text: >-
      A project's toolchain and dependencies change only in an environment-change task that a
      human approved.
revisit_when: >-
  Lake gains an offline, hook-free way to materialize a workspace from its manifest.
---

## Context

Requirements R3, R7 and R14: Lean services for many versions, in the cluster or external.

## Decision

- Environment fingerprint: a hash of `lean-toolchain`, the resolved `lake-manifest.json`, and the
  lakefile options that affect elaboration. For `lakefile.lean`, the options are read inside the
  offline sandbox.
- An environment builder turns each fingerprint into an image: toolchain from the mirror,
  dependencies fetched from the manifest and built, Mathlib artifacts placed.
- The Lean router sends every request to a pool pinned to the requesting worktree's fingerprint.
  Backends sit behind one LeanService interface: lean-lsp-mcp or a raw LSP session for goals and
  diagnostics (with session affinity), a REPL through LeanInteract, the Kimina Lean Server for
  batch checking, and Pantograph for goal-level search. Any backend can run in the cluster or be
  external.
- Build artifacts are cached per fingerprint and commit. Pools for idle fingerprints scale to zero.
- Search is version-consistent: every candidate lemma from LeanExplore, Loogle or LeanSearch is
  checked with `#check` in the requesting environment before a prover sees it.
- prover-conductor never changes a project's toolchain or dependencies on its own. An upgrade is an
  environment-change task with human approval, including lock migration (ADR-0010).

## Open questions

- `fingerprint-lakefile-options`: which lakefile options affect elaboration?
- `mathlib-artifact-source`: Mathlib's upstream build cache, or platform builds? (SPIKE-01)
- `helper-version-cost`: what does keeping the Lean helper building across the window cost?
  (SPIKE-05)

## Alternatives considered

- One global Lean version: violates R7.
- Running `lake update` or `lake exe cache get` during fetch: runs user code with network access
  (ADR-0008).
