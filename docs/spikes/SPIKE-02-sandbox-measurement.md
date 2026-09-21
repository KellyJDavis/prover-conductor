---
id: SPIKE-02
title: Sandbox cost for Lean workloads
informs: [ADR-0005, ADR-0008]
status: done
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

Five working days, from 2026-09-21 (confirmed by the owner at spike start).

## Results

### Scope actually run

The owner has no Linux or KVM host, so this spike ran on a Mac with Docker only. Measured: bare vs
gVisor (systrap platform) inside a privileged Docker container, Ray Sandboxes' local runtime
(`ray.experimental.sandbox.SandboxRuntime`, the backend the `Sandbox` actor wraps), and the macOS
`@anthropic-ai/sandbox-runtime` (`srt`). **Not measured:** gVisor's KVM platform, x86-64, a real
multi-node Ray cluster (the `Sandbox` actor path through `ray.init` and scheduling), cross-host
snapshot restore, and the "idle machine" requirement beyond checking that no other container was
running. Every number below is from this one machine, so treat ratios as indicative and absolute
times as specific to it. See "Rerunning on a Linux host with KVM".

### Setup (2026-09-21)

- Hardware: Apple M2 Max, 12 CPUs, 64 GB; macOS 26.5.1 (Darwin 25.5.0); Docker 29.2.1, Docker
  Desktop VM kernel 6.12.72-linuxkit, arm64, 12 CPUs and about 16 GB given to the VM. No `/dev/kvm`.
- Lean v4.32.0, Mathlib `81a5d25` as pinned by physicslib4 (sorry-free modules), cache placed with
  `lake exe cache get`, `lake build` succeeded (3176 jobs; 2 m 38 s natively on macOS, 3 m 28 s in
  Docker/arm64 Linux).
- gVisor `runsc release-20260914.0`, `--platform=systrap --network=none --ignore-cgroups
  --host-uds=none --overlay2=none`, run nested inside `docker run --privileged` (image
  `spikes/SPIKE-02/docker/Dockerfile.gvisor`). "Bare" is the same container without `runsc`.
- Project tree on a Docker volume (VM-local ext4), not a Mac bind mount, so file I/O is not
  virtiofs. Each run is a fresh container (`--cpus=8 --memory=14g`), so per-run peak memory comes
  from the container cgroup (`memory.peak`); the Linux page cache is warm and shared across runs.
- Workloads (`spikes/SPIKE-02/docker/inner.sh`, `mac_bench.py`):
  - `startup`: `true`.
  - `import`: `lake env lean fixtures/import_mathlib.lean` (`import Mathlib`, `#eval 1 + 1`).
  - `heavy`: `lake env lean` on Mathlib's `Analysis/Calculus/ContDiff/Basic.lean` (a public
    Mathlib file, the slowest of the candidates tried, elaborated against built imports).
  - `build`: delete the artifacts of `Physicslib4.Spacetime.Minkowski` (1786 lines, no `sorry`),
    then `lake build Physicslib4.Spacetime.Minkowski`. Mathlib itself is not rebuilt.
- Prep (network on, not timed): `spikes/SPIKE-02/docker/prep.sh`; `work/physicslib4` is a fresh
  clone of physicslib4 fetched with SPIKE-01's `fetcher.py`.

### Linux: bare vs gVisor (5 repetitions each, all exit 0)

Command: `spikes/SPIKE-02/bench.sh 5 bare gvisor` then `python3 spikes/SPIKE-02/summarize.py`.
Raw data is `spikes/SPIKE-02/work/results.jsonl` (ignored by git); the table is the summary.
Peak memory is the container cgroup peak, which under gVisor includes the sandbox's own memory.
gVisor does not report a per-process max RSS through `time -v` (0 in the data), so no RSS column.

| workload | backend | wall s median | wall s min-max | cgroup peak MB |
|---|---|---|---|---|
| startup | bare | 0.003 | 0.002-0.003 | 7 |
| startup | gvisor | 0.043 | 0.042-0.045 | 47 |
| import | bare | 2.409 | 2.356-2.422 | 735 |
| import | gvisor | 9.383 | 8.991-9.595 | 1197 |
| heavy | bare | 4.624 | 4.568-4.832 | 500 |
| heavy | gvisor | 9.170 | 9.091-9.644 | 622 |
| build | bare | 7.391 | 7.037-7.719 | 757 |
| build | gvisor | 12.520 | 12.418-12.651 | 824 |

gVisor is 3.9x on `import Mathlib` (which mmaps about 6 GB of `.olean` files through gVisor's file
gateway), 2.0x on the heavy file and 1.7x on the module rebuild. Memory overhead is 60-470 MB.

### Ray Sandboxes (Ray 2.58.0, alpha) on the same workloads

Ray Sandboxes is a persistent `runsc run` container per sandbox plus `runsc exec` per command, with
images pulled from an HTTPS registry or, for a local `.tar`, extracted as a single rootfs layer.
Command: `docker run --rm --privileged -v .../work/rootfs.tar:/data/rootfs.tar:ro ... spike02-ray
python /b.py 4` (`ray_sandbox_bench.py`; image `docker/Dockerfile.ray`; rootfs from
`docker export` of the baked image). Settings: `network="none"`, `readonly=False`,
`rootless=False`, `RAY_SANDBOX_IGNORE_CGROUPS=1`. Four sandboxes, one after another:

| step | wall s, per sandbox (rep 0 / 1 / 2 / 3) |
|---|---|
| extract 11.2 GB rootfs tar (once) | 18.0 |
| create sandbox | 0.113 / 0.115 / 0.113 / 0.118 |
| exec `true` | 0.006 / 0.007 / 0.007 / 0.007 |
| exec `import Mathlib` | 18.97 (cold page cache) / 9.61 / 9.55 / 9.46 |
| exec heavy file | 7.16 / 7.06 / 7.00 / 7.11 |
| exec module rebuild | 11.43 / 10.49 / 10.45 / 10.51 |

The Ray path lands where `runsc do` did (import 9.5 s vs 9.4 s; the other two workloads are within
a few seconds of the table above, with a different root filesystem, so don't read them as a
comparison). Sandbox creation and per-command cost are negligible; the cost is Lean's own startup.
This ran the local `SandboxRuntime`, not the actor path through `ray.init`.

### Image size and startup

- `spike02-gvisor` (Debian, Lean v4.32.0 toolchain, gVisor): 4.63 GB on disk.
- `spike02-baked` (that plus the built physicslib4 tree with Mathlib artifacts, `.lake` 7.4 GB):
  14.8 GB on disk, 3.32 GB compressed. Command: `docker images | grep spike02`.
- Container start on the baked image, `docker run --rm spike02-baked true`, 5 runs: 0.995 (first),
  0.345, 0.323, 0.347, 0.338 s. `runsc do true` inside it: 71 (first), 36, 38, 35, 36 ms.
  Image pulls from a registry were not measured (only local images and a local tar extract).

### Network isolation test

Command: `uv run --with pytest pytest spikes/SPIKE-02/test_network.py -s -m network`; output in
`spikes/SPIKE-02/work/network_test.txt`; 2 passed. `docker/probe.sh` runs ten probes (TCP to an
internet IP, HTTPS by name, DNS lookup, cloud metadata address, an HTTP service on the container's
own private `eth0` address, the Docker gateway and bridge, `10.0.0.1`, `192.168.65.254`, UDP to
1.1.1.1:53, a raw socket).

- Control (no sandbox): internet by IP, by name, DNS and the private-address service were REACHED,
  so the probes can see traffic. The metadata address, gateway, bridge, `10.0.0.1`, UDP and
  `192.168.65.254` were unreachable even in the control, because nothing there listens or answers
  in Docker Desktop; those probes prove nothing on their own. The raw socket was allowed.
- `runsc --network=none`: all ten BLOCKED, and only `lo` is present (`gateway=none`).
- Ray Sandboxes with `network="none"` (run in `ray_sandbox_bench.py`, output in
  `work/ray_bench.jsonl`): all ten BLOCKED as well. The private-service probe there had no
  listener, so its BLOCKED is weaker evidence; the control above covers that case for gVisor.
- Not tested: `network="public"` or `"host"` (which ADR-0005 already forbids for tenant code) and
  a real cluster network with internal services.

### Snapshot and restore

gVisor's `runsc checkpoint` / `runsc restore` work on a warm Lean process. The Ray Sandboxes 2.58
API has none (no snapshot, checkpoint or restore in its source). Test (`docker/ckpt.sh`, three
runs, `work/ckpt.txt`): start `lake env lean --run fixtures/warm.lean` (imports Mathlib, then
increments a counter and appends it to a file every 200 ms) as a detached `runsc run` container with
`--network=none`; checkpoint it; delete it; restore it as a new container.

| step | run 1 / 2 / 3 |
|---|---|
| cold start to first heartbeat (container start, `lake env`, `import Mathlib`) | 11.34 / 11.32 / 11.42 s |
| `runsc checkpoint` | 3.42 / 3.39 / 3.03 s |
| checkpoint image size | 484 / 483 / 483 MB |
| `runsc restore` to next heartbeat | 1.29 / 1.30 / 1.31 s |

The counter continued from where it stopped (in-process state was restored, not re-run). Limits:
same host and same container only, warm page cache, `--overlay2=none` (the root filesystem was not
part of the checkpoint), no KVM platform, and no cross-host restore.

### macOS: native vs `srt` (5 repetitions each, all exit 0)

`srt` is `@anthropic-ai/sandbox-runtime` 0.0.77 as installed by npm (Node v20.20.2), which
uses `sandbox-exec` (Seatbelt). Settings: `spikes/SPIKE-02/srt-settings.json` (no allowed
domains, writes limited to the project and temp, `~/.ssh`, `~/.aws`, `~/.config/gh`, `~/.gnupg`
unreadable). Commands: `source ~/.nvm/nvm.sh; nvm use 20; python3 spikes/SPIKE-02/mac_bench.py 5`.
Data is `work/results-mac.jsonl`. `time -l` runs outside the sandbox (it fails on `sysctl` inside),
so max RSS is the largest process in the tree; for `srt` that includes its own Node process.
The native tree is `work/physicslib4-mac` (own clone, `lake build` on macOS).

| workload | backend | wall s median | wall s min-max | max RSS MB |
|---|---|---|---|---|
| startup | native | 0.004 | 0.004-0.005 | 2 |
| startup | srt | 0.103 | 0.103-0.107 | 59 |
| import | native | 4.554 | 4.508-4.571 | 5225 |
| import | srt | 4.749 | 4.686-4.794 | 5224 |
| heavy | native | 5.727 | 5.574-5.893 | 1277 |
| heavy | srt | 5.713 | 5.658-5.826 | 1277 |
| build | native | 8.232 | 8.114-8.435 | 2783 |
| build | srt | 8.359 | 8.246-8.616 | 2788 |

Overhead of `srt` is about 0.1 s of startup and 0-4% on the workloads. Behavior check (one run):
inside `srt`, `curl https://github.com` failed (`CONNECT tunnel failed, response 403`: `srt` sends
network through a filtering proxy, so an allowlist is the mechanism and the empty list denies
everything), `ls ~/.ssh` gave `Operation not permitted`, `touch ~/outside` gave `Operation not
permitted`, and a write inside the project worked. An earlier `srt` run counted `rc=1` because
`time -l` was inside the sandbox; those data were discarded and the harness fixed.

### Warm-start recommendation

Per-session sandbox with one long-lived Lean process, and, where the backend supports it, start
that process from a pristine snapshot.

- A sandbox costs about 0.1 s to create and 7 ms per command (Ray Sandboxes) or 43 ms per
  `runsc do`, so creating one per session is cheap. What costs is Lean starting: about 9.5 s of
  `import Mathlib` under gVisor. That cost is per process, so it must be paid once per session
  by keeping the process alive, not once per command.
- Restoring a snapshot of a warm `import Mathlib` process cut the start to about 1.3 s (from
  about 11 s) for a 483 MB image. It fits ADR-0008 only if the snapshot comes from a process that
  ran nothing but platform imports, and each restore serves one session (ADR-0018 draft).
- Ray Sandboxes 2.58 does not offer it, so a snapshot backend means wrapping `runsc` directly
  behind `SandboxRunner` or requesting the feature.
- Do not use a per-command sandbox: 9.5 s of import per Lean call is the number to avoid.

### Rerunning on a Linux host with KVM

Everything is scripted: build `docker/Dockerfile.gvisor`, run `docker/prep.sh`, then `bench.sh`,
`docker/ckpt.sh` (both take `PLATFORM=kvm` as an environment variable) and `test_network.py` on the target host, and add a cross-host restore. Keep the same
workloads so the tables compare.

## Implications for ADRs

- **ADR-0005 (accepted): can be accepted as written.** Ray Sandboxes ran Lean and Mathlib
  workloads with `network="none"` and blocked every probe, so INV-0005-2 held in the test. The
  "budget SPIKE-02 sets" in its `revisit_when` is not set by measurement alone: the overhead is
  1.7-3.9x here, and the owner set the budget at 2.0x (module rebuild), 2.0x (heavy Mathlib file) and 4.0x
  (`import Mathlib`), which the measurements meet (1.7x, 1.98x, 3.9x); see ADR-0018. Ray Sandboxes is confirmed alpha with no snapshot API.
- **ADR-0008 (proposed): can be accepted as written, with one clarification.** Nothing measured
  conflicts with it. Restoring a pristine snapshot needs to be stated as consistent with
  INV-0008-6; that is in draft ADR-0018 rather than an amendment. The local profile is workable:
  `srt` costs about 0.1 s and 0-4% and enforced the no-network, confined-write and
  denied-credential policy of INV-0008-9 in one test. `local-sandbox-default` can stay "on".
  Not measured: the hostile-tenant cases, KVM-platform overhead and shared-cluster behavior.
- **New decision needed: ADR-0018 (proposed)**, sandbox warm start with per-session sandboxes and
  pristine snapshots, with the owner's overhead budget and open questions `snapshot-through-ray` and
  `snapshot-portability`.
