---
id: SPIKE-03
title: Statement-hash definition and stability
informs: [ADR-0010]
status: open
---

## Question

What exactly should a lock hash cover, so that benign edits leave it unchanged and meaning-changing
edits change it? Choices include binder names, universe parameter names, instance-implicit
arguments, and where the closure of project-local definitions stops.

## Why it matters

Intent locks are the defense against quietly weakened statements. A hash that is too sensitive
makes every refactor a re-approval; one that is too coarse lets meaning change unnoticed.

## Method

1. Prototype the hash in a scratch Lean package under `spikes/SPIKE-03/` (with the `lean-helper`
   subagent). It stays there: build step 2 moves it into `lean/ConductorTools`, together with
   SPIKE-05's helper.
2. Build a fixture project with pairs of edits. Benign: renaming a bound variable, reformatting,
   reordering unrelated declarations, changing a proof. Meaning-changing: weakening a hypothesis,
   changing a definition in the closure, adding a local instance, shadowing notation.
3. Write the cases as tests marked `lean`, under `spikes/SPIKE-03/`.

## Exit criteria

- A written hash specification in `docs/specs/statement-hash.md`.
- The fixture suite under `spikes/SPIKE-03/`, with at least ten benign and ten meaning-changing
  cases (adjust at start), behaves as specified; the command that runs it is recorded in Results.

## Time box

Set when starting; suggested five working days.

## Results

Not started.

## Implications for ADRs

Not started.
