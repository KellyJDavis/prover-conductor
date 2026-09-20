---
id: SPIKE-05
title: One Lean helper across the support window
informs: [ADR-0003, ADR-0009]
status: open
---

## Question

Can one source tree of `lean/ConductorTools` build and run on every toolchain in the support
window, or does it need per-version shims? Does loading a project's environment ever run the
project's `initialize` blocks?

## Why it matters

Every gate check and every decomposition check depends on the helper (ADR-0002, ADR-0010). Its
maintenance cost is the main cost of the version window (ADR-0003).

## Method

1. Create the helper as a Lean package under `spikes/SPIKE-05/ConductorTools`, depending on Lean
   core only, with the first queries: declaration existence, axioms used, `sorryAx`
   reachability, project-local constants used, and a placeholder statement hash (SPIKE-03 defines
   the real one). It stays there: build step 2 moves it into `lean/ConductorTools`.
2. Build and run it against a small fixture project on the oldest and newest toolchains in the
   window, then on every release in between: locally on macOS, and on Linux through a workflow
   this spike may add, `.github/workflows/spike-05-lean-helper.yml`.
3. Catalog each metaprogramming API difference and how it was bridged.
4. Test whether `initialize` blocks in the inspected project execute when its environment is
   loaded.

## Exit criteria

- `.github/workflows/spike-05-lean-helper.yml` builds and runs the helper on every toolchain in
  the window on Linux, and the macOS results are recorded.
- The list of API differences, and a decision: single source or per-version shims.
- The `initialize` behavior documented for each toolchain.
- The JSON output schema in `docs/specs/lean-facts.md`.

## Time box

Set when starting; suggested five working days.

## Results

Not started.

## Implications for ADRs

Not started.
