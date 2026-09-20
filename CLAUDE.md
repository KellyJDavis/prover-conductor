# prover-conductor

prover-conductor conducts agents that prove results in Lean: from an informal theorem or a
blueprint node, through formal statements and proofs, to gated, reviewed commits in GitHub
repositories that use the leanblueprint layout. It succeeds Gödel's Poetry.

- Distribution `prover-conductor`, import package `prover_conductor`, CLI `conductor`. Apache-2.0.
- Status: skeleton. No production code yet; the first work items are the spikes in `docs/spikes/`.
- Design: `docs/architecture.md`. It is not loaded automatically; read it before design work.
  Decisions: `docs/adr/`.

## Commands

- Set up: `uv sync`
- Everything CI runs, in order:
  `uv run python scripts/check_invariants.py && uv run python scripts/gen_adr_rules.py --check && uv run ruff check . && uv run ruff format --check . && uv run pyright && uv run lint-imports && uv run pytest`
- Fast tests: `uv run pytest` (skips the `lean` and `network` markers). Lean tests: `uv run pytest -m lean`.
- After editing any ADR: `uv run python scripts/gen_adr_rules.py`
- CLI: `uv run conductor --version`, `uv run conductor doctor`

## Where things are

- `src/prover_conductor/<area>/`: one subpackage per architectural area. Each `__init__.py`
  docstring says what belongs there and which ADRs govern it.
- `docs/architecture.md`, `docs/adr/`, `docs/spikes/`, `docs/specs/`
- `scripts/`: ADR tooling. `tests/meta/`: tests of repository conventions and tooling.
- `agent-library/`: prover-conductor's own agent specs (data). Not to be confused with
  `.claude/agents/` (Claude Code subagents for developing this repository) or
  `src/prover_conductor/agents/` (the agent runtime).
- `policies/`: autonomy presets, gate profiles and routing policies (data).
- `lean/`: home of the Lean helper `ConductorTools`. SPIKE-05 prototypes it under
  `spikes/SPIKE-05/`, and build step 2 moves it here.
- `spikes/`: experiment code, one directory per spike, created by the spikes themselves.

## How decisions work

- ADRs in `docs/adr/` are the source of truth for decisions (ADR-0000 describes the process).
  Their YAML frontmatter lists `applies_to` globs and invariants.
- `.claude/rules/adr/` is generated from the ADRs and loads when you read files an ADR governs.
  Never edit it by hand.
- Accepted ADRs are immutable, and only the owner changes an ADR's status. To change a decision,
  draft a new proposed ADR that supersedes the old one (see `docs/adr/README.md`). Hooks block
  edits to accepted ADRs and status changes.
- Proposed ADRs are the current direction but not binding. Ask before implementing anything that
  answers one of their open questions.
- What enforces each invariant is recorded in `docs/adr/enforcement.yaml`, which you may edit.
  When you write a test that enforces an invariant, name the invariant ID in the test's docstring
  and add the reference there. ADRs never carry enforcement fields.
- Before implementing code that an accepted invariant governs, add a `scope` for it in the
  enforcement file: the narrowest globs where that code will live. CI then fails until the
  enforcing test exists. Unenforced invariants without a scope are only warnings.
- Before drafting an ADR, run `git fetch`, then take its number from
  `uv run python scripts/next_adr_number.py`.

## Invariants that apply everywhere

1. Stochastic proposes, deterministic decides: agents and models never write to GitHub; only
   `prover_conductor.gate` may import `prover_conductor.vcs.github_write` (ADR-0001).
2. The deterministic layer (`core`, `vcs`, `gate`, `lean`, `sandbox`, `envs`, `blueprint`,
   `search`, `traces`, `data`) never imports `agents` or `models` (ADR-0001).
3. Agents hand off top-level declarations, never goals inside another proof; nothing depends on
   the Kimina Lean Server's AST extension (ADR-0002).
4. Tenant-controlled or model-written Lean code runs only through the sandbox interface, never in
   a Ray worker process (ADR-0005).
5. Verification verdicts come from platform binaries, never from a tenant's toolchain (ADR-0008,
   proposed).

## Conventions

- Python 3.12+, uv, ruff, pyright (strict for `src/`), pytest, import-linter (ADR-0007).
- Python files are ASCII-only.
- Mark Lean-dependent tests `@pytest.mark.lean` and network tests `@pytest.mark.network`.
- Work on a branch and open a pull request; never push to `main`.
- Work in one session at a time, in the main checkout. If sessions ever run in parallel, each
  needs its own git worktree (`claude --worktree <name>`); run `uv sync` in it first.
- Spikes run one at a time. A spike changes nothing outside `spikes/<SPIKE-NN>/`, its own spike
  file and new files in `docs/specs/`, unless its exit criteria name another path.
- State a task's exit command before starting, and run it before saying the task is done.
- Record spike results in the spike's file under `docs/spikes/`, not only in chat.
- Keep this file under 200 lines; put details in docs, skills or path-scoped rules.

## Claude Code setup

- Skills: `/verify-skeleton` (first-session checklist), `/new-adr <title>`, `/spike <SPIKE-NN>`.
- Subagents: `adr-auditor` (read-only review of a change against its governing ADRs) and
  `lean-helper` (Lean work under `lean/`).
- MCP: `lean-lsp` (lean-lsp-mcp) in `.mcp.json`.
- Hooks in `.claude/settings.json`: block edits to accepted ADRs, status changes and generated
  rules; format edited Python files; run the ADR checks when you finish a turn.
