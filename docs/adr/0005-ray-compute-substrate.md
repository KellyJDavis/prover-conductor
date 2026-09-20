---
id: ADR-0005
title: Ray is the compute substrate
status: accepted
date: 2026-09-19
summary: >-
  Platform services run on Ray. Tenant-controlled and model-written code runs only through the
  SandboxRunner interface, backed on clusters by Ray Sandboxes (gVisor) with networking disabled.
  Ray itself is never the isolation boundary, and Ray actors never hold state that must survive a
  restart.
applies_to:
  - "src/prover_conductor/sandbox/**"
  - "src/prover_conductor/workflows/**"
  - "deploy/**"
  - "serving/**"
depends_on:
  - ADR-0004
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0005-1
    text: >-
      Tenant-controlled or model-written Lean code never executes in a Ray worker process; it runs
      only through SandboxRunner.
  - id: INV-0005-2
    text: >-
      Every cluster sandbox that runs tenant-controlled or model-written code has networking
      disabled.
  - id: INV-0005-3
    text: >-
      Every cluster deployment enables Ray token authentication and exposes no dashboard, Jobs API
      or Ray Client endpoint to tenants.
  - id: INV-0005-4
    text: >-
      Ray Sandboxes and any other pre-release sandbox API are used only behind SandboxRunner.
  - id: INV-0005-5
    text: >-
      Nothing that must survive a cluster restart, such as run state or pending approvals, is held
      only in a Ray actor.
revisit_when: >-
  Ray Sandboxes is withdrawn, or cannot run Lean and Mathlib workloads within the budget that
  SPIKE-02 sets.
---

## Context

prover-conductor needs distributed compute for agents, Lean workers, model serving and later RL
training, plus isolation for untrusted code.

## Decision

- Ray is the compute substrate for platform services. Ray Serve with vLLM serves self-hosted
  models, and the RL training stack runs on Ray too.
- Tenant-controlled and model-written code runs only through
  `prover_conductor.sandbox.SandboxRunner`. On clusters the backend is Ray Sandboxes, which runs
  gVisor on Ray worker nodes with networking disabled by default. Ray Sandboxes is an alpha API,
  which is one reason for the interface. The local backend is decided in ADR-0008.
- Ray is not the isolation boundary. Ray runs whatever code it is given and does not isolate jobs
  that share a cluster. So tenant code never runs as a Ray task or actor, token authentication
  (available since Ray 2.52) is on in every deployment, and the dashboard, Jobs API and Ray Client
  are never reachable by tenants.
- Sandboxes that run tenant-controlled code have networking disabled. Ray Sandboxes' public
  network mode can reach anything the node can, internal cluster services included, so it is
  never used for tenant code.
- Ray actors hold no durable state. Anything that must survive a restart, such as run state or
  approvals that wait for days, lives in a durable workflow layer whose engine is chosen when first
  needed.
- gVisor runs only on Linux, so local mode on macOS uses an OS-level sandbox backend rather than a
  virtual machine (ADR-0008).

## Consequences

- Deployment manifests must set Ray token authentication and network policy; `deploy/` does not
  exist yet.
- SPIKE-02 measures gVisor overhead and warm-start options for Lean workloads.

## Alternatives considered

- A Kubernetes pod per sandbox with a Kata or gVisor RuntimeClass: strong per-pod separation, but
  multi-second startup and no shared substrate with serving and RL training.
- Firecracker microVMs: need KVM on every host and more operational work.
