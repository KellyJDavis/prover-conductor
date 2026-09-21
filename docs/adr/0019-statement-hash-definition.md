---
id: ADR-0019
title: Statement hash covers the elaborated statement and its local closure
status: proposed
date: 2026-09-21
summary: >-
  A lock hash is SHA-256 over the canonically serialized elaborated statement and the closure of
  project-local constants it mentions. Bound-variable, instance-binder and universe-parameter
  names, proofs and attributes are excluded; binder infos, local constant names and definition
  values are included. External definitions are listed by name and type hash, and a changed
  external body is caught by pinning the environment, not by the hash.
applies_to:
  - "src/prover_conductor/gate/**"
  - "src/prover_conductor/blueprint/**"
  - "lean/**"
depends_on:
  - ADR-0010
open_questions:
  - external-definition-values
  - hash-load-safety
settled_by:
  - SPIKE-03
superseded_by: null
invariants:
  - id: INV-0019-1
    text: >-
      A lock hash is unchanged by renaming bound variables, instance-implicit binders or universe
      parameters, by changing any proof, and by changing whitespace, comments, docstrings,
      declaration order or unrelated declarations.
  - id: INV-0019-2
    text: >-
      A lock hash changes when the elaborated statement changes, or when a definition value,
      structure, inductive, instance or local constant name in its project-local closure changes.
  - id: INV-0019-3
    text: >-
      A lock records the hash specification version it was computed under, and the gate rejects a
      comparison across versions.
revisit_when: >-
  Benign refactors, such as reordering anonymous instances, cause re-approvals often enough that
  reviewers stop reading them, or a meaning-changing edit is found that the hash misses.
---

## Context

SPIKE-03 prototyped the hash and ran 60 fixture cases (24 benign, 23 meaning-changing, 3 design and
10 extra) against Lean v4.33.1, with the same results on v4.22.0-rc4, v4.29.0-rc6 and
v4.35.0-rc1. `docs/specs/statement-hash.md` is the specification; this ADR records the decisions
that ADR-0010 left open as `hash-definition`.

## Decision

- The hash is over the elaborated `Expr`, so notation shadowing, local instances, coercions and
  autoImplicit are caught, and formatting, comments and proof changes are not.
- Excluded: bound-variable names, instance-implicit binder names, universe parameter names (by
  position in the declaration's parameter list), `mdata`, proofs (any `Prop`-typed proof term, in
  statements and definition values), attributes, and the locked declaration's own name.
- Included: all four binder infos, local constant names (renaming a definition in the closure
  needs re-approval), definition values, structure fields, constructors and class flags.
- The closure stops at the project boundary: the first module-name component is a configured
  local root. External constants are listed with module, kind and a hash of their type.
- **Provisional:** a changed value of an external definition, for example a Mathlib `def`, is not
  visible in the hash. Environment upgrades already re-hash every lock under ADR-0010 and pin the
  environment fingerprint (ADR-0009); until `external-definition-values` is settled, that pin is
  the only defense, and the upgrade task must show locks whose external references changed
  version.
- The hash loads environments with extensions and initializers off. Whether hashing tenant code
  outside a sandbox is safe is `hash-load-safety`; until settled, ADR-0005's rule applies.

## Consequences

- Sensitivity errs safe: semantically equal rewrites such as `a > b` versus `b < a` need
  re-approval.
- Reordering anonymous instances of one class changes the hash; naming them avoids it.
- The specification is versioned, and a change to it invalidates stored locks.

## Alternatives considered

- Name-independent references to local constants: cannot express recursive and mutual definitions,
  and would hide renames that break blueprint `\lean{}` links.
- Hashing external definition values: could make Mathlib bumps invalidate many locks (unmeasured); not chosen
  without measurement of how many locks it would touch.
- Semantic normalization of statements: unbounded work and its own trust problem.
