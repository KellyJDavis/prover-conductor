---
id: SPIKE-03
title: Statement-hash definition and stability
informs: [ADR-0010]
status: done
---

## Question

What exactly should a lock hash cover, so that benign edits leave it unchanged and meaning-changing
edits change it? Choices include binder names, universe parameter names, instance-implicit
arguments, and where the closure of project-local definitions stops.

## Why it matters

Intent locks are the defense against quietly weakened statements. A hash that is too sensitive
makes every refactor a re-approval; one that is too coarse lets meaning change unnoticed.

## Method

1. Prototype the hash in a scratch Lean package under `spikes/SPIKE-03/` (with the `lean-helper`
   subagent). It stays there: build step 2 moves it into `lean/ConductorTools`, together with
   SPIKE-05's helper.
2. Build a fixture project with pairs of edits. Benign: renaming a bound variable, reformatting,
   reordering unrelated declarations, changing a proof. Meaning-changing: weakening a hypothesis,
   changing a definition in the closure, adding a local instance, shadowing notation.
3. Write the cases as tests marked `lean`, under `spikes/SPIKE-03/`.

## Exit criteria

- A written hash specification in `docs/specs/statement-hash.md`.
- The fixture suite under `spikes/SPIKE-03/`, with at least ten benign and ten meaning-changing
  cases (adjust at start), behaves as specified; the command that runs it is recorded in Results.

## Time box

Five working days, confirmed at start (2026-09-21). Exit criteria met within the first session.

## Results

Environment: macOS (Darwin 25.5.0, M2), Lean v4.33.1 via elan, Lean-core-only package (no Mathlib)
except where noted. The prototype is `spikes/SPIKE-03/hash/` (executable `stmthash`, hand-written
SHA-256 because Lean core has none); cases are in `spikes/SPIKE-03/cases.py`; tests in
`spikes/SPIKE-03/test_statement_hash.py`. The specification is `docs/specs/statement-hash.md`.

Commands and measurements:

- `uv run pytest -m lean spikes/SPIKE-03 -q`: 66 passed, 1 skipped in about 50 s (re-run by me
  after the subagent's run; the skip is the Mathlib test).
- `SPIKE03_MATHLIB=/Users/kdavis/Code/KellyJDavis/mathlib4-aqft uv run pytest -m lean spikes/SPIKE-03 -q`:
  67 passed in about 62 s (subagent's run, not repeated by me). That checkout is a built Mathlib on
  toolchain v4.22.0-rc4; the test rebuilds the tool under it and checks three declarations, each
  benign and meaning-changing. Mathlib constants appear as external references.
- All 60 cases run by hand (subagent's run, not part of the suite) against v4.22.0-rc4,
  v4.29.0-rc6 and v4.35.0-rc1, rebuilding the tool each time: identical outcomes. The one
  portability fix was `String.take`, whose return type changed between versions.
- Clean tool build about 8 s; each case about 0.7 s (two compiles, two tool runs).
- `uv run pytest`, `ruff check`, `ruff format --check` and `pyright` were clean after the spike
  files were added (full CI run recorded below).

Cases (60, counted from `cases.py`): 24 benign (b01-b23 plus b08b) hash equal; 23
meaning-changing (m01-m22 plus m11b) hash differently; 3 design cases (d01-d03) and 10 extras
(x01-x10) behave as decided, except x04 and x05, which are known gaps of the ideal behavior (x04
expects "same" but differs; x05 expects "differ" but the external body change is invisible). The
suite marks them as gaps so they are pinned, not hidden. Every other case behaved as specified.

Design outcomes: see the specification. Notable choices: renaming a local constant is meaningful
(d01), renaming the locked theorem is not (d02), all binder infos are hashed (d03 shows the
opt-out), universe names are canonicalized by declaration-list position (x09), proofs are erased
everywhere, attributes are not hashed (b19, x10).

Findings:

1. Reordering two anonymous instances of one class changes the hash (x04): generated names follow
   declaration order and local constants are referenced by name.
2. A changed value of an external (Mathlib or core) definition is invisible to the hash and to the
   external type hash (x05). Only the environment pin catches it.
3. The elaborated-term hash is over-sensitive to semantically equal rewrites (x01-x03). Safe, but
   costs re-approvals.
4. Attribute changes (`irreducible`, `simp`, instance priority) are not detected. Deliberate.
5. `importModules (loadExts := true)` throws on v4.33.1 unless initializers are enabled; the tool
   uses `loadExts := false` and still reads structure info, class status and matcher info. No
   positive control showed that an `initialize` block would run under the other setting, so the
   guard test is a non-regression check only. Safety of hashing tenant code outside a sandbox is
   not established.
6. Not covered: Mathlib run on v4.33.1 (only the local v4.22.0-rc4 checkout), cost on large
   Mathlib definitions (`Meta.isProof` runs on every node), macro-scoped names, mutual and nested
   inductives beyond light coverage, `where` and `let rec` auxiliaries.

## Follow-up results (2026-09-21)

Both open questions of ADR-0019 were tried after the PR merged. Branch `spike/SPIKE-03-followup`.

**External definition values.** Sample: 16 realistic statements (`ext_sample.lean`, Mathlib
`import Mathlib`, one project-local def). Two built Mathlib revisions on disk: v4.22.0-rc4
(mathlib4-aqft, 252457cd1f, Aug 2025) and v4.30.0 (physicslib4's Mathlib, c5ea00351c, May 2026), a
nine-month gap, larger than a typical bump. Commands, from `spikes/SPIKE-03/`:
`uv run python ext_values.py old <mathlib4-aqft>`, `uv run python ext_values.py new <physicslib4>/.lake/packages/mathlib <physicslib4>/.lake/packages`,
then `uv run python ext_compare.py` and `uv run python ext_shallow.py`. Treating all library roots
as local gives the "deep" closure (values of every reachable definition, proofs erased).

- Deep closure size, median over the 16 statements: 996 (old) and 985 (new) constants, max 2342 and
  2327; core included. Mathlib-only (core external): median 637 and 594. One tool run for all 16
  statements including loading Mathlib: about 10 s (old) and 12 s (new); cost is not a blocker.
- Invalidation across the two revisions: deep 16 of 16 statements, mathlib-only 16 of 16. In the deep run,
  10 to 589 closure entries changed per statement and 46 to 459 were added or removed. These are
  upper bounds on meaningful change (auto-generated instance names and refactors count).
- Current design (external types only, Mathlib external, `ext_shallow.py`): 10 of 16 lock hashes
  unchanged, 6 changed. The 6 changed because the elaborated statement itself differs, through
  instance-path constants that exist in one revision only (for example `Monoid.toNatPow`,
  `PseudoMetricSpace.toUniformSpace`). External type hashes changed for a constant present in both revisions in only one statement (s16). So the shallow hash already flags upgrades that changed how statements
  elaborate, which is what ADR-0010 wants an approver to see.
- Untried: hashing only externals mentioned directly (value one level deep), or a curated list of
  meaning-bearing definitions.

**Load safety.** `spikes/SPIKE-03/test_init_probe.py` (4 cases, `uv run pytest -m lean
spikes/SPIKE-03/test_init_probe.py`, 4 passed on v4.33.1). A module with
`initialize IO.FS.writeFile ...`: compiling it does not run the block. Importing it runs the block
only with `enableInitializersExecution` and `loadExts := true` (positive control); with initializers
enabled and `loadExts := false`, or with the tool's configuration (neither), it does not run;
`loadExts := true` without enabling throws. Not tested: hostile `.olean` files (Lean does not
validate them; treated as out of scope by requiring platform-compiled oleans), other Lean versions.

## Implications for ADRs

- **ADR-0010**: cannot be accepted as written for `hash-definition`; ADR-0019 (proposed) records
  the answer as a new decision, and ADR-0010 stays proposed until the owner decides. The
  `comparator-scale` and `witness-policy` questions are untouched by this spike. INV-0010-1 (a
  change to a locked statement or its closure invalidates the lock) is consistent with the
  prototype except for external definition values (finding 2) and attributes (finding 4); the
  ADR's wording "definitions in its closure" should say project-local, which ADR-0019 states.
- **ADR-0019** (new, proposed): hash definition, the local-closure boundary and specification
  versioning. Both questions it left open were answered by the follow-up: do not hash external
  values, and load with initializers off from platform-compiled oleans. ADR-0019 is updated to say
  so and adds INV-0019-4.
- **ADR-0005 / ADR-0008**: no change. Loading is inert for `initialize`, but a hostile `.olean`
  is untested, so the sandbox rule stands.
- **ADR-0009**: environment upgrades depend on the fingerprint pin to catch changed external
  values, so the fingerprint must cover Mathlib's revision.
