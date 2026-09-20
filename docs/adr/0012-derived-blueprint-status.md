---
id: ADR-0012
title: Blueprint status is derived, never claimed
status: proposed
date: 2026-09-19
summary: >-
  The project graph joins the leanblueprint TeX, parsed with leanblueprint's own plasTeX plugin,
  with facts from the Lean environment at the same commit. Status comes from the join, and
  \leanok is written only by deterministic code after the gate passes. Helper lemmas live in a
  working graph and are promoted to the public blueprint only when mathematically meaningful.
applies_to:
  - "src/prover_conductor/blueprint/**"
depends_on:
  - ADR-0003
open_questions:
  - parse-fidelity
settled_by:
  - SPIKE-06
superseded_by: null
invariants:
  - id: INV-0012-1
    text: >-
      Only the deterministic blueprint writer sets \leanok, and only after a passing gate run.
  - id: INV-0012-2
    text: >-
      The drift check fails on a \leanok claim the Lean facts contradict, a \uses that misses a
      project-local dependency a proof uses, or a \lean{} name that does not exist.
  - id: INV-0012-3
    text: >-
      Working-graph helper lemmas are committed as private declarations beside their parent until
      promoted to the blueprint.
  - id: INV-0012-4
    text: >-
      Blueprint prose written by agents contains no Lean identifiers.
revisit_when: >-
  leanblueprint or LeanArchitect starts deriving status from Lean itself.
---

## Context

In leanblueprint, `\leanok` is the author's assertion, and `checkdecls` verifies only that
referenced names exist. Goedel-Architect keeps one global dependency graph and rewrites it between
proving passes; Numina's Fuse shows open work through the blueprint's `\uses` and `\leanok`.

## Decision

- The project graph joins the TeX (nodes, labels, `\lean{}` links, statement-level and proof-level
  `\uses`) with facts from the Lean environment at the same commit: existence, `sorryAx`
  reachability, axioms, and the project-local constants each proof uses.
- Status is derived from the join and never read from the TeX. `\leanok` is written by
  deterministic code after a passing gate run; agents write prose, not status.
- Drift is a check: contradicted `\leanok` claims, `\uses` that miss real dependencies, and
  dangling `\lean{}` names.
- Two levels: the public blueprint in the repository, and the working graph where refinement puts
  helper lemmas. The blueprint maintainer promotes a working node when it is mathematically
  meaningful; until then helpers stay private declarations beside their parent.
- Blueprint prose is self-contained mathematics with no Lean identifiers.
- Repositories that use LeanArchitect's `@[blueprint]` annotations get an adapter that reads the
  same facts from Lean.

## Open questions

- `parse-fidelity`: how well leanblueprint's parser handles real blueprints (SPIKE-06).

## Alternatives considered

- Trust `\leanok`: status drifts from reality and cannot gate anything.
- Put every helper lemma in the public blueprint: buries the mathematics under plumbing.
