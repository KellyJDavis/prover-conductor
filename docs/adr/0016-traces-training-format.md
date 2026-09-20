---
id: ADR-0016
title: Traces are the training-data format
status: proposed
date: 2026-09-19
summary: >-
  Everything is an event: model calls, tool calls, Lean interactions, gate stages, questions,
  decisions, approvals, and human edits of agent proposals. The event schema is the training-data
  schema. RLVR tasks are extracted from repositories by truncating the environment before each
  proved declaration, with the gate's verification profile as the reward.
applies_to:
  - "src/prover_conductor/traces/**"
  - "src/prover_conductor/data/**"
  - "evals/**"
depends_on:
  - ADR-0014
open_questions:
  - schema-exposure
settled_by:
  - SPIKE-07
superseded_by: null
invariants:
  - id: INV-0016-1
    text: >-
      Every model call is recorded as an event before its result is used.
  - id: INV-0016-2
    text: >-
      An RLVR task's environment contains nothing at or after its declaration, and the reference
      proof passes the task's own checker.
  - id: INV-0016-3
    text: >-
      Evaluation splits are made by blueprint chapter or dependency cluster, never at random.
  - id: INV-0016-4
    text: >-
      The difference between an agent's proposal and the version a human approved is recorded as
      an event.
revisit_when: >-
  Training pipelines need a representation that events cannot be converted into losslessly.
---

## Context

Requirements R11 and R12: inspection of running work, and inference results that are easy to
train on.

## Decision

- Everything is an event: model calls (rendered request, response, usage), tool calls, Lean
  interactions (goals, diagnostics), gate stages, questions, decisions, approvals, and the
  difference between what an agent proposed and what a human approved.
- The event schema is the training-data schema. Spans follow OpenTelemetry's GenAI conventions.
- Inspection reads the same stream: a live agent tree, per-agent streams, attach, steer, pause,
  kill and fork, rollups for large fan-outs, and step-by-step replay.
- Dataset builders produce supervised data (verified proofs and successful trajectories),
  preference pairs (human edits at review, gate failures paired with their fixes, reviewer
  verdicts) and RLVR task sets.
- RLVR extraction: each proved declaration becomes a task whose environment is truncated to what
  precedes it, with duplicate statements removed; the goal is the locked statement; the reward is
  the gate's verification profile (compile, axioms, statement match, no style checks). The same
  code is the evaluation harness.
- Evaluation splits are by blueprint chapter or dependency cluster, never random. Scores on
  declarations older than a model's training cutoff are upper bounds.
- Storage: hot state in Postgres, payloads in object storage as Parquet. The live fan-out
  mechanism is chosen together with the workflow layer.

## Open questions

- `schema-exposure`: event fields depend on what providers expose (SPIKE-07).

## Alternatives considered

- Separate logging and training formats: every conversion loses fields, and datasets can't be
  rebuilt from the source of truth.
