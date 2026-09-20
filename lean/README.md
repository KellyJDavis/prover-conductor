# lean/

Home of `ConductorTools`, the Lean helper that reports facts about a project's declarations:
existence, elaborated-statement and definition-closure hashes, axioms, `sorryAx` reachability, and
the project-local constants a proof uses. It does not exist yet. SPIKE-05 prototypes it under
`spikes/SPIKE-05/`, SPIKE-03 prototypes the hash under `spikes/SPIKE-03/`, and build step 2 moves
both here, with tests.

Constraints (ADR-0002, ADR-0003, ADR-0009, ADR-0010):

- depends on Lean core only, so it can load any supported project's environment;
- builds on every toolchain in the support window, checked by a CI matrix;
- emits versioned JSON on stdout, specified in `docs/specs/lean-facts.md`;
- never enables execution of the inspected project's `initialize` blocks.
