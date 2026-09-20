## What changed

## ADRs and invariants

- ADRs affected:
- Invariants added, changed or newly enforced:

## Checks

- [ ] `uv run python scripts/check_invariants.py`
- [ ] `uv run python scripts/gen_adr_rules.py --check`
- [ ] `uv run ruff check . && uv run ruff format --check .`
- [ ] `uv run pyright`
- [ ] `uv run lint-imports`
- [ ] `uv run pytest`
- [ ] No accepted ADR edited; changed decisions are new proposed ADRs
