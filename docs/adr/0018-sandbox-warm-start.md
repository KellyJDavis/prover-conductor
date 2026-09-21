---
id: ADR-0018
title: Sandbox warm start with per-session sandboxes and pristine snapshots
status: proposed
date: 2026-09-21
summary: >-
  Each session gets its own sandbox and one long-lived Lean process, so the cost of importing
  Mathlib is paid once per session and no process is ever shared. Where the backend can, a session's
  Lean process may start by restoring a snapshot taken from a platform-built process that ran
  only `import` of a platform base image's libraries and never any tenant or model-written code.
applies_to:
  - "src/prover_conductor/sandbox/**"
  - "src/prover_conductor/envs/**"
  - "deploy/**"
depends_on:
  - ADR-0005
  - ADR-0008
open_questions:
  - snapshot-through-ray
  - snapshot-portability
settled_by:
  - SPIKE-02
superseded_by: null
invariants:
  - id: INV-0018-1
    text: >-
      A snapshot used to start a Lean process is taken only from a process started by a platform
      builder from a platform base image that has run nothing except imports of that image's
      libraries.
  - id: INV-0018-2
    text: >-
      Every restore of a snapshot creates a new sandbox for exactly one session; a restored or
      running sandbox is never handed to another tenant or session.
revisit_when: >-
  A backend's snapshot mechanism can capture tenant state that the restore then exposes, the
  overhead budget is set and measured numbers on a Linux KVM host exceed it, or Ray Sandboxes adds
  a snapshot API that changes what SandboxRunner should expose.
---

## Context

SPIKE-02 measured Lean workloads under gVisor (runsc release-20260914.0, systrap platform, no KVM,
arm64 Docker Desktop VM on Apple M2 Max) and Ray Sandboxes (Ray 2.58.0, alpha). Importing Mathlib
took 2.4 s bare and 9.4 s under gVisor, and it is the same cost for every fresh Lean process. Creating a
sandbox costs about 0.1 s and each command in a live sandbox about 7 ms, so the sandbox itself is
cheap and the repeated import is what hurts. `runsc checkpoint` of a warm `import Mathlib`
process took 3.3 s and produced a 483 MB image; restoring it reached a running process in 1.3 s
against about 11 s cold, with the process's in-memory state intact. Ray Sandboxes 2.58 has no
snapshot API. ADR-0008 forbids reusing a Lean process across tenants or sessions.

## Decision

- One sandbox per session, created through `SandboxRunner`, with one long-lived Lean process (or a
  small pool owned by that session) inside it, so `import Mathlib` is paid once per session.
- A backend that supports it may start that process by restoring a snapshot. The snapshot is
  built by a platform builder from a platform base image, from a process that has run only the
  imports (INV-0018-1). Each restore gives one session its own new sandbox (INV-0018-2). This
  does not reuse a process that elaborated tenant code, so it is consistent with INV-0008-6; it
  is a narrower statement of what "warm" may mean.
- Backends without snapshot support fall back to the cold start. `SandboxRunner` therefore
  exposes snapshot support as an optional capability, not a requirement.

- Overhead budget, set by the owner: a sandboxed workload may take at most 2.0x the bare wall
  time for a module rebuild, 2.0x for a heavy Mathlib file and 4.0x for `import Mathlib`. This is
  the budget that ADR-0005 and ADR-0008 refer to in their `revisit_when`. SPIKE-02 measured 1.7x,
  1.98x and 3.9x (gVisor systrap platform, no KVM, arm64), so all three fit, the heavy file
  with almost no margin.

## Consequences

- Session start is about 1.3 s with a snapshot and about 10 s without on the measured setup.
- Snapshots are per base image and Lean toolchain and must be rebuilt whenever the base image
  changes; each is about 0.5 GB for Mathlib.
- Ray Sandboxes cannot take or restore snapshots in 2.58, so a snapshot-capable backend either
  wraps runsc directly behind `SandboxRunner` or waits for a Ray API.

## Open questions

- `snapshot-through-ray`: wrap runsc directly for snapshots, or ask Ray for an API?
- `snapshot-portability`: does a checkpoint restore on another host or kernel? Not measured; it
  needs a Linux cluster.

## Alternatives considered

- Reusing warm Lean processes across sessions: fastest, but ruled out by INV-0008-6.
- A longer-lived per-tenant sandbox pool: weaker separation between sessions of one tenant and
  no measured need once restore takes about a second.
