---
id: ADR-0006
title: Names and license
status: accepted
date: 2026-09-19
summary: >-
  The distribution is prover-conductor, the import package prover_conductor, and the console
  command conductor. The project is licensed Apache-2.0 for initial development.
applies_to:
  - "pyproject.toml"
  - "src/prover_conductor/__init__.py"
  - "src/prover_conductor/cli.py"
  - "LICENSE"
  - "README.md"
depends_on: []
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0006-1
    text: >-
      The distribution is named prover-conductor and installs the console command conductor.
  - id: INV-0006-2
    text: >-
      The import package is prover_conductor, and nothing installs a top-level conductor module.
  - id: INV-0006-3
    text: >-
      The project is licensed Apache-2.0 and LICENSE holds the full license text.
revisit_when: >-
  Before the first public release, if the hosted service should move to a copyleft license.
---

## Context

The first candidate, `orchestrator`, is taken on PyPI and collides with the name of the system's
own orchestrator agent. `lean-conductor` misdescribes the system, which conducts agents that prove
results in Lean rather than conducting Lean.

## Decision

- Distribution `prover-conductor`, import package `prover_conductor`, console command `conductor`.
- License: Apache-2.0 for initial development.

## Consequences

- The PyPI name `conductor` belongs to a project whose only release, from 2018, contains no code.
  PEP 541 has a process for claiming such names, but it is slow, and not needed here.
- The import package must not be `conductor`: `conductor-python`, the Conductor OSS SDK, installs a
  top-level `conductor` module.
- "Conductor" is a crowded name in agent tooling; expect search collisions.
- PyPI does not reserve names, so publish a minimal first release early.
- Versions published under Apache-2.0 stay available under it. Moving the hosted service to a
  copyleft license would have to happen before the first public release.

## Alternatives considered

`orchestrator` (taken, and ambiguous), `lean-conductor` (misdescribes the system),
`prover-orchestra`, `prover-agents`, `formal-agents`.
