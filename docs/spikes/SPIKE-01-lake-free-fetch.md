---
id: SPIKE-01
title: Lake-free fetch and the source of Mathlib artifacts
informs: [ADR-0008, ADR-0009]
status: open
---

## Question

Can every dependency of a supported project be fetched from `lake-manifest.json` alone, with
plain git at pinned revisions, so that Lake never runs with network access? Where should Mathlib
build artifacts come from: Mathlib's upstream cache, or platform builds per Mathlib commit, and
at what cost?

## Why it matters

Resolving a Lake workspace elaborates `lakefile.lean`, and packages can declare `post_update`
hooks; Mathlib's uses one to sync the toolchain and fetch its cache. Running Lake in a networked
stage hands user code a connection (ADR-0008).

## Method

1. Corpus: physicslib4, plus the public projects listed in leanblueprint's README that use a
   supported toolchain (ADR-0003).
2. For each project, fetch with a manifest-only fetcher (git at each package's `rev`, no Lake).
   Then, with networking disabled, place Mathlib artifacts and run `lake build`.
3. Classify every failure: manifest out of sync with the lakefile, missing package, dependence on
   a `post_update` hook, other.
4. For two Mathlib commits, measure fetching upstream artifacts against building Mathlib from
   source on a platform builder.
5. Write a unit test showing that the fetcher refuses loopback, private, link-local and cloud
   metadata addresses.

## Exit criteria

- A table of projects and outcomes with every failure classified.
- A recommendation for the Mathlib artifact source, with measured costs.
- The address-refusal test passes.

## Time box

Five working days, from 2026-09-20 (confirmed by the owner at spike start).

## Results

### Setup (2026-09-20)

- Branch `spike/SPIKE-01`. Host: Apple M2 Max, 12 CPUs, 16 GB given to Docker (Darwin 25.5.0), Docker 29.2.1, no Linux/KVM host.
- Isolation for the "networking disabled" stage: Docker `--network none`. This is **not gVisor**
  (ADR-0005/0008), so it approximates INV-0008-1 but is weaker evidence. Build times reflect this
  machine, not a platform builder.
- Corpus source: projects in leanblueprint's README, mapped from github.io URLs to `owner/repo`,
  plus physicslib4 (https://github.com/physicslib/physicslib4). Probe: `spikes/SPIKE-01/corpus_probe.py`
  (`uv run python spikes/SPIKE-01/corpus_probe.py`, run 2026-09-20).
- Support window used: official `leanprover/lean4` releases and release candidates from v4.24.0
  (2025-10-14) onward. The exact window is configuration (ADR-0003); this is my reading of
  "roughly the last year".
- Probe result: 27 candidates in window, 11 excluded.
  - No `lean-toolchain` at top level: leanprover-community/liquid, b-mehta/unit-fractions.
  - Older than the window: remydegenne/testing-lower-bounds (v4.13.0-rc3), leanprover-community/con-nf
    (v4.21.0-rc3), pitmonticone/FLT3 (v4.7.0-rc2), Command-Master/lean-bourgain (v4.7.0),
    ivan-sergeyev/seymour (v4.18.0), leastauthority/STIR (v4.19.0-rc3), ahhwuhu/zeta_3_irrational
    (v4.18.0), b-mehta/ABC-Exceptions (v4.21.0-rc3), fpvandoorn/BonnAnalysis (v4.10.0-rc1).
  - The probe checks the top-level lakefile only; per-dependency lakefiles (INV-0003-2) are checked
    during fetching.
  - Repository names for fpvandoorn/carleson, fpvandoorn/BonnAnalysis and mo271/FormalBook were
    inferred from website domains, not stated in the README.
- Scope (owner's choice): tier 1 = manifest-only fetch and classification for all 27; tier 2 =
  offline `lake build` for about 8 projects. Mathlib cost measurement uses two recent Mathlib rev
  pins taken from corpus projects.

### Tier 1: manifest-only fetch and classification (27 projects)

Commands (run 2026-09-20, from the repository root):

```
uv run python spikes/SPIKE-01/corpus_probe.py > spikes/SPIKE-01/probe.jsonl
cd spikes/SPIKE-01 && uv run --no-project python tier1.py     # writes work/tier1.jsonl
uv run --no-project python tier1_table.py                      # renders the table below
```

`tier1.py` shallow-clones each project's default branch, then `fetcher.py` runs `git init`,
`git fetch --depth 1 <url> <rev>` and a detached checkout for every git package in
`lake-manifest.json`, with no Lake anywhere. Path packages are accepted only if they lie inside
the project tree. Toolchain: git 2.51.0, Python 3.12.11, macOS host. Projects are at their default
branch HEAD as of 2026-09-20, so revisions drift after that date.

| Project | Toolchain | Pkgs | Fetched with plain git | Classification |
|---|---|---|---|---|
| AlexKontorovich/PrimeNumberTheoremAnd | v4.32.2 | 13 | yes | none |
| FredRaj3/SemicircleLaw | v4.24.0 | 15 | yes | other: in-repo `path` package HammerCore inside fetched package Hammer; no network needed once Hammer is checked out |
| ImperialCollegeLondon/FLT | v4.34.0 | 10 | yes | none |
| RemyDegenne/CLT | v4.29.0-rc3 | 10 | yes | none |
| RemyDegenne/brownian-motion | v4.33.0-rc1 | 12 | yes | none |
| Verified-zkEVM/ArkLib | v4.33.1 | 20 | yes | none |
| YaelDillies/ChandraFurstLipton | v4.35.0-rc2 | 10 | yes | none |
| YaelDillies/LeanAPAP | v4.35.0-rc2 | 11 | yes | none |
| YaelDillies/LeanCamCombi | v4.35.0-rc2 | 9 | yes | none |
| YaelDillies/Toric | v4.35.0-rc2 | 10 | yes | none |
| acmepjz/lean-iwasawa | v4.33.0-rc1 | 10 | yes | none |
| bergschaf/Localic-Caratheodory-Extensions | v4.28.0-rc1 | 9 | yes | none |
| bergschaf/lean-banach-tarski | v4.25.0-rc2 | 14 | yes | none |
| emilyriehl/infinity-cosmos | v4.34.0-rc1 | 11 | yes | none |
| fpvandoorn/carleson | v4.34.0-rc2 | 10 | yes | none |
| ilpreterosso/LEANearized-RadiiPolynomial | v4.28.0-rc1 | 11 | no | other: absolute local `path` dependency (/Users/... on the author's machine); unfetchable, must fail onboarding |
| kkytola/ExtremeValueProject | v4.32.0-rc1 | 15 | yes | none |
| leanprover-community/flt-regular | v4.34.0-rc2 | 9 | yes | none |
| leanprover-community/sphere-eversion | v4.34.0-rc2 | 10 | yes | none |
| mo271/FormalBook | v4.34.0-rc2 | 10 | yes | none |
| oliver-butterley/SpectralThm | v4.33.0-rc1 | 10 | yes | none |
| physicslib/physicslib4 | v4.32.0 | 15 | yes | none |
| sinhp/groupoid_model_in_lean4 | v4.25.0-rc2 | 11 | yes | other: conditional require of doc-gen4 (`meta if get_config? env = some "dev"`); manifest correctly omits it, so the naive lakefile/manifest compare is a false positive |
| teorth/equational_theories | v4.29.1 | 10 | yes | none |
| teorth/expdb | v4.32.0 | 10 | yes | none |
| teorth/pfr | v4.35.0-rc2 | 11 | yes | none |
| thefundamentaltheor3m/Sphere-Packing-Lean | v4.32.0 | 10 | yes | none |

Aggregate (from `work/tier1.jsonl`): 304 git packages fetched across the 27 projects (the 26 that
fetched completely, plus the git packages of RadiiPolynomial); 20 distinct Mathlib revisions across
the 27 projects; every fetched dependency has exactly one of `lakefile.lean` and `lakefile.toml`
(INV-0003-2 holds for every package fetched); `fetcher.py` refuses any non-https URL, and none was
refused in this corpus.

Failure classes (the required classification):

| Class | Count | Projects |
|---|---|---|
| Manifest out of sync with lakefile | 0 real | one false positive, see next row |
| Conditional `require` (config-dependent), not a real mismatch | 1 | groupoid_model_in_lean4 |
| Missing package | 0 | |
| Dependence on a `post_update` hook to obtain the package itself | 0 | |
| Other: in-repo `path` package (fixed in the fetcher) | 1 | SemicircleLaw |
| Other: absolute local `path` dependency (unfetchable) | 1 | LEANearized-RadiiPolynomial |

`post_update` hooks exist in exactly two packages of the corpus: Mathlib (all 27 projects), whose
hook runs `lake exe cache get` and syncs the toolchain, and `auto` (SemicircleLaw, through
LeanHammer), whose hook downloads a Zipperposition executable. Both run on `lake update`, which the
manifest-only fetcher never invokes.

Limits of tier 1: it shows every package can be materialized from the manifest with git. It does
not show that `lake build` accepts that layout offline, and its lakefile/manifest comparison covers
direct requires by name only, not revisions or options. Tier 2 tests both.

### Tier 2: offline `lake build` (Docker `--network none`, not gVisor)

Image: `spikes/SPIKE-01/docker/Dockerfile` (debian bookworm-slim, elan, `leanprover/lean4:v4.32.0`,
linux/arm64 on an M2 host; Docker 29.2.1, 12 CPUs, 16 GB). Built with network in 2m19s, which
stands in for the platform's toolchain-mirror step.

**physicslib4 (v4.32.0, Mathlib 81a5d25):**

1. Fetch: `uv run --no-project python spikes/SPIKE-01/fetcher.py spikes/SPIKE-01/work/physicslib4`
   -> 15 packages, no failures, about 20 s, 183 MB.
2. Artifact placement, **with network**: `spikes/SPIKE-01/docker/cache_get.sh work/physicslib4
   v4.32.0` runs `lake exe cache get` (with `MATHLIB_NO_CACHE_ON_UPDATE=1`) in a networked
   container. Result: 8639 files from `lakecache.blob.core.windows.net/mathlib4-master`, all
   decompressed, 120 s wall, `.lake` 7.2 GB.
3. Offline build: `spikes/SPIKE-01/docker/offline_build.sh work/physicslib4 v4.32.0`. The script
   first checks that `curl https://github.com` fails inside the container (it did:
   "github.com unreachable"), then runs `lake build`. Result: `Build completed successfully
   (3176 jobs)`, exit 0, 207 s wall. Lake 5.0.0-src+8c9756b, Lean 4.32.0 aarch64-linux.

Caveat that bears on the spike's question: step 2 ran **Lake with network access** (`lake exe cache
get` elaborates the project's and Mathlib's lakefiles and builds Mathlib's `cache` executable).
The fetch and the offline build are Lake-free of network, but artifact placement as done here is
not. Whether the cache executable can be built offline and then run alone with network is
tested next.

**physicslib4, Lake never networked (fresh clone `work/physicslib4-nolake`):**

1. `git clone --depth 1` of physicslib4, then `fetcher.py`: 15 of 15 packages.
2. Build only Mathlib's `cache` executable, offline: `spikes/SPIKE-01/docker/run_in.sh none
   work/physicslib4-nolake v4.32.0 'lake build cache'` -> `Build completed successfully (27
   jobs)`, 32 s wall.
3. Run that binary with network, with `lake` (elan shim and toolchain binary) replaced by a canary
   script that records any call: `.lake/packages/mathlib/.lake/build/bin/cache get`. First attempt
   failed with `unknown module prefix 'Mathlib'`: the binary needs Lean's search paths, which
   `lake env` normally provides. Second attempt with `LEAN_SRC_PATH` (project plus every package
   directory, 16 entries) and `LEAN_PATH` (each package's `.lake/build/lib/lean`) set by hand:
   8639 files downloaded and decompressed, exit 0, about 68 s wall (`time` around the container
   run). The canary file was never created, so Lake was not called.
4. Offline build of that tree: `docker/offline_build.sh work/physicslib4-nolake v4.32.0` ->
   network check passed, `Build completed successfully (3176 jobs)`, 216 s wall.

So for physicslib4 the whole pipeline (git fetch, offline build of `cache`, networked run of the
`cache` binary alone, offline `lake build`) works without Lake ever having network access. Two
things it relied on: the `cache` binary is built from the tenant-pinned Mathlib checkout, and the
search-path variables are computed by us rather than by Lake.

### Tier 2 results: 8 projects, Lake never had network access

Pipeline per project (`spikes/SPIKE-01/docker/tier2.sh`, driven by `tier2_all.sh`; run 2026-09-20
on fresh trees produced by `tier1.py`, image `spike01-lean:multi` with the seven toolchains):

1. Offline (`--network none`): `lake build cache` builds Mathlib's `cache` executable.
2. With network: the `cache` binary alone runs `cache get`, with `LEAN_SRC_PATH` and `LEAN_PATH` set
   by hand and `lake` replaced by a canary that records every call. A call of the form
   `build <pkg>:release` is answered with success, because the platform already placed that
   archive (see the ProofWidgets note below); any other call fails and is reported as `OTHER`.
3. Offline (`--network none`, curl to github.com must fail first): `lake build`, capped at 2700 s.

| Project | Toolchain | Mathlib rev | cache exe build | `cache get` | offline `lake build` | Lake calls seen | `.lake` |
|---|---|---|---|---|---|---|---|
| physicslib4 | v4.32.0 | 81a5d257c | 32 s | about 68 s | 216 s | none | 6.9 GB |
| lean-banach-tarski | v4.25.0-rc2 | 0c8813a61 | 20 s | 57 s | 34 s | `:release` only (shimmed) | 5.6 GB |
| groupoid_model_in_lean4 | v4.25.0-rc2 | 32bd6c7c8 | 12 s | 52 s | 170 s | `:release` only (shimmed) | 5.7 GB |
| ExtremeValueProject | v4.32.0-rc1 | 1b0782d81 | 25 s | 67 s | 107 s | none | 6.9 GB |
| CLT | v4.29.0-rc3 | bf8875c7d | 16 s | 71 s | 37 s | `:release` only (shimmed) | 6.3 GB |
| PrimeNumberTheoremAnd | v4.32.2 | 905b95818 | 30 s | 94 s | 1191 s | none | 8.5 GB |
| carleson | v4.34.0-rc2 | b63493a47 | 26 s | 65 s | 269 s | none | 7.3 GB |
| LeanAPAP | v4.35.0-rc2 | 065356127 | 35 s | 67 s | 109 s | none | 7.2 GB |

All eight built offline with exit code 0. The physicslib4 row comes from the earlier Lake-free run
(`work/physicslib4-nolake`, timed with `time` around each container run, not `tier2.sh`). Offline
build times cover the project's own modules only, since Mathlib's artifacts were placed. Project
revisions are default-branch HEAD on 2026-09-20.

**A failure found and fixed on the way (classification: cloud release, "other").** The first
attempt on lean-banach-tarski (Mathlib `0c8813a61`) failed. The `cache` binary of that Mathlib
calls `lake build proofwidgets:release` (canary: `lake called: -v build proofwidgets:release`) and
then aborted with `Failed to fetch ProofWidgets cloud release: lake failed with error code 1`, so
no Mathlib artifacts were placed. The offline build then compiled Mathlib from source and stopped
at `proofwidgets/widgetJsAll`, which needs npm. Cause: ProofWidgets (older revisions) declares
`preferReleaseBuild := true`, `buildArchive? := "ProofWidgets4.tar.gz"` and
`releaseRepo := "https://github.com/leanprover-community/ProofWidgets4"`. Lake fetches that
archive from GitHub releases; `lake-manifest.json` does not record it. Fix: `fetcher.py` now
finds an explicit `releaseRepo` and `buildArchive` in a fetched package's lakefile, takes the tag
that points at the pinned revision from `git ls-remote --tags` (v0.0.77 for that revision),
downloads `<releaseRepo>/releases/download/<tag>/<archive>` with plain HTTPS and unpacks it into
the package's `.lake/build`. With that in place, Lake never needed the network. The earlier
"7419 of 7424 jobs in 22 min 47 s" figure from the failed run is **withdrawn**: that build never
completed, and its job total was still growing.

Cloud-release use across the corpus (grep of the fetched lakefiles for `preferReleaseBuild`,
`buildArchive` and `releaseRepo`, then reading each hit): 8 of 27 projects have a package that
sets `preferReleaseBuild := true`.

- ProofWidgets, explicit repo and archive: SemicircleLaw (v4.24.0), CLT (v4.29.0-rc3),
  Localic-Caratheodory-Extensions (v4.28.0-rc1), lean-banach-tarski (v4.25.0-rc2),
  LEANearized-RadiiPolynomial (v4.28.0-rc1), groupoid_model_in_lean4 (v4.25.0-rc2) and
  equational_theories (v4.29.1). Newer ProofWidgets revisions do not use it.
- CompPoly (ArkLib, v4.33.1): explicit repo and `CompPoly-oleans.tar.gz`, which is prebuilt oleans
  published by a third-party repository.
- auto (SemicircleLaw): `preferReleaseBuild := true` with no explicit repo or archive, so Lake's
  defaults apply. The fetcher does not handle this case, and it was not tested.
- Duper sets `preferReleaseBuild := false` and does not count.

Not tested in tier 2: SemicircleLaw, Localic-Caratheodory-Extensions, equational_theories and
ArkLib were never built offline, so whether the release fetch is enough for them is unmeasured.
Tier 2 covers 8 of 27 projects, chosen to span toolchains and both lakefile flavours.

### Mathlib artifact source: measured cost

Clean from-source builds: fresh `git clone --depth 1`, `fetcher.py`, no cache, `lake build
Mathlib` in a `--network none` container, nothing else running (`docker/from_source.sh` aborts if
any other container is running). Command: `docker/from_source_all.sh`, results in
`work/fromsource.results`. Host: Apple M2 Max, Docker with 12 CPUs and 16 GB.

| Mathlib rev | Toolchain | Upstream cache (`cache` exe build + `cache get`) | From source (`lake build Mathlib`) | Ratio |
|---|---|---|---|---|
| 81a5d257c (physicslib4) | v4.32.0 | 32 s + about 68 s = about 100 s | 11110 s (3 h 05 min), `.lake` 10 GB | about 111x |
| 0c8813a61 (lean-banach-tarski) | v4.25.0-rc2 | 20 s + 57 s = 77 s | 11933 s (3 h 19 min), `.lake` 6.9 GB | about 155x |

Notes on the measurements:

- Cache times for 81a5d257c come from the Lake-free run (`time` around the container runs); those
  for 0c8813a61 come from `tier2.sh`. Both exclude building the toolchain image.
- `docker stats --no-stream` sampled the running build at 304% and 245% CPU (about 2.5 to 3 of the
  12 cores) and 3.2 to 4.0 GB of memory. I do not know whether Docker Desktop, the virtual file
  system under the bind mount, or Lake's job graph limited parallelism. A builder on Linux with
  many cores would probably be faster; the ratio on this hardware is an upper bound of unknown
  size, not a prediction.
- An earlier, uncontrolled from-source build of 0c8813a61 (banach-tarski, after the ProofWidgets
  release was placed) took 10634 s, 11% below the clean 11933 s for the same revision. It was not
  run in isolation and is kept only as a sanity check.
- Both from-source builds exited 0 with `--network none` and needed no cache.
- Across the corpus, 20 distinct Mathlib revisions serve 27 projects (most revisions serve one
  project). Building each from source at about 3 h would cost about 60 build-hours on this
  hardware; upstream artifacts cost about 100 s each plus about 7 GB of disk.

### Mathlib artifact source: what the upstream cache does and does not guarantee

Read from `Cache/SECURITY.md`, `Cache/Infra.lean` and `Cache/Requests.lean` in the fetched
Mathlib (rev 81a5d257c); I did not audit the cache infrastructure itself.

- Mathlib's own statement: "The infrastructure cannot validate artifact content; verifying
  integrity would mean re-running the build." The only check on a downloaded file that I found in
  the `cache` executable is the format magic and the 8-byte hash header of the `.ltar`
  (`readLtarHash`). I found no signature or content check.
- Trust comes from containers. `mathlib4-master` is written only by mathlib4 `master`/`staging`
  CI. `forks` (PR builds), `nightly-testing` and `pr-toolchain-tests` are lower trust. `legacy`
  (the bare `mathlib4` container) is described in the source as a read-only mirror of
  master-built artifacts.
- The default read chain for repository `leanprover-community/mathlib4` is `[master, legacy]`.
  For any other repository (a fork) it is `[master, forks, legacy]`, which admits PR-built
  artifacts. Every `cache get` in tier 2 printed two attempts, from `mathlib4-master` and then
  from `mathlib4` (legacy), and none from `forks`.
- The chain can be overridden by environment (`MATHLIB_CACHE_FROM`, `MATHLIB_CACHE_GET_URL`), and
  the executable takes its repository identity from the checkout's git remote.
- The `cache` executable is built from the pinned Mathlib checkout and then run with network
  access. If the manifest's `mathlib` entry were a fork, or a commit reachable only through a PR
  ref, that would be tenant-influenced code running with network. In this corpus every `mathlib`
  entry I inspected (`work/*/lake-manifest.json`, which includes duplicate trees of physicslib4
  made for the experiments) points at `https://github.com/leanprover-community/mathlib4`, with or
  without a `.git` suffix, so the fork case did not occur; the platform would still have to check.
- Of the 20 distinct revisions, 17 are ancestors of upstream `master`
  (`gh api repos/leanprover-community/mathlib4/compare/<rev>...master`, status `ahead`). The other
  3 (0df444a36, 5e932f97d, 905b95818) are commits `chore: bump toolchain to v4.33.1`, `v4.29.1` and
  `v4.32.2`, each carrying that tag upstream and diverging from master by 1 to 2 commits. So
  "ancestor of upstream master, or an upstream release tag" accepts all 20; "ancestor of master"
  alone would reject 3.

### Recommendation: source of Mathlib artifacts

Use the upstream cache, placed by Mathlib's own `cache` executable, for Mathlib commits that are
ancestors of upstream `master` or carry an upstream release tag (all 20 revisions in this corpus
qualify). Build the `cache` executable offline from the pinned upstream source, run it alone with
network access against the `master` and `legacy` containers only, and let the platform compute the
Lean search paths. Build Mathlib from source on a platform builder for any other commit, or
refuse the project.

| Measure | Upstream cache | From source |
|---|---|---|
| Wall time, 81a5d257c (v4.32.0) | about 100 s | 11110 s |
| Wall time, 0c8813a61 (v4.25.0-rc2) | 77 s | 11933 s |
| Disk after the step | 5.6 to 8.5 GB per project `.lake` in tier 2 | 6.9 to 10 GB |
| 20 distinct revisions of the corpus | about 30 min in total | about 60 build-hours |

What supports it: the Lake-free pipeline built all 8 tier 2 projects offline, and Mathlib's own
trust model puts artifacts written only by mathlib4 `master`/`staging` CI in `master`.

What does not: Mathlib states that the cache cannot validate artifact content, so this trusts
Mathlib's CI, which INV-0008-5 as written does not allow; that is the owner's decision
(`upstream-cache-trust` in ADR-0017). Nothing was run under gVisor. Only 8 of 27 projects were
built offline, and none of the four other projects with cloud releases (SemicircleLaw,
Localic-Caratheodory, equational_theories, ArkLib). The from-source builds used about 2.5 to 3
cores, so a builder with more cores may be faster.

## Implications for ADRs

- **ADR-0008 (proposed): needs an amendment and one decision.**
  - `fetch-without-lake`: yes for git packages (26 of 27 projects, 304 packages). No for
    "manifest alone": 8 of 27 projects depend on Lake cloud releases the manifest does not record
    (ADR-0017, INV-0017-3).
  - INV-0008-1 held throughout the pipeline (Lake never had network access) under Docker
    `--network none`; gVisor was not tested.
  - INV-0008-7 should extend to redirects: the release download redirects to a second host
    (ADR-0017, INV-0017-1).
  - `mathlib-artifact-trust`: INV-0008-5 as written forbids using upstream artifacts. Accepting
    upstream `master`/`legacy` as a second source needs the owner's decision (ADR-0017,
    `upstream-cache-trust`).
- **ADR-0009 (proposed): needs an amendment.**
  - `mathlib-artifact-source`: upstream cache, under the conditions above (ADR-0017).
  - "Fetched from the manifest with plain git at pinned revisions" must add cloud-release
    archives, and the fingerprint must cover their digests, since tags and assets are mutable
    (ADR-0017, INV-0017-6).
  - `fingerprint-lakefile-options` and `helper-version-cost` are not addressed by this spike.
- **ADR-0003 (accepted): can stay as written.** INV-0003-2 (exactly one lakefile per package) held
  for every package fetched. Onboarding also needs a rule that it lacks, refusing absolute `path`
  dependencies (1 of 27 projects); that is a new decision, recorded in ADR-0017 (INV-0017-2), not
  an edit to ADR-0003. Of the 38 candidates from the README plus physicslib4, 11 fall outside the
  window (9 on toolchains older than v4.24.0, 2 with no `lean-toolchain`).
- **New: ADR-0017 (proposed)** carries these amendments, with four open questions for the owner
  (`upstream-cache-trust`, `cloud-release-policy`, `release-defaults`, `source-build-capacity`).
  Acceptance would require the owner to decide those, and an enforcing test for each invariant
  before code lands in `envs/` (CLAUDE.md, enforcement scopes).

Other findings for later work, not tied to one ADR: `post_update` hooks exist in Mathlib and in
`auto`, whose hook downloads a Zipperposition binary; the manifest-only fetcher never runs them.
The manifest can omit conditional requires (`meta if get_config? env = some "dev"`).
