---
id: ADR-0011
title: Gate profiles with Mathlib style as the floor
status: proposed
date: 2026-09-19
summary: >-
  Each repository has a gate profile. Mathlib's style linters are a floor that no profile can
  disable; Mathlib policy checks are optional per repository, and prover-conductor replaces
  bundled linters it disables with its own checks for the style parts. The build tolerates only the
  sorry warning on locked, statement-only declarations.
applies_to:
  - "src/prover_conductor/gate/**"
  - "policies/**"
depends_on:
  - ADR-0001
  - ADR-0010
open_questions:
  - linter-partition
  - ratchet-default
settled_by:
  - SPIKE-08
superseded_by: null
invariants:
  - id: INV-0011-1
    text: >-
      The build fails on any error or warning except the sorry warning on a locked,
      statement-only declaration.
  - id: INV-0011-2
    text: >-
      No repository profile can disable a linter in the style floor.
  - id: INV-0011-3
    text: >-
      Disabling a bundled linter, such as the header linter, enables prover-conductor's
      replacement check for its style parts.
  - id: INV-0011-4
    text: >-
      Axioms of changed declarations and their dependents stay within propext, Classical.choice,
      Quot.sound and the repository's allowlist; sorryAx enters only through locked statement-only
      dependencies.
  - id: INV-0011-5
    text: >-
      The pre-elaboration scan runs before anything is elaborated and rejects new axioms outside
      the allowlist, sorry or admit outside statement-only nodes, unsafe, implemented_by, extern,
      native_decide, debug options and code-executing commands.
revisit_when: >-
  Mathlib splits its standard linter set into style and policy sets itself.
---

## Context

R15 asks for Mathlib's coding standards, but some linters in Mathlib's standard set encode Mathlib
policy rather than style. The header linter requires Mathlib's exact Apache-2.0 license line, and
it also checks the copyright block, imports and module docstring as one bundle, while tenants use
other licenses. Linter options switch whole linters, not parts. Blueprint projects legitimately
carry sorried statements.

## Decision

- Each repository has a gate profile. The floor, which no profile can disable, is Mathlib's style
  linters; Mathlib policy checks are optional. Since Mathlib defines one standard set,
  prover-conductor writes down its own partition into style and policy.
- A repository that disables a bundled linter gets prover-conductor's replacement for its style
  parts; for the header linter, the copyright block and module docstring, checked against the
  repository's own license.
- R15 then reads: nothing is committed that fails the repository's profile.
- Gate stages, stopping at the first failure:

| Stage | Check |
|---|---|
| Patch policy | allowed paths only; toolchain, manifest and lakefile untouched unless the task is an environment change |
| Pre-elaboration scan | parse-only scan for new axioms outside the allowlist, `sorry` or `admit` outside statement-only nodes, `unsafe`, `implemented_by`, `extern`, `native_decide`, `debug.*` options, code-executing commands |
| Build | `lake build` with `weak.linter.mathlibStandardSet` adjusted by the profile; every error or warning fails, except the `sorry` warning on a locked, statement-only declaration |
| Lint | `lake lint` (Batteries `runLinter`), `lake exe lint-style`, `lake exe mk_all --check` |
| Axiom audit | axioms of changed declarations and their dependents within the standard three plus the allowlist; `sorryAx` only through locked statement-only dependencies |
| Intent locks | ADR-0010 |
| Blueprint | `leanblueprint checkdecls`, the blueprint builds, derived status matches the TeX, `\uses` covers actual dependencies (ADR-0012) |

- Onboarding an existing repository: clean up first, or use a ratchet. Under the ratchet,
  diagnostics in declarations a patch touches fail as usual, recorded legacy diagnostics elsewhere
  are tolerated, and the record only shrinks. The ratchet satisfies R15 for everything
  prover-conductor writes, not for the repository as a whole.

## Open questions

- `linter-partition`: which linters in Mathlib's standard set are style and which are policy.
- `ratchet-default`: clean-up or ratchet as the default for existing repositories. The
  physicslib4 backtest (build step 3) informs this.

## Alternatives considered

- Enforce Mathlib's full standard set everywhere: forces Mathlib's license line on every tenant.
- Let repositories choose their own linters freely: drops R15's guarantee.
