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

## Implications for ADRs

- **ADR-0010**: cannot be accepted as written for `hash-definition`; ADR-0019 (proposed) records
  the answer as a new decision, and ADR-0010 stays proposed until the owner decides. The
  `comparator-scale` and `witness-policy` questions are untouched by this spike. INV-0010-1 (a
  change to a locked statement or its closure invalidates the lock) is consistent with the
  prototype except for external definition values (finding 2) and attributes (finding 4); the
  ADR's wording "definitions in its closure" should say project-local, which ADR-0019 states.
- **ADR-0019** (new, proposed): hash definition, the local-closure boundary and specification
  versioning. Two questions stay open in it: `external-definition-values` (needs a measurement of
  how many locks hashing external values would invalidate on a Mathlib bump) and
  `hash-load-safety`.
- **ADR-0005 / ADR-0008**: no change. Hashing tenant code is not shown to be safe outside the
  sandbox, so the sandbox rule stands.
- **ADR-0009**: environment upgrades depend on the fingerprint pin to catch changed external
  values, so the fingerprint must cover Mathlib's revision.
