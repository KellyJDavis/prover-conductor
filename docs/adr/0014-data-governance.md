---
id: ADR-0014
title: Data governance and training eligibility
status: proposed
date: 2026-09-19
summary: >-
  Every event records its tenant's consent state and a data classification at write time, and
  dataset builders select on them. Nothing enters a shared model without opt-in; anything trained
  on a tenant's private data serves only that tenant. Payloads are encrypted with per-tenant keys
  so erasure is key destruction. Provider terms are recorded with every record.
applies_to:
  - "src/prover_conductor/traces/**"
  - "src/prover_conductor/data/**"
depends_on:
  - ADR-0004
open_questions:
  - provider-terms
  - legal-review
settled_by:
  - SPIKE-07
superseded_by: null
invariants:
  - id: INV-0014-1
    text: >-
      Every event carries its tenant, the tenant's consent state and a data classification, as of
      write time.
  - id: INV-0014-2
    text: >-
      Dataset builders exclude events whose consent state or provider terms disallow the target
      use.
  - id: INV-0014-3
    text: >-
      Payloads are encrypted with per-tenant keys, and destroying a tenant's key makes its payloads
      unreadable.
  - id: INV-0014-4
    text: >-
      A model trained on a tenant's private data is served only to that tenant.
revisit_when: >-
  Legal review changes the consent model, or a launch provider changes its terms.
---

## Context

Traces are future training data (R12), and the hosted service is open to arbitrary users, so
training on traces needs consent and erasure from the first event.

## Decision

- Every event records the tenant's consent state and a data classification as of write time.
  Dataset builders select on those fields, and a withdrawal excludes the tenant from every later
  build.
- Nothing enters a shared model without opt-in. Shared models train only on public repositories
  whose licenses allow it. Anything trained on a tenant's private data serves only that tenant.
- Every record carries provenance: tenant, repository license, environment fingerprint, generating
  model and provider terms. Builders filter by provider terms, since some API providers restrict
  using outputs to train competing models.
- Payloads are encrypted with per-tenant keys; erasure is key destruction (crypto-shredding).
  Trained weights cannot reliably forget, so the consent text says so before anything is used.
- Open registration includes EU users, so GDPR applies. The consent flow, retention and terms need
  legal review before launch; these records are not legal advice.
- prover-conductor's own RLVR training uses tasks derived from physicslib4, which is first-party
  data and needs no user consent.

## Open questions

- `provider-terms`: training restrictions, retention and zero-data-retention options per launch
  provider (SPIKE-07).
- `legal-review`: the consent flow and retention policy.

## Alternatives considered

- Decide consent at dataset build time: impossible to reconstruct what a user agreed to when an
  event was written.
- Delete payloads for erasure: an append-only event log makes deletion error-prone; key destruction
  is one operation.
