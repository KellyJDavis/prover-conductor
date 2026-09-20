"""The only client of GitHub write APIs: pushes, pull requests, merges and check runs.

Only `prover_conductor.gate` may import this module (INV-0001-1, enforced by the import-linter
contract `gate-sole-github-writer`). Every write re-checks the acting user's permission on the
repository at the time of the write (ADR-0004). No implementation yet.
"""
