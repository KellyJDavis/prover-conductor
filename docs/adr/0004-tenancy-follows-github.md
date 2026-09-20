---
id: ADR-0004
title: Tenancy and authorization follow GitHub
status: accepted
date: 2026-09-19
summary: >-
  A tenant is a GitHub repository, keyed by its numeric repository ID. The repository's owning
  account, user or organization, owns the tenant through its GitHub App installation, and every
  action is authorized against the acting user's current permission on the repository. Region is
  a deployment setting.
applies_to:
  - "src/prover_conductor/core/**"
  - "src/prover_conductor/vcs/**"
  - "src/prover_conductor/gate/**"
  - "src/prover_conductor/workflows/**"
depends_on:
  - ADR-0001
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0004-1
    text: >-
      Tenants are keyed by GitHub's numeric repository ID, never by owner and name.
  - id: INV-0004-2
    text: >-
      Every approval, merge and push re-checks the acting user's permission on the repository at
      the time of the action.
  - id: INV-0004-3
    text: >-
      Repository maintainers approve intent locks, and the main theorem's lock always needs a
      human approval.
  - id: INV-0004-4
    text: >-
      Every persistent store takes its location from deployment configuration; nothing hard-codes
      a region.
revisit_when: >-
  Users need tenants that span several repositories, for example a library split across repos.
---

## Context

The hosted service is open to arbitrary registered users and works on GitHub repositories, many
of them owned by organizations.

## Decision

- A tenant is a GitHub repository keyed by GitHub's numeric repository ID. Renames and transfers
  keep a tenant intact; a deleted and recreated repository is a new tenant.
- The repository's owning account (user or organization) owns the tenant through its GitHub App
  installation.
- Every action is authorized against the acting user's permission on the repository, re-checked
  at the moment of each approval, merge and push rather than cached from sign-in. Repository
  maintainers approve intent locks; the main theorem's lock always needs a human.
- Consent splits: each user consents for their own conversation traces, and the owning account
  for the repository's content (ADR-0014).
- The service operator, the legal entity responsible for the data, is a deployment-level role,
  not a GitHub account. It must be settled before public registration opens.
- Region is a deployment setting: every persistent store takes its location from deployment
  configuration.

## Consequences

- Budgets and quotas exist per user, per tenant and per owning account.
- Leases on project-graph nodes keep two users' runs off the same node.

## Alternatives considered

- Tenant = user: breaks for organization-owned repositories and shared projects.
- Tenant = App installation: too coarse, since one installation can cover many unrelated
  repositories.
