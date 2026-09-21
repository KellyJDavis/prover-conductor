---
id: ADR-0017
title: Fetch and Mathlib artifact placement without a networked Lake
status: proposed
date: 2026-09-21
summary: >-
  Platform code fetches a project's git packages from lake-manifest.json, plus explicit cloud-release
  archives at the tag of the pinned revision, and places Mathlib artifacts by running Mathlib's own
  cache executable, built offline, only for upstream Mathlib commits and only against the master
  and legacy containers. Lake never has network access. Any other Mathlib is built from source on
  a platform builder or rejected.
applies_to:
  - "src/prover_conductor/envs/**"
  - "src/prover_conductor/sandbox/**"
depends_on:
  - ADR-0003
  - ADR-0008
  - ADR-0009
open_questions:
  - upstream-cache-trust
  - cloud-release-policy
  - release-defaults
  - source-build-capacity
settled_by:
  - SPIKE-01
superseded_by: null
invariants:
  - id: INV-0017-1
    text: >-
      Every request the fetcher makes, including each redirect target, passes the address rules of
      INV-0008-7 before it is sent.
  - id: INV-0017-2
    text: >-
      A path dependency is accepted only when it resolves inside the project's own tree once the
      git packages are fetched; an absolute path, or a path that leaves the tree, fails onboarding.
  - id: INV-0017-3
    text: >-
      A cloud-release archive is fetched only for a package whose lakefile sets preferReleaseBuild
      to true and names both releaseRepo and buildArchive, at a tag that points at the pinned
      revision, and is unpacked without writing outside the package's build directory.
  - id: INV-0017-4
    text: >-
      The Mathlib cache executable runs with network access only when the pinned mathlib package
      is the upstream repository at a commit that is an ancestor of upstream master or carries an
      upstream release tag, and it reads only the master and legacy containers.
  - id: INV-0017-5
    text: >-
      No Lake process runs while the network is reachable, including during artifact placement;
      the platform computes the Lean search paths and answers the release-fetch calls itself.
  - id: INV-0017-6
    text: >-
      The environment fingerprint covers the digest of every cloud-release archive placed in the
      environment.
revisit_when: >-
  Lake gains an offline, hook-free way to materialize a workspace and its releases from the
  manifest, Mathlib signs or content-verifies cache artifacts, or a supported project needs a
  fetch mechanism this decision does not cover.
---

## Context

SPIKE-01 asked whether every dependency can be fetched from `lake-manifest.json` alone so that Lake
never runs networked, and where Mathlib artifacts should come from. Its results are in
`docs/spikes/SPIKE-01-lake-free-fetch.md`; the figures below are from that file. They were
measured on an Apple M2 Max with Docker `--network none`, not gVisor, on 27 in-window projects
from leanblueprint's README plus physicslib4, at default-branch revisions of 2026-09-20.

- The git fetch works: 26 of 27 projects fetched completely with plain git at pinned revisions
  (304 packages). The failure was a dependency by absolute local path
  (`/Users/.../leancert`). Every fetched package has exactly one lakefile.
- The manifest is not enough for 8 of 27 projects. Older ProofWidgets revisions, and CompPoly,
  set `preferReleaseBuild := true` with a `releaseRepo` and `buildArchive`; Lake downloads that
  archive from GitHub releases, and the manifest does not record it. Without it, Mathlib's cache
  executable calls `lake build proofwidgets:release`, and an offline build falls back to npm.
  One further package (`auto`) sets `preferReleaseBuild := true` with no explicit repository or
  archive; that case is untested. `post_update` hooks exist in Mathlib and `auto` (which
  downloads a binary); the manifest-only fetcher never runs them.
- Placing upstream artifacts, then building offline, worked for all 8 projects built (physicslib4
  and 7 others, toolchains v4.25.0-rc2 to v4.35.0-rc2): 12 to 35 s to build Mathlib's `cache`
  executable offline, 52 to 94 s to run it with network, and an offline `lake build` that took 34 s
  to 1191 s. Lake was never called, except for `build <pkg>:release` calls in the three older
  projects, which the platform answered after placing the archive itself.
- Mathlib from source took 11110 s (3 h 05 min) and 11933 s (3 h 19 min) for two revisions, against
  about 100 s and 77 s through the upstream cache (about 111 and 155 times), with the build using
  about 2.5 to 3 of the 12 cores. The 20 distinct Mathlib revisions of the 27 projects would cost
  about 60 build-hours from source on that hardware.
- Mathlib's own `Cache/SECURITY.md` says the cache infrastructure cannot validate artifact
  content. Trust comes from container: `master` is written only by mathlib4 `master` and `staging`
  CI, `legacy` is described as a read-only mirror of master-built artifacts, and forks read
  `forks` as well. All 20 revisions were either ancestors of upstream `master` (17) or upstream
  release-tag commits (3).

This bears on ADR-0008: INV-0008-1 (Lake never runs in a sandbox with network access), INV-0008-5
(shared caches accept only platform-built artifacts) and INV-0008-7 (the fetcher refuses bad
addresses). It settles the open questions `fetch-without-lake` and `mathlib-artifact-trust` in
part, and ADR-0009's `mathlib-artifact-source`. ADR-0003 (accepted) is not changed; this ADR adds
an onboarding rule that it does not contain.

## Decision

- Fetching is platform code. It materializes the manifest's git packages with `git fetch
  --depth 1` at the pinned revision. A `path` package is accepted only if it lies inside the
  project tree (for instance a package inside another fetched package).
- For a package whose lakefile explicitly asks for a cloud release, the fetcher takes the tag
  that points at the pinned revision from `git ls-remote --tags`, downloads
  `<releaseRepo>/releases/download/<tag>/<buildArchive>` over https and unpacks it into the
  package's `.lake/build`, refusing any archive member that escapes that directory.
- Every request, including each redirect hop (GitHub serves release assets from a second host),
  passes the address checks of INV-0008-7.
- Mathlib artifacts are placed in three steps that keep Lake offline: build Mathlib's `cache`
  executable offline; run that binary alone with network access, with the Lean search paths set by
  the platform and `lake` unavailable except for answering `build <pkg>:release`; then build
  offline. The binary runs with network only for upstream Mathlib at an upstream `master`
  ancestor or release tag, restricted to the `master` and `legacy` containers.
- A Mathlib that fails that test is built from source on a platform builder, or the project is
  refused. Nothing built in a tenant sandbox enters a shared cache (INV-0008-5).
- The fingerprint of ADR-0009 also covers the digest of each placed release archive, because a
  release tag and its assets are mutable.

## Consequences

- Fetching Mathlib costs about 100 s and 7 GB of disk instead of about 3 hours of build, so a
  fingerprint for a new Mathlib commit is cheap to create.
- The platform depends on Mathlib's CI for the integrity of `master` and `legacy` artifacts; it
  does not verify them. Under INV-0008-5 as written, this needs the owner's decision.
- Running the `cache` executable with network is running Mathlib-authored code with network. It is
  built from the pinned upstream source, so the test in the decision is what keeps tenant code
  out of that step.
- Environment builders gain a version-dependent step: the older Mathlib `cache` executable calls
  Lake for the ProofWidgets release; newer ones did not in this corpus.
- Onboarding refuses a project with an absolute `path` dependency (1 of 27 here).
- The platform needs its own builder capacity for Mathlib commits outside the test.

## Open questions

- `upstream-cache-trust`: accept `master` and `legacy` artifacts of upstream Mathlib as a second
  source next to platform builds, given that content is not verified? Proposed: yes, for the
  commits and containers above. Amends the wording of INV-0008-5 if accepted.
- `cloud-release-policy`: which release repositories are accepted? The corpus has ProofWidgets4
  (leanprover-community) and CompPoly (prebuilt oleans from a third-party repository).
  Proposed: an allowlist; for a package that is not on it, ignore the archive and build from
  source, which this spike did not test.
- `release-defaults`: how to treat `preferReleaseBuild := true` without an explicit repository and
  archive (`auto`), where Lake's defaults apply. Not handled or tested.
- `source-build-capacity`: what a platform builder needs to build Mathlib from source in
  reasonable time; the spike's figures come from a Docker host that used 2.5 to 3 cores.

## Alternatives considered

- `lake exe cache get` with network: works, but Lake then elaborates the project's and Mathlib's
  lakefiles with network access, which INV-0008-1 forbids.
- Building every Mathlib from source: no trust in Mathlib's cache, but about 3 hours per commit
  on the spike's hardware and 20 distinct commits for 27 projects.
- Reading the `forks` container as well: rejected, since those artifacts come from PR builds that
  run untrusted code.
