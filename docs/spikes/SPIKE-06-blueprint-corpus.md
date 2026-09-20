---
id: SPIKE-06
title: Blueprint parsing on real projects
informs: [ADR-0012]
status: open
---

## Question

How faithfully does leanblueprint's own plasTeX plugin recover nodes, labels, `\lean{}` links and
`\uses` edges from real blueprints?

## Why it matters

The project graph (ADR-0012) and onboarding (ADR-0003) depend on parsing blueprints the way
leanblueprint itself does.

## Method

1. Parse the public blueprints listed in leanblueprint's README, plus physicslib4's.
2. Compare the recovered graph with each project's own generated dependency graph.
3. Catalog every discrepancy and parse failure by cause.

## Exit criteria

- A fidelity table per project.
- The list of blueprint features the parser misses.
- A recommendation for the onboarding contract.

## Time box

Set when starting; suggested three working days.

## Results

Not started.

## Implications for ADRs

Not started.
