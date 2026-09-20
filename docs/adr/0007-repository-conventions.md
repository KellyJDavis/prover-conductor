---
id: ADR-0007
title: Repository and development conventions
status: accepted
date: 2026-09-19
summary: >-
  One Python distribution with subpackages under src/; Python 3.12+, uv with a committed lock
  file, ruff, pyright (strict for src/), pytest with lean and network markers excluded by default,
  and import-linter for architectural rules. Tasks are GitHub issues with exit commands; work lands
  through pull requests.
applies_to:
  - "pyproject.toml"
  - ".github/**"
  - "tests/**"
  - "src/**"
depends_on: []
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0007-1
    text: >-
      Tests that need Lean carry the lean marker, tests that need network carry the network
      marker, and the default pytest run excludes both.
  - id: INV-0007-2
    text: >-
      Code under src/ passes pyright in strict mode.
  - id: INV-0007-3
    text: >-
      The ruff lint and format checks pass.
  - id: INV-0007-4
    text: >-
      The import-linter contracts pass.
revisit_when: >-
  A part of the system needs an independent release cycle, or the toolchain slows CI enough to
  matter.
---

## Context

The repository is developed largely by Claude Code, so conventions have to be mechanical and
checked rather than remembered.

## Decision

- One Python distribution with subpackages under `src/prover_conductor/`. Split into workspace
  members only when a part needs an independent release.
- Python 3.12+, uv with a committed `uv.lock`, ruff for lint and format, pyright (strict for
  `src/`, standard elsewhere), pytest, and import-linter for architectural rules.
- Tests that need Lean are marked `lean`, tests that need network are marked `network`, and the
  default run excludes both.
- Python files are ASCII-only.
- Tasks are GitHub issues from the templates in `.github/ISSUE_TEMPLATE/`, each naming the ADRs
  involved and an exit command.
- Work happens on branches and lands through pull requests; `main` is protected.

## Consequences

- CI runs the ADR checks, ruff, pyright, import-linter and the default test suite on every pull
  request.
- A session without a Lean toolchain or Mathlib cache can still run the whole default suite.

## Alternatives considered

- A multi-package uv workspace from the start: more configuration before any part needs it.
- mypy instead of pyright: slower, and pyright's strict mode catches more by default.
