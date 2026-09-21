# Architecture decision records

Each decision lives in one file, `NNNN-<slug>.md`, with YAML frontmatter that scripts read and
prose that people and Claude Code read. Start from `template.md`. ADR-0000 sets out this process.

## Lifecycle

- **proposed**: the current direction, not yet binding. Anyone, Claude Code included, may draft or
  revise a proposed ADR.
- **accepted**: binding. Only the owner accepts an ADR. Accepted ADRs are never edited; a change is
  a new ADR that supersedes the old one, after which the owner marks the old one `superseded` and
  sets `superseded_by`.
- **superseded** and **rejected**: kept for history; the rule generator ignores them.

`open_questions` lists what must be answered before acceptance. `settled_by` lists the spikes whose
results accept or amend the ADR.

## Numbering

Sessions may draft ADRs on different branches, so the next number in your checkout may already be
taken elsewhere. Run `git fetch`, then `uv run python scripts/next_adr_number.py`. It prints the
next number that is free on every branch, and any number that different branches already use for
different ADRs. If a merge still collides, the branch that merges second renumbers its ADR: file
name, `id`, invariant IDs, index row, and every reference.

## Invariants and their enforcement

An ADR states its invariants; `enforcement.yaml` in this directory records what enforces each one.
Unlike an accepted ADR, the enforcement file can be edited at any time, by anyone, Claude Code
included; CODEOWNERS routes changes to the owner. ADRs themselves carry no enforcement fields.

    INV-0001-1:
      enforced_by:
        - import-linter:gate-sole-github-writer
    INV-0002-2:
      enforced_by: []
      scope:
        - "src/prover_conductor/agents/decompose/**"

`scripts/check_invariants.py` verifies each reference:

| Form | What the checker verifies |
|---|---|
| `test:<path>::<test_name>` | the test exists and its file mentions the invariant ID |
| `import-linter:<contract id>` | the contract exists in `pyproject.toml` and its name mentions the invariant ID |
| `hook:<path>` | the hook script exists and `.claude/settings.json` registers it |
| `ci:<workflow path>#<step id>` | the workflow has that step and mentions the invariant ID |
| `codeowners:<pattern>` | `.github/CODEOWNERS` has an entry for the pattern |

An invariant without enforcement is debt, reported as a warning. It becomes an error only when its
ADR is accepted, its entry declares a `scope`, and real code exists in that scope. Markdown,
`py.typed`, `.gitkeep` and docstring-only Python modules don't count as code. Add a scope when a
task starts implementing an invariant: CI then holds the task until the enforcing test exists.

The checker also fails when an ADR carries an `enforced_by` field, when code, tests, hooks,
workflows or `pyproject.toml` mention an invariant ID that no ADR defines, when an enforcement
entry names an undefined invariant, when a `settled_by` spike has no file in `docs/spikes/`, and
when the index below lacks an ADR or shows the wrong status.

## Generated Claude Code rules

`scripts/gen_adr_rules.py` writes `.claude/rules/adr/NNNN-<slug>.md` for every proposed or
accepted ADR, with the ADR's `applies_to` globs as the rule's `paths:`. Claude Code loads a rule
when it reads a matching file, so an ADR's decision and invariants appear exactly where they
apply. CI fails if the generated rules are stale. Rules don't include enforcement details, so
editing the enforcement file never makes them stale.

## Commands

    uv run python scripts/check_invariants.py        # validate ADRs and enforcement
    uv run python scripts/gen_adr_rules.py           # regenerate the rules after editing an ADR
    uv run python scripts/gen_adr_rules.py --check   # verify the rules are current
    uv run python scripts/next_adr_number.py         # next ADR number free on every branch

## Index

| ID | Status | Title |
|---|---|---|
| ADR-0000 | accepted | Record decisions as ADRs with enforced invariants |
| ADR-0001 | accepted | The stochastic layer proposes; the deterministic layer decides |
| ADR-0002 | accepted | Agents hand off top-level declarations, never goals |
| ADR-0003 | accepted | Supported Lean versions, project formats and onboarding |
| ADR-0004 | accepted | Tenancy and authorization follow GitHub |
| ADR-0005 | accepted | Ray is the compute substrate |
| ADR-0006 | accepted | Names and license |
| ADR-0007 | accepted | Repository and development conventions |
| ADR-0008 | proposed | Threat model and sandbox profiles |
| ADR-0009 | proposed | Environment fingerprints and Lake-free fetch |
| ADR-0010 | proposed | Intent locks, obligations and certification |
| ADR-0011 | proposed | Gate profiles with Mathlib style as the floor |
| ADR-0012 | proposed | Blueprint status is derived, never claimed |
| ADR-0013 | proposed | Model access through capability routing and bring-your-own-key |
| ADR-0014 | proposed | Data governance and training eligibility |
| ADR-0015 | proposed | Agents are data; tools are code |
| ADR-0016 | proposed | Traces are the training-data format |
| ADR-0017 | proposed | Fetch and Mathlib artifact placement without a networked Lake |
| ADR-0018 | proposed | Sandbox warm start with per-session sandboxes and pristine snapshots |
