---
id: SPIKE-07
title: Provider terms and what APIs expose for traces
informs: [ADR-0013, ADR-0014, ADR-0016]
status: open
---

## Question

For each launch provider (OpenAI, Anthropic, and OpenAI-compatible servers such as vLLM and
Ollama): what do the terms say about training on outputs, retention and zero-data-retention, and
what does the API expose that traces need (reasoning content, log probabilities, token IDs,
usage)?

## Why it matters

Dataset builders filter by provider terms (ADR-0014), and the event schema depends on what can be
recorded (ADR-0016).

## Method

1. The owner reads the current terms for each hosted provider and records the relevant clauses
   with links and dates.
2. Claude Code sends identical requests to each provider with small scripts under
   `spikes/SPIKE-07/` (not product adapters, which come later) and records the exact request and
   response shapes.

## Exit criteria

- A table per provider: training restrictions, retention, zero-data-retention availability,
  reasoning, log probabilities, token IDs.
- Proposed event-schema fields.
- Any planned use a provider's terms rule out, flagged.

## Time box

Set when starting; suggested three working days.

## Results

Not started.

## Implications for ADRs

Not started.
