# prover-conductor

Conducts agents that prove results in Lean: from informal theorems or blueprint nodes to formal
statements, proofs and reviewed commits in GitHub repositories that use the
[leanblueprint](https://github.com/PatrickMassot/leanblueprint) layout.

**Status:** repository skeleton. The architecture and decisions are written down; implementation
starts with the spikes in `docs/spikes/`.

| | |
|---|---|
| Distribution | `prover-conductor` |
| Import package | `prover_conductor` |
| Command | `conductor` |
| License | Apache-2.0 |

## Quick start

```bash
uv sync
uv run conductor --version
uv run conductor doctor
```

## Documentation

- `docs/architecture.md`: the design and the reasoning behind it
- `docs/adr/`: architecture decision records with machine-checked invariants
- `docs/spikes/`: time-boxed experiments that settle open decisions
- `CLAUDE.md`: instructions for Claude Code

## Developing with Claude Code

This repository is set up to be developed with Claude Code. In the first session, run
`/verify-skeleton` before any feature work. Decisions stay with the owner: Claude Code drafts ADRs
as proposals, hooks stop it from editing accepted ones, and changes under `docs/adr/`, `.claude/`
and `.github/` need the code owner's review.

## License

Apache-2.0; see `LICENSE`.
