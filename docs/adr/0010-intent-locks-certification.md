---
id: ADR-0010
title: Intent locks, obligations and certification
status: proposed
date: 2026-09-19
summary: >-
  An intent lock covers a statement and the closure of project-local definitions, structures and
  instances it mentions. Every gate run checks lock hashes, and Comparator certifies locked
  theorems whose dependency cone is sorry-free. Locks carry obligations, such as a non-vacuity
  witness, that must be discharged before a node counts as done or certified. Environment upgrades
  migrate locks with human approval.
applies_to:
  - "src/prover_conductor/gate/**"
  - "src/prover_conductor/blueprint/**"
  - "lean/**"
depends_on:
  - ADR-0001
  - ADR-0004
open_questions:
  - hash-definition
  - comparator-scale
  - witness-policy
settled_by:
  - SPIKE-03
  - SPIKE-04
superseded_by: null
invariants:
  - id: INV-0010-1
    text: >-
      Changing a locked statement, or any definition, structure or instance in its closure,
      invalidates the lock and routes it back for approval.
  - id: INV-0010-2
    text: >-
      The certified tier is issued only after Comparator accepts, running on platform binaries,
      against a published challenge.
  - id: INV-0010-3
    text: >-
      A node with undischarged lock obligations is neither done nor certified, and every
      attestation reports obligation status.
  - id: INV-0010-4
    text: >-
      An environment upgrade re-hashes every lock and requires approval of each changed statement.
  - id: INV-0010-5
    text: >-
      Lock files are committed to the target repository so its own CI can verify them.
revisit_when: >-
  Statement hashing proves unstable under benign edits (SPIKE-03), or Comparator becomes cheap
  enough to run on every gate pass.
---

## Context

The kernel checks proofs, not meaning. The multi-agent autoformalization study by Lu, Tjoa and
Cirac (arXiv:2607.07857) found that keeping formal statements faithful to the intended mathematics
was harder than closing lemmas: the kernel accepted quietly weakened theorems and hypotheses that
nothing satisfies.

## Decision

- An intent lock covers a statement plus the transitive closure of the project-local definitions,
  structures and instances it mentions. Editing anything in the closure invalidates the lock.
  Hashing the elaborated statement catches notation shadowing and instance hijacking that a
  source-text comparison misses.
- Two tiers. Every gate run compares hashes of the elaborated statement and its definition
  closure, computed by the Lean helper in the pinned environment. Comparator certifies locked
  theorems whose whole dependency cone is sorry-free; it accepts only propext, Quot.sound and
  Classical.choice, so it cannot certify work that still depends on sorried lemmas.
- Locks carry an obligations list, for example a non-vacuity witness, a back-translation review
  or a human sign-off. A node with undischarged obligations is neither done nor certified, and
  attestations report obligation status. What counts as a non-degenerate witness is policy per
  lock, decided later.
- Lock files are committed to the target repository.
- Environment upgrades re-hash every lock, show old and new statements side by side for approval
  within the upgrade task, and flag locks whose Mathlib dependencies changed definition.
- Approval rights follow ADR-0004: repository maintainers approve locks, and the main theorem's
  lock always needs a human.

## Open questions

- `hash-definition`: binder names, universe parameters, instance arguments and the closure
  boundary (SPIKE-03).
- `comparator-scale`: cost and version coverage (SPIKE-04).
- `witness-policy`: what a non-vacuity witness must show.

## Alternatives considered

- Source-text comparison of statements: misses changes made through notation or instances.
- Comparator on every gate run: cannot handle sorried dependencies, and costs too much per patch.
