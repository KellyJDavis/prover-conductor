---
id: ADR-0008
title: Threat model and sandbox profiles
status: proposed
date: 2026-09-19
summary: >-
  Two profiles behind one SandboxRunner. Hosted: tenants are adversaries, building a repository is
  running hostile code, tenant code runs only in gVisor sandboxes without network, verdicts come
  from platform binaries, and shared caches accept only platform-built artifacts. Local: the
  operator is trusted but model output is not; an OS-level sandbox with no network, confined writes
  and denied credential reads is on by default and can be switched off.
applies_to:
  - "src/prover_conductor/sandbox/**"
  - "src/prover_conductor/envs/**"
  - "src/prover_conductor/gate/**"
  - "deploy/**"
depends_on:
  - ADR-0004
  - ADR-0005
open_questions:
  - local-sandbox-default
  - mathlib-artifact-trust
  - fetch-without-lake
settled_by:
  - SPIKE-01
  - SPIKE-02
  - SPIKE-08
superseded_by: null
invariants:
  - id: INV-0008-1
    text: >-
      Lake never runs in a sandbox that has network access.
  - id: INV-0008-2
    text: >-
      Toolchains come only from checksum-verified mirrors of allowlisted official releases.
  - id: INV-0008-3
    text: >-
      Dependency identity is resolved by URL and commit; an attestation calls a dependency upstream
      only when both match the upstream repository.
  - id: INV-0008-4
    text: >-
      Verification verdicts come only from platform binaries, never from a tenant's toolchain.
  - id: INV-0008-5
    text: >-
      Shared caches accept only artifacts built by platform builders from pinned public sources;
      anything produced in a tenant sandbox stays in that tenant's cache.
  - id: INV-0008-6
    text: >-
      A Lean process that elaborated one tenant's code is never reused for another tenant or
      another session.
  - id: INV-0008-7
    text: >-
      The dependency fetcher refuses loopback, private and link-local addresses and cloud metadata
      endpoints.
  - id: INV-0008-8
    text: >-
      On shared model serving, prefix caches are salted per tenant.
  - id: INV-0008-9
    text: >-
      In local mode, unless the operator disables it, model-written code runs in the OS-level
      sandbox with no network, writes limited to the worktree and a scratch directory, and reads of
      credential paths denied.
revisit_when: >-
  A sandbox escape in the chosen substrate, or build overhead beyond the budget SPIKE-02 sets.
---

## Context

On the hosted service, users are potential adversaries, not just models. Before any agent acts,
building a repository runs user-controlled code: Lake elaborates `lakefile.lean`, packages can
declare `post_update` hooks (Mathlib's fetches its build cache that way), and source files can run
`#eval`, `run_cmd` and `initialize`. Locally, the operator trusts their repository, but
model-written code is elaborated before anyone reads it, and what models write can be steered by
papers, search results or dependency docstrings.

## Decision: hosted profile

- Every build and every Lean process that touches tenant or model-written code runs in a gVisor
  sandbox with networking disabled and no credentials (ADR-0005).
- Fetching is platform code, not Lake: dependencies come from `lake-manifest.json` through plain
  git at pinned revisions, and the fetcher refuses loopback, private, link-local and metadata
  addresses. Lake runs only offline (ADR-0009).
- Toolchains come only from checksum-verified mirrors of allowlisted official releases
  (ADR-0003). Dependency identity is resolved by URL and commit.
- Verification verdicts come from platform binaries (lean4export, the replaying kernel,
  Comparator), never from the tenant's toolchain.
- Sharing across tenants:

| Resource | Shared | Rule |
|---|---|---|
| Toolchains | yes | allowlisted official releases from checksum-verified mirrors |
| Base images (toolchain plus upstream dependencies) | yes | built only by platform builders from pinned upstream sources; content-addressed and signed |
| Anything built inside a tenant sandbox | no | tenant-scoped cache, never promoted |
| Warm Lean processes | no | one per session, destroyed afterwards |
| Model prefix caches | salted | per-tenant salt (vLLM `cache_salt`) |
| Search indexes | public libraries only | indexes over private repositories stay tenant-scoped |
| User-registered MCP servers | no | visible only to the registering tenant; responses are untrusted input |
| Traces and knowledge bases | no | per project, encrypted with per-tenant keys |
| Agent library | read-only | agents a tenant defines stay in that tenant |
| Fine-tuned models | only if trained on consented public data | otherwise served only to the tenant whose data trained them |

## Decision: local profile

- The operator is trusted; model output is not.
- Model-written Lean code runs in an OS-level sandbox. Anthropic's sandbox runtime
  (`@anthropic-ai/sandbox-runtime`) is one candidate: it uses sandbox-exec on macOS and bubblewrap
  on Linux, with no container or virtual machine.
- Policy: no network; writes limited to the worktree and a scratch directory; reads of credential
  paths denied, since otherwise a secret can be copied into the worktree and leave in a commit.
- On by default, and the operator can switch it off.

## Consequences

- Repositories whose manifest is out of sync with their lakefile fail onboarding instead of
  triggering a networked Lake run.
- Warm starts come from per-session sandboxes or snapshot and restore, never from reuse
  (SPIKE-02).
- The adversarial suite gains hostile-tenant cases: malicious lakefiles, spoofed toolchains, a
  forked "mathlib", poisoned cache artifacts, exfiltration attempts and resource exhaustion.
- An external security review and an invite-only beta come before public registration.

## Open questions

- `local-sandbox-default`: is the local sandbox on by default? Proposed: yes.
- `mathlib-artifact-trust`: trust Mathlib's upstream build cache, or build Mathlib per commit on
  platform builders? (SPIKE-01)
- `fetch-without-lake`: can every supported project be fetched without running Lake? (SPIKE-01)

## Alternatives considered

- A Linux virtual machine for local mode on macOS: stronger isolation than the operator's trust
  model needs, at a real cost in setup and performance.
- Running Lake with network in a separate sandbox: `post_update` hooks and `lakefile.lean` would
  still run user code with a network connection.
