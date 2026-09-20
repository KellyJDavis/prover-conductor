---
id: SPIKE-04
title: Comparator at scale
informs: [ADR-0010]
status: open
---

## Question

What does certification with Comparator cost for realistic theorems, how must definitions in the
challenge match the solution, and on which toolchains in the support window do matching Comparator
and lean4export releases exist?

## Why it matters

The certified tier (ADR-0001, ADR-0010) depends on Comparator replaying proofs through platform
binaries. If it is too slow or missing for part of the window, the tier needs a different shape.

## Method

1. Write challenges by hand for one sorry-free physicslib4 theorem and for one theorem from a
   large public blueprint project. Lock files don't exist yet (SPIKE-03 defines what they hash),
   and writing challenges by hand keeps this spike independent of SPIKE-03.
2. Run Comparator on each; record time, memory and failure modes.
3. Tabulate Comparator and lean4export availability across the support window.

## Exit criteria

- Measured costs for both theorems, with commands.
- One working hand-written challenge, with notes on what generating it from a lock would take.
- The version table.

## Time box

Set when starting; suggested three working days.

## Results

Not started.

## Implications for ADRs

Not started.
