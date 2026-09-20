---
id: ADR-0013
title: Model access through capability routing and bring-your-own-key
status: proposed
date: 2026-09-19
summary: >-
  Agents request capabilities, not models, and a routing policy maps them to endpoints. At launch,
  access is bring-your-own-key through three adapters: OpenAI, Anthropic's native Messages API,
  and OpenAI-compatible endpoints such as vLLM and Ollama. On the hosted service, user-supplied
  endpoints pass SSRF protections and must authenticate. The gateway logs every request exactly as
  sent.
applies_to:
  - "src/prover_conductor/models/**"
depends_on:
  - ADR-0004
open_questions:
  - trace-exposure
settled_by:
  - SPIKE-07
superseded_by: null
invariants:
  - id: INV-0013-1
    text: >-
      No agent spec names a concrete model; agents declare capability requirements.
  - id: INV-0013-2
    text: >-
      The gateway records each request exactly as sent, with sampling parameters and model
      identity and revision, and the full response, including reasoning where it is exposed.
  - id: INV-0013-3
    text: >-
      On the hosted service, user-supplied endpoints are reached only through an egress path that
      refuses loopback, private and link-local addresses and pins resolved addresses, and only over
      authenticated HTTPS.
  - id: INV-0013-4
    text: >-
      Provider keys are stored encrypted per tenant and never enter an agent's context or a
      sandbox.
revisit_when: >-
  The hosted service starts paying for inference, or a launch provider's terms rule out a planned
  use of its outputs.
---

## Context

Requirements R2, R4 and R13. The launch economics are bring-your-own-key: the hosted service does
not pay for inference.

## Decision

- Agents request capabilities (tool use, context length, reasoning, whole-proof Lean generation,
  cost tier). A routing policy maps capabilities to endpoints, with fallbacks and canaries.
- Launch adapters: OpenAI; Anthropic through its native Messages API, because traces need its
  thinking blocks; and OpenAI-compatible endpoints such as vLLM and Ollama. A prompt-adapter layer
  handles model families that expect fixed templates, such as specialized provers.
- For vLLM and Ollama, bring-your-own-key means bring-your-own-endpoint. On the hosted service
  such endpoints are reached only through a protected egress path and must use HTTPS with
  authentication; Ollama does not authenticate by default, so users put a token in front of it.
  Local mode may use localhost endpoints.
- The gateway records each request exactly as sent (rendered prompt, sampling parameters, model
  identity and revision) and the full response.
- Provider keys are stored encrypted per tenant and never enter an agent's context or a sandbox.
- R13 at launch is met by self-hosted deployments (Ray Serve with vLLM) and by users who serve
  released weights on their own endpoints.

## Open questions

- `trace-exposure`: what each API exposes for traces: reasoning, log probabilities, token IDs
  (SPIKE-07).

## Alternatives considered

- Platform-paid inference at launch: costs scale with open registration before any revenue.
- A generic abstraction library in place of adapters: loses provider-specific fields that traces
  need.
