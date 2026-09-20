"""The internal git store, worktrees, and the GitHub App client.

`github_write` is the only module that may call GitHub write APIs, and only `gate` may import it
(ADR-0001). Governing ADRs: ADR-0001, ADR-0004. Deterministic layer. No implementation yet.
"""
