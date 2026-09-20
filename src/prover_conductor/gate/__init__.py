"""The commit gate: patch policy, pre-elaboration scan, build, lint, axiom audit, intent locks,
blueprint consistency, attestations and the merge queue.

The only package that may import `prover_conductor.vcs.github_write` (INV-0001-1). Governing ADRs:
ADR-0001, ADR-0004, ADR-0008, ADR-0010, ADR-0011. Deterministic layer. No implementation yet.
"""
