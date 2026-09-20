---
name: verify-skeleton
description: First-session checklist that confirms this repository's Claude Code setup works before any feature work. Run once after the skeleton is committed.
disable-model-invocation: true
---

Verify the skeleton. Report every item as PASS or FAIL with evidence: command output, or what the
human confirmed. Fix environment-specific failures on a branch named `verify-skeleton` and open a
pull request. Do not change any ADR's status.

1. Files: run `git ls-files | diff - .claude/skills/verify-skeleton/files.txt`. No output means
   every file of the skeleton is committed, hidden ones included. Any difference is a FAIL.
2. Tools: run `uv --version` and `git --version`. Run `uv sync --locked`, then
   `uv run conductor --version` and `uv run conductor doctor`.
3. CI parity: run each step of `.github/workflows/ci.yml` locally, in order, and confirm that all
   pass.
4. Hooks in the main checkout:
   - Use the Edit tool to append a blank line to
     `docs/adr/0001-stochastic-proposes-deterministic-decides.md`. Expect the PreToolUse hook to
     block it.
   - Use the Edit tool on `.claude/rules/adr/0000-record-decisions-as-adrs.md`. Expect a block.
   - Ask the human to run `/hooks` and confirm that the PreToolUse, PostToolUse and Stop hooks
     from `.claude/settings.json` are listed.
5. Hooks in a worktree: run `git worktree add .claude/worktrees/verify -b verify-hooks-scratch`.
   Use the Edit tool to append a blank line to
   `.claude/worktrees/verify/docs/adr/0001-stochastic-proposes-deterministic-decides.md`. Expect a
   block. Then run `git worktree remove --force .claude/worktrees/verify` and
   `git branch -D verify-hooks-scratch`.
6. Instructions: ask the human to run `/context` and confirm that CLAUDE.md appears under Memory
   files.
7. Path-scoped rules: read `src/prover_conductor/gate/__init__.py`, then state whether the
   generated rules for ADR-0001, ADR-0004, ADR-0007, ADR-0008, ADR-0010 and ADR-0011 are now in
   your context.
8. MCP: ask the human to run `/mcp` and confirm that the `lean-lsp` server connects. The
   repository has no Lean project until build step 2; that is expected.
9. GitHub settings, done by the human: protect `main` so that it requires a pull request, the
   `checks` job of the `ci` workflow, and review from code owners. Turn on "Automatically delete
   head branches" in the repository's general settings, so merged spike branches disappear.
   Confirm that `.github/CODEOWNERS` names the right account.
10. Summarize what passed, what failed, and what you changed.
