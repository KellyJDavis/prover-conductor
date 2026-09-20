---
name: spike
description: Run a time-boxed spike from docs/spikes to its exit criteria and record the results.
disable-model-invocation: true
argument-hint: <SPIKE-NN>
---

Run spike $ARGUMENTS. Spikes run one at a time.

1. Check that no other spike is in progress: run `git fetch -q`, then
   `git branch -r --no-merged origin/main --list 'origin/spike/*'`. If it lists any branch other
   than `origin/spike/$ARGUMENTS`, stop and tell the human.
2. Read `docs/spikes/$ARGUMENTS-*.md` and every ADR listed under `informs`.
3. Restate the question, method, exit criteria and time box, and ask the human to confirm or
   adjust them before starting.
4. Set up the branch. In the main checkout, run `git switch main && git pull`, then
   `git switch -c spike/$ARGUMENTS` (or `git switch spike/$ARGUMENTS` when resuming). In a session
   started with `claude --worktree`, the worktree is already on a fresh `worktree-<name>` branch:
   rename it with `git branch -m spike/$ARGUMENTS` instead, and run `uv sync` first.
5. Keep everything under `spikes/$ARGUMENTS/`: code, scripts and small fixtures. Put clones of
   third-party repositories, builds and downloads under `spikes/$ARGUMENTS/work/`, which git
   ignores. Install Python dependencies with `uv run --with <package>` or an environment inside
   that directory; never edit `pyproject.toml` or `uv.lock`. Change nothing under `src/` or
   `lean/`, and nothing else outside `spikes/$ARGUMENTS/`, this spike's file and new files in
   `docs/specs/`, unless the exit criteria name the path.
6. Record results in the spike file's Results section as they arrive: commands, versions,
   measurements and failures. Every measurement includes the command that produced it.
7. When the exit criteria are met or the time box expires, fill in "Implications for ADRs": for
   each ADR, whether it can be accepted as written, needs an amendment, or needs a new decision.
   Draft amendments as new proposed ADRs following `docs/adr/README.md`, numbered with
   `scripts/next_adr_number.py`.
8. Run the CI steps from CLAUDE.md, push the branch, and open a pull request. Then stop: do not
   change any ADR's status, and do not start another spike.
