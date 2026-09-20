---
id: SPIKE-02
title: Sandbox cost for Lean workloads
informs: [ADR-0005, ADR-0008]
status: open
---

## Question

What do the sandbox backends cost for Lean work? On Linux clusters: a Mathlib-dependent
`lake build` and an `import Mathlib` session under Ray Sandboxes (gVisor) against no sandbox;
image size and startup with a Mathlib-sized image; whether snapshot and restore of a warm Lean
process is available and how fast it is. Locally: the overhead of the OS-level sandbox runtime on
macOS for the same build.

## Why it matters

Warm Lean processes can't be shared across tenants or sessions (ADR-0008), so startup cost decides
the warm-start design. The accepted choice of Ray Sandboxes assumes the overhead is tolerable.

## Method

1. Use one sorry-free physicslib4 module and one Mathlib-heavy public file as workloads.
2. Measure wall time, peak memory and startup latency for: bare process, gVisor through Ray
   Sandboxes with `network="none"`, and on macOS, the OS-level sandbox. gVisor runs only on Linux,
   so its measurements need a Linux host with gVisor installed; the macOS measurements run
   locally.
3. Measure on an otherwise idle machine: no other builds, spikes or heavy applications running.
   Repeat each measurement at least three times, report the median and the spread, and record the
   hardware and operating system.
4. Check that `network="none"` blocks egress and cluster-internal addresses.
5. Test whatever snapshot and restore mechanism the backend offers, with an `import Mathlib`
   process as the snapshot.

## Exit criteria

- A table of timings and memory for each backend and workload, with commands, repetitions and
  hardware.
- Confirmation, by test, that network-less sandboxes reach nothing.
- A warm-start recommendation: per-session sandbox, snapshot and restore, or something else.

## Time box

Set when starting; suggested five working days.

## Results

Not started.

## Implications for ADRs

Not started.
