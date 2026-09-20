---
id: ADR-0015
title: Agents are data; tools are code
status: proposed
date: 2026-09-19
summary: >-
  Every agent is an AgentSpec: prompt fragments, capability requirements, tool grant, budget,
  output schema and termination conditions. spawn_agent instantiates existing specs; define_agent
  creates new kinds within the definer's tool grant and budget. New tools arrive only through pull
  requests or administrator registration, and promotion to a shared library requires a replay
  evaluation.
applies_to:
  - "src/prover_conductor/agents/**"
  - "agent-library/**"
depends_on:
  - ADR-0001
  - ADR-0013
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0015-1
    text: >-
      A defined agent's tool grant is a subset of its definer's grant, and its budget is carved
      from the definer's budget.
  - id: INV-0015-2
    text: >-
      No code path lets an agent register a new tool.
  - id: INV-0015-3
    text: >-
      Agent specs are validated against a schema before use.
  - id: INV-0015-4
    text: >-
      The orchestrator's prompt is rebuilt from structured state each turn; no run state exists
      only in a model's context.
revisit_when: >-
  Replay evaluations show that defined agents rarely outperform the initial roster.
---

## Context

Requirement R5: a fixed initial set of agents, and an orchestrator that can create new ones. TeXRA
defines agents as YAML files, each free to use a different model. In the Lu, Tjoa and Cirac study,
roles were added one at a time as bottlenecks appeared, and the orchestrator accounted for 43% of
model spend because its context grew large.

## Decision

- Every agent is an AgentSpec: a role prompt assembled from versioned fragments, capability
  requirements, a tool grant, a budget (tokens, dollars, Lean CPU-seconds, wall clock), an output
  schema and termination conditions.
- Initial roster: orchestrator, statement formalizer, fidelity reviewer (never shares a context
  with the formalizer), prover (a portfolio of strategies), theorem-search scout, simplifier,
  blueprint maintainer, and a reviewer that runs on every patch.
- `spawn_agent` instantiates an existing spec and needs only budget. `define_agent` creates a new
  kind from existing fragments, with a tool grant no wider than the definer's and a budget carved
  from its own. At conservative autonomy presets a new kind needs human approval.
- Agents are data; tools are code. New tools arrive only through pull requests or administrator
  registration of an MCP server.
- Promoting a defined agent to a project or organization library requires a replay evaluation on
  past tasks; promotion to the platform library also needs platform review.
- Batch sampling, such as hundreds of whole-proof samples, is a scheduled job, not hundreds of
  agents.
- The orchestrator's state lives in the workflow layer, not in its context; its prompt is rebuilt
  each turn from structured state. Side-effecting control operations also exist as deterministic
  commands.

## Alternatives considered

- Agents as code classes: every new kind needs a release.
- Letting agents write tools: an agent could grant itself capabilities the policy never approved.
