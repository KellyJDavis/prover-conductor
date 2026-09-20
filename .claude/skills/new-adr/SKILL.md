---
name: new-adr
description: Draft a new architecture decision record in docs/adr with status proposed, following the template, with checkable invariants.
disable-model-invocation: true
argument-hint: <short title of the decision>
---

Draft an ADR for: $ARGUMENTS

1. Read `docs/adr/README.md` and `docs/adr/template.md`. Run `git fetch`, then
   `uv run python scripts/next_adr_number.py`, and take the number it prints.
2. Search the existing ADRs for overlap. If the new decision changes an accepted ADR, the new ADR
   supersedes it: list the old one in `depends_on` and explain the change under Context. Never
   edit the accepted ADR.
3. Create `docs/adr/NNNN-<slug>.md` from the template with `status: proposed` and today's date.
4. Write each invariant as a checkable statement, with no `enforced_by` field. Where enforcement
   already exists (a test, import-linter contract, hook, CI step or CODEOWNERS entry), record it
   in `docs/adr/enforcement.yaml`.
5. Set `applies_to` to the narrowest globs that cover the governed code.
6. Add a row to the index in `docs/adr/README.md`.
7. Run `uv run python scripts/gen_adr_rules.py` and `uv run python scripts/check_invariants.py`.
8. Stop and summarize for the human: the decision, its open questions, and what acceptance would
   require. Never set the status to accepted.
