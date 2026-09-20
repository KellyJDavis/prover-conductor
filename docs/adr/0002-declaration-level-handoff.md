---
id: ADR-0002
title: Agents hand off top-level declarations, never goals
status: accepted
date: 2026-09-19
summary: >-
  Work that crosses an agent boundary is a top-level Lean declaration. Decomposition is
  lemma-first: children are closed statements whose sufficiency is checked in the pinned
  environment before any child is attempted. Nothing extracts sorried have-statements into
  declarations, and nothing depends on the Kimina Lean Server's AST extension.
applies_to:
  - "src/prover_conductor/agents/**"
  - "src/prover_conductor/lean/**"
  - "src/prover_conductor/blueprint/**"
  - "agent-library/**"
  - "lean/**"
depends_on:
  - ADR-0001
open_questions: []
settled_by: []
superseded_by: null
invariants:
  - id: INV-0002-1
    text: >-
      No component turns a goal inside a declaration's proof into a new declaration by syntactic
      or textual extraction.
  - id: INV-0002-2
    text: >-
      A decomposition is accepted only if each child elaborates on its own, every path from the
      parent's proof to sorryAx passes through a child, the parent's proof uses no project-local
      lemmas beyond its children and declared parents, no child restates the parent or an
      ancestor, and the parent's statement is unchanged.
  - id: INV-0002-3
    text: >-
      Nothing depends on the Kimina Lean Server's AST extension; Kimina, where used, is only a
      checking backend.
  - id: INV-0002-4
    text: >-
      Hypotheses are removed from a child only after it is proved, based on unusedArguments
      output, and the result is verified again.
revisit_when: >-
  A mechanical Expr-level lift proves both faithful and readable enough that restating children
  by model becomes the bottleneck.
---

## Context

Gödel's Poetry decomposes a hard theorem into a proof sketch whose `have` statements are proved
by `sorry`, then extracts those as independent theorems using an AST extension of the Kimina Lean
Server. Extraction is the error-prone step. It fails in two places: re-elaborating a rendered goal
can change coercions, implicit arguments or instances, and pruning context before a proof exists
can silently drop a hypothesis the proof needed.

## Decision

- The unit of handoff between agents is a top-level declaration, never a goal inside another
  declaration's proof. Scratch `sorry`s inside `have`s are fine within one agent's session,
  because that agent fills them in place and the file is compiled whole.
- Decomposition is lemma-first (Goedel-Architect's representation, applied locally). For a node
  N, the decomposer writes new top-level declarations C1...Ck with `sorry` bodies and a proof of N
  that uses them. Before any child is attempted, the Lean helper checks in N's pinned environment
  that each Ci elaborates on its own; every path from N's proof to `sorryAx` passes through some
  Ci; N's proof uses no project-local lemmas beyond the Ci and N's declared parents; no Ci restates
  N or an ancestor (by statement hash); and N's own statement is unchanged.
- Children's proofs fill their own declarations; nothing is spliced back into N.
- Hypotheses a proved child does not need are removed afterwards, from `unusedArguments` output,
  and the result is verified again.
- Recursion is local refinement: only the forfeiting node's subtree is rewritten. It escalates to
  global refinement (the refiner sees the whole working graph) after a depth or budget limit,
  after repeated forfeits with the same diagnosis, or when repairing a negated child would change
  N's statement. If N itself is disproved and locked, the question goes to a human.
- Partial proofs: the agent that wrote one finishes it in place, or the decomposer restates the
  remaining goals as children under the same checks. A mechanical Expr-level lift (abstracting a
  goal over its full local context) may produce a draft of that restatement, never the final
  statement.
- The decomposer runs on a general model. A specialized prover's `have` sketch may be passed to it
  as a hint; renderings are prompts, never ground truth.
- Nothing depends on the Kimina Lean Server's AST extension. Kimina may serve as a checking
  backend.

## Consequences

- A decomposition error costs budget, not correctness: a wrong child surfaces as a negation or a
  forfeit that says the statement is wrong.
- Every child is a real declaration: reusable, promotable to the blueprint, in the form
  whole-proof models expect, and an exact RLVR task.
- The decomposer must write closed statements, which is harder than writing
  `have h : P := by sorry` in context.

## Alternatives considered

- AST or text extraction of `have`s, as in Gödel's Poetry: the failure modes above.
- Solving goals in context, for example through Pantograph: no extraction, but goals are not
  reusable declarations, proofs nest inside one large declaration, and state is tied to a process.
- Expr-level lifting as the primary mechanism: faithful by construction, but unreadable, and names
  are unstable across edits.
