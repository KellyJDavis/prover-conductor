# prover-conductor: architecture

Status: design baseline, 2026-09-19. This document explains the system as a whole and the reasoning
behind it. Binding decisions are the ADRs in `docs/adr/`. Where this document and an ADR disagree,
the ADR wins and this document gets corrected.

prover-conductor succeeds Gödel's Poetry (arXiv:2512.14252); its planning name was Tomita–Takesaki's
Orchestra. Distribution `prover-conductor`, import package `prover_conductor`, command `conductor`
(ADR-0006).

## 1. Purpose and requirements

prover-conductor conducts agents that prove results in Lean. It takes an informal theorem or a
blueprint node, produces faithful formal statements and proofs, and lands them as gated, reviewed
commits in GitHub repositories that use the leanblueprint layout.

| | Requirement |
|---|---|
| R1 | Functionality similar to Goedel-Architect, Numina's Fuse, TeXRA, and the multi-agent workflow of Lu, Tjoa and Cirac |
| R2 | Use local or remote LLMs |
| R3 | Use local or remote services, such as a Lean MCP server |
| R4 | Not wed to any LLM or model family; swap models as needed |
| R5 | A fixed initial set of agents (orchestrator, prover, theorem search, proof simplifier, blueprint maintainer, proof reviewer), plus agents the orchestrator creates when needed |
| R6 | Command-line, desktop and web clients |
| R7 | Not bound to a particular Lean or Mathlib version |
| R8 | Levels of automation, from "prove this informal theorem, blueprint included" to "prove this blueprint node and let me approve before commit" |
| R9 | Conversation with the orchestrator, for commands and for discussing hard or unclear issues |
| R10 | GitHub repositories in the leanblueprint layout |
| R11 | Inspection of running processes, including subagent output |
| R12 | Inference results that are easy to use for training new models |
| R13 | Model serving as part of the system (vLLM, Ollama and similar) |
| R14 | Lean services (Kimina Lean Server, LeanExplore and similar) integrated in the cluster or external |
| R15 | Never commit code with errors, lint failures, or deviations from the repository's coding standards, with Mathlib's style as the floor (ADR-0011) |

Multi-user means a hosted service open to arbitrary registered users. The same software also runs
locally for one person, and on a self-hosted Ray cluster.

### What we take from prior systems

- **Goedel-Architect** (arXiv:2606.06468) keeps one global dependency graph and rewrites it between
  proving passes. Lemmas are proved in parallel, each seeing only its declared parents, and a
  failure returns either a Lean-verified negation or a structured forfeit (diagnosis, attempts,
  proposed fix or decomposition). It validates graph edges with LeanArchitect and notes that naive
  recursive decomposition loops on dead ends. We take the graph, forfeits and negations, and global
  refinement.
- **Numina's Fuse** is a GitHub-connected web application: branches carry TeX blueprints whose
  `\uses` and `\leanok` show open work, users chat with it, and an auto mode runs parallel
  subagents on a sandboxed server-side clone. We take the GitHub and blueprint workflow and the
  chat-plus-auto-mode interaction.
- **TeXRA** defines agents as YAML files, each free to run a different model, and returns every
  edit as a diff to approve. We take agents as data and approval of diffs.
- **Lu, Tjoa and Cirac** (arXiv:2607.07857) grew six roles one at a time as bottlenecks appeared:
  orchestrator, proof writer, library scout, simplifier, blueprint synchronizer and an
  automatically running reviewer. They used scout-then-prove handoffs and review-repair loops
  capped at five rounds, and credit persistent memory with keeping dead ends from being
  re-investigated. Two findings shape this design: keeping formal statements faithful was harder
  than closing lemmas, and the orchestrator was 43% of model spend because its context grew large.
- **Gödel's Poetry** contributes whole-proof generation with verifier-guided self-correction and
  recursive decomposition. Its extraction of sorried `have` statements through the Kimina Lean
  Server's AST extension is the part we do not carry over (ADR-0002).

## 2. Principles

1. **Stochastic proposes, deterministic decides.** Models and agents only propose; the commit gate
   alone writes to GitHub, after mechanical checks (ADR-0001).
2. **Declaration-level handoff.** Work crossing an agent boundary is a top-level Lean declaration,
   never a goal inside another proof (ADR-0002).
3. **Status is derived, never claimed.** Blueprint status comes from the Lean environment, not from
   what the TeX asserts (ADR-0012).
4. **Agents are data; tools are code.** New agents recombine existing capabilities; new
   capabilities arrive only through code review (ADR-0015).
5. **Everything is an event.** The trace format is the training format (ADR-0016).
6. **Nothing a user supplies is trusted for a verification decision, and nothing produced in one
   tenant's sandbox reaches another** (ADR-0008).

## 3. System overview

```text
+---------------------------------------------------------------------+
| Clients: conductor CLI | desktop | web | MCP / ACP                  |
+---------------------------------------------------------------------+
| Control-plane API: auth, tenancy, sessions, live event stream       |
+----------------------+-----------------------+----------------------+
| Project graph    [D] | Orchestrator      [S] | Workflow layer   [D] |
| blueprint + Lean     | chat, plans, spawns   | runs, approvals      |
+----------------------+-----------------------+----------------------+
| Model gateway        | Agent runtime     [S] | Tool router      [D] |
| routing, keys, logs  | agents as specs       | MCP, per fingerprint |
+----------------------+-----------------------+----------------------+
| Model backends   [S] | Trace store           | Lean pools       [D] |
| APIs, vLLM, Ollama   | event-sourced log     | sandboxed            |
+----------------------+-----------------------+----------------------+
| Training             | GitHub repository     | Commit gate      [D] |
| SFT, prefs, RLVR     | leanblueprint layout  | sole GitHub writer   |
+----------------------+-----------------------+----------------------+
[S] model-driven: proposes only.   [D] deterministic: decides.
Substrate: Ray. Tenant-controlled and model-written code runs only in sandboxes.
```

Clients are thin. They share one control-plane API: REST for resources and a per-session event
stream for anything live. The API has parity: the orchestrator is a client with a policy-scoped
token, so anything a user can do with a button it can do with a tool call, under the same checks.
The desktop app is a Tauri shell around the web client and can embed the single-process local
mode for offline work.

The code maps onto subpackages of `prover_conductor`: `core` (domain model and policy),
`workflows`, `agents`, `models`, `lean`, `envs`, `sandbox`, `search`, `blueprint`, `gate`, `vcs`,
`traces` and `data`. Import-linter enforces that only `gate` imports the GitHub write client and
that the deterministic packages never import `agents` or `models`.

## 4. Control plane and conversation (R8, R9, R11)

**The orchestrator** is an agent whose state does not live in its context window. Runs, tasks,
budgets, open questions and decisions live in the durable workflow layer; the orchestrator's
prompt is rebuilt each turn from that structured state plus a compacted digest of recent events.
Per-call cost stays flat as a project grows, and a crashed or swapped orchestrator resumes
mid-plan. The workflow engine is chosen when first needed (Temporal and DBOS are the candidates);
Ray actors never hold state that must survive a restart (ADR-0005).

**Conversation.** Commands become orchestrator tool calls. Side-effecting control operations
(pause, cancel, approve, raise a budget) also exist as deterministic slash commands, so controlling
a running system never depends on a model parsing the user correctly. Any agent can raise a typed
question, blocking or not, attached to a blueprint node with the evidence that prompted it: a
forfeit analysis, a counterexample, two conflicting source conventions. The orchestrator batches
and deduplicates questions into the conversation. Answers are stored as decisions on the node,
where later agents read them and where they become training signal.

**Autonomy** is a policy over approval points, not a single mode. The approval points are intent
locks, blueprint structure changes, proof commits, environment changes, and new agent kinds or
budget increases.

| Preset | Intent locks | Blueprint structure | Proof commits | Environment changes |
|---|---|---|---|---|
| Review everything | human | human | human | human |
| Prove and review | human (usually already locked) | human | human | human |
| Supervised | human | automatic, user notified | automatic after the gate and reviewer | human |
| Full autonomy | fidelity reviewer plus lock obligations | automatic | automatic | human |

New agent kinds and budget increases need approval in the first three presets. In every preset
the main theorem's lock waits for a human, because it is the one step where an error is invisible
to everything downstream; removing that takes an explicit override. Approvals are durable waits: a
pending approval parks one branch of the work graph while everything independent keeps running.

## 5. Project graph and blueprints (R10)

The system's model of a repository joins two sources at the same commit (ADR-0012). The informal
side comes from parsing the blueprint with leanblueprint's own plasTeX plugin: nodes, labels,
`\lean{}` links, and statement-level and proof-level `\uses`. The formal side comes from the Lean
environment through the Lean helper: whether each linked declaration exists, whether its value
reaches `sorryAx`, which axioms it depends on, and which project-local constants its proof uses.

Status is derived from the join. `\leanok` is written by deterministic code after the gate passes,
so the blueprint maintainer writes prose, not status, and drift becomes a mechanical check.
Repositories that use LeanArchitect's `@[blueprint]` annotations get an adapter that reads the same
facts from Lean.

The graph has two levels. The public blueprint is the document in the repository. The working
graph is where refinement puts helper lemmas. The blueprint maintainer promotes a working node into
the blueprint when it is mathematically meaningful; proof-engineering helpers stay private
declarations beside their parent. Blueprint prose stays self-contained mathematics with no Lean
identifiers.

**Onboarding** (ADR-0003): the repository uses an official Lean release or release candidate from
roughly the last year, exactly one lakefile format per package, and the leanblueprint layout. A
repository without the layout is onboarded through a scaffolding commit that passes the gate; an
empty repository also gets a Lake project on the newest supported toolchain. This is what lets the
most automated level start from nothing but an informal theorem.

## 6. Agents (R5)

Every agent is an AgentSpec, which is data (ADR-0015): a role prompt from versioned fragments,
capability requirements instead of a model name, a tool grant, a budget (tokens, dollars, Lean
CPU-seconds, wall clock), an output schema and termination conditions.

**Roster.** The six required roles plus two:

- **orchestrator**: plans, spawns, converses, asks;
- **statement formalizer**: turns informal statements into Lean statements, for the most automated
  level;
- **fidelity reviewer**: checks formal statements against their informal meaning, and never shares
  a context with the formalizer, since a reviewer that has read the formalizer's reasoning inherits
  its misreadings;
- **prover**: a portfolio of strategies behind one interface (below);
- **theorem-search scout**: finds existing results before proving starts;
- **simplifier**: shortens and cleans proofs that already pass;
- **blueprint maintainer**: writes and restructures blueprint prose, promotes working nodes;
- **reviewer**: runs on every patch, checks Mathlib conventions and generality, and searches for
  whether a lemma already exists in Mathlib.

**Prover portfolio.** Tool-integrated proving over LSP feedback (lean-lsp-mcp) for general models;
whole-proof sampling with verifier-guided self-correction for specialized provers, the loop Gödel's
Poetry uses, rebuilt on the model gateway and the LeanService interface; lemma-first decomposition
for hard nodes (section 7); and global refinement in the style of Goedel-Architect. Gödel's Poetry
itself can run unchanged outside the system as an evaluation baseline. Repair loops are capped (the
Lu, Tjoa and Cirac workflow used five rounds) and a capped-out attempt ends in a forfeit, not a
silent retry.

**Typed outcomes.** A prover returns a patch, a forfeit (diagnosis, what was tried, proposed
decomposition), or a Lean-verified negation. Negations go into the project's knowledge base as
known-false statements with counterexamples, so no later agent re-attempts them.

**Knowledge base.** Per project and versioned: scouting memos, rejected routes, conventions,
technique notes, and a small pinned set every agent reads.

**Dynamic agents.** `spawn_agent` instantiates an existing spec (fan five provers out over five
frontier nodes) and needs only budget. `define_agent` creates a new kind from existing fragments,
with a tool grant no wider than the definer's and a budget carved from its own. A cluster of
forfeits sharing a diagnosis is a good trigger for proposing a new kind, which automates how roles
arose in the Lu, Tjoa and Cirac workflow. Promotion from one-off to a project or organization
library requires a replay evaluation on past tasks from the trace store. Batch sampling, such as
256 samples from a whole-proof model, is one scheduled job, displayed as such, not 256 agents.

The agent loop is written in-house rather than taken from a framework: it is a few hundred lines,
and because the trace format is the training format, the system needs exact control over what is
sent.

## 7. Decomposition without extraction

The rule (ADR-0002): the unit of handoff between agents is a top-level declaration. Inside one
agent's session, `have h : P := by sorry` is a fine scratch device, because that agent fills it in
place and the file compiles whole. What never happens is turning such a goal into a new
declaration by extraction; that is where Gödel's Poetry's pipeline was error-prone, since
re-elaborating a rendered goal can change coercions, implicit arguments or instances, and pruning
context before a proof exists can drop a hypothesis the proof needed.

**Lemma-first decomposition.** When node N forfeits, the decomposer writes new top-level
declarations C1...Ck with `sorry` bodies, plus a proof of N that uses them. Before any child is
attempted, the Lean helper checks in N's pinned environment that:

1. each Ci elaborates on its own;
2. every path from N's proof to `sorryAx` passes through some Ci (sufficiency, checked before any
   proving effort is spent);
3. N's proof uses no project-local lemmas beyond the Ci and N's declared parents;
4. no Ci restates N or an ancestor, by statement hash;
5. N's statement is unchanged.

Children are then proved in their own declarations, and nothing is spliced back into N. Hypotheses
a proved child does not use are removed afterwards, from Batteries' `unusedArguments` output, and
the result is re-verified. A wrong child costs budget, not correctness: it surfaces as a negation
or a statement-wrong forfeit. Every child is reusable, promotable to the blueprint, in the form
whole-proof models expect, and an exact RLVR task.

The cost is that the decomposer must write closed statements, so it runs on a general model; a
specialized prover's `have` sketch can be passed along as a hint, never as ground truth.

**Recursion and escalation.** A forfeiting child gets the same step (local refinement). The
refinement escalates to global, with the whole working graph in view, after a depth or budget
limit, after repeated forfeits with the same diagnosis (the dead-end loop Goedel-Architect warns
about), or when repairing a negated child would change N's statement. If N itself is disproved and
locked, the question goes to a human.

**Partial proofs.** The agent that wrote a partial proof finishes it in place, or the decomposer
restates the remaining goals as children under the same checks. A mechanical Expr-level lift
(abstracting a goal over its full local context) may draft that restatement but never replaces it.

All checks run through `lake env lean`, the REPL or LSP. The Kimina Lean Server is an optional
throughput backend; nothing depends on its AST extension.

## 8. Models (R2, R4, R13)

Agents request capabilities: tool use, context length, reasoning, whole-proof Lean generation,
cost tier. A routing policy maps capabilities to endpoints, with fallbacks and canaries (ADR-0013).

Launch is bring-your-own-key through three adapters: OpenAI; Anthropic's native Messages API,
because traces need its thinking blocks; and OpenAI-compatible endpoints such as vLLM and Ollama.
A prompt-adapter layer handles model families that expect a fixed template, as most specialized
provers do. For self-hosted servers, bring-your-own-key means bring-your-own-endpoint: on the hosted
service these are reached only through an egress path that refuses loopback, private and link-local
addresses and pins resolved addresses, over HTTPS with authentication. Provider keys never enter an
agent's context or a sandbox.

The gateway records each call completely: the rendered request exactly as sent, the sampling
parameters, the model identity and revision, and the full response including reasoning where it is
exposed. A framework-level message list is not enough for training.

Serving (R13): self-hosted deployments run vLLM under Ray Serve, fed by a model registry; a newly
trained model is registered, canaried on a fraction of one role's traffic, and promoted on
evaluation results. vLLM is the default engine because its prefix cache can be salted per tenant.
Locally, Ollama or llama.cpp. At launch the hosted service does not pay for inference, so R13 is met
by self-hosted deployments and by users serving released weights on their own endpoints.

## 9. Lean execution (R3, R7, R14)

**Environments.** Version independence rests on an environment fingerprint: a hash of
`lean-toolchain`, the resolved `lake-manifest.json`, and the lakefile options that affect
elaboration (ADR-0009). An environment builder turns each fingerprint into an image, and the Lean
router sends every request to a pool pinned to the requesting worktree's fingerprint. The support
window is official `leanprover/lean4` releases and release candidates from roughly the last year
(ADR-0003), about one fingerprint per release.

**Fetching without Lake.** Resolving a Lake workspace elaborates `lakefile.lean`, and packages can
declare `post_update` hooks (Mathlib uses one to sync the toolchain and fetch its cache), so Lake
must never run with network access. Platform code fetches dependencies from `lake-manifest.json`
with plain git at pinned revisions, refusing private addresses; Lake then runs offline in the
sandbox. Where Mathlib's build artifacts come from is SPIKE-01's question.

**Backends.** Pools sit behind one LeanService interface and can be mixed: lean-lsp-mcp or a raw
LSP session for goals and diagnostics (with session affinity), a REPL through LeanInteract, the
Kimina Lean Server for high-throughput checking, and Pantograph for goal-level search. Any of them
can run in the cluster or outside it, registered with a fingerprint, capacity and credentials. To
agents, internal and external services alike are MCP servers, so local versus remote is a registry
entry. Pools for idle fingerprints scale to zero; active ones need capacity planning, since a
process with Mathlib imported is memory-heavy. Build artifacts are cached per fingerprint and
commit.

**Elaboration executes code.** `#eval`, `run_cmd`, `initialize` and custom elaborators run
arbitrary code, so every Lean process that touches tenant or model-written code runs sandboxed
(section 12). A parse-only check for code-executing and kernel-bypassing constructs would be a
useful upstream contribution to Mathlib; until one exists, the gate carries its own.

**Version-consistent search.** LeanExplore, Loogle and LeanSearch each index a particular Mathlib
version, so a suggested lemma may not exist in the project's pinned Mathlib. The search layer checks
each candidate with `#check` in the requesting environment before a prover sees it.

prover-conductor never changes a project's toolchain or dependencies on its own. An upgrade is an
environment-change task behind its own approval point, and it migrates intent locks (section 10).

## 10. The commit gate (R15)

Agents produce patches against internal worktrees; the gate is the only component that pushes, as a
GitHub App (ADR-0001). It runs from a clean checkout of base plus patch, in the pinned image, inside
the sandbox, and stops at the first failure (ADR-0011):

| Stage | Check | Catches |
|---|---|---|
| Patch policy | allowed paths only; toolchain, manifest and lakefile untouched unless the task is an environment change | scope creep, silent dependency bumps |
| Pre-elaboration scan | parse-only scan for new axioms outside the allowlist, `sorry` or `admit` outside statement-only nodes, `unsafe`, `implemented_by`, `extern`, `native_decide`, `debug.*` options, code-executing commands | cheats and elaboration-time code, before anything runs |
| Build | `lake build` with Mathlib's standard linter set adjusted by the repository profile; every error or warning fails except the `sorry` warning on a locked, statement-only declaration | errors, style-linter violations |
| Lint | `lake lint` (Batteries `runLinter`), `lake exe lint-style`, `lake exe mk_all --check` | missing docstrings, simp-normal-form and unused-argument problems, text style |
| Axiom audit | axioms of changed declarations and their dependents within propext, Classical.choice, Quot.sound and the allowlist; `sorryAx` only through locked statement-only dependencies | smuggled axioms, `sorry` reached through dependencies |
| Intent locks | hash equality for locked statements and their definition closures; Comparator for locked theorems whose dependency cone is sorry-free | weakened statements, edited definitions, environment tricks |
| Blueprint | `leanblueprint checkdecls`; the blueprint builds; derived status matches the TeX; `\uses` covers actual dependencies | drift between TeX and Lean |

**Profiles.** Mathlib's style linters are a floor no repository can disable; Mathlib policy checks
are optional. The header linter shows why: it demands Mathlib's exact Apache-2.0 line and bundles
the copyright block, imports and module docstring, so a repository with another license disables
it and gets prover-conductor's replacement check for the style parts. Existing repositories either
clean up first or onboard under a ratchet: diagnostics in touched declarations fail, recorded
legacy diagnostics elsewhere are tolerated, and the record only shrinks.

**Intent locks** (ADR-0010) cover a statement plus the closure of project-local definitions,
structures and instances it mentions, because changing a definition changes a theorem's meaning
without touching its text. Hashing the elaborated statement catches notation shadowing and instance
hijacking. Locks are committed to the target repository so its own CI verifies them. They carry
obligations, such as a non-vacuity witness showing the hypotheses hold for a nontrivial instance; a
node with undischarged obligations is neither done nor certified. Environment upgrades re-hash
every lock and put changed statements in front of an approver.

**Two tiers.** Every gate run compares lock hashes computed by the Lean helper. Comparator builds a
trusted challenge and the untrusted solution in separate sandboxes, exports both with lean4export,
and replays the solution through the kernel; independent kernels such as nanoda can check the same
export. Comparator accepts only propext, Quot.sound and Classical.choice, so it certifies
milestones: locked theorems whose whole dependency cone is sorry-free, the main theorem included.
Attestations say which tier they are: gate-passed (checks ran in the tenant's environment) or
certified (platform binaries against a published challenge).

**Landing.** Platform writes are pull requests. A merge queue re-runs the gate on each patch rebased
onto the current head, so two green patches cannot make a red main. A passing run yields a signed
attestation (commit, fingerprint, gate version, stage results, obligation status), posted as a
GitHub check run and stored with the traces. The same gate ships as a GitHub Action that branch
protection makes a required check, so a misconfigured deployment still cannot merge what the gate
rejects. Merging happens in GitHub, with auto-merge in presets that allow it.

**What the gate cannot do.** It cannot establish that names follow Mathlib's naming conventions,
that a lemma has the right generality, or that a formal statement means what its informal
counterpart means. Reviewer agents and human lock approval cover those.

**Adversarial suite.** The gate is tested by attack: statement weakening, axioms hidden behind
definitions, `debug.skipKernelTC`, instance hijacking, notation shadowing, elaboration-time I/O,
hostile lakefiles, spoofed toolchains, forked dependencies, poisoned caches. A gate nobody has
attacked is not evidence of anything.

## 11. Traces and training data (R11, R12)

Everything is an event (ADR-0016): every model call with its rendered request, response and usage;
every tool call; every Lean interaction with goals and diagnostics; every gate stage, question,
decision and approval. The most valuable event is the difference between what an agent proposed
and what a human approved. Spans follow OpenTelemetry's GenAI conventions, so observability tools
can attach; domain events have their own schemas. Hot state lives in Postgres and payloads in object
storage as Parquet; the live fan-out mechanism is chosen with the workflow layer.

**Inspection** reads the same stream: a live agent tree with per-agent token streams and goal
states; attach, steer, pause, kill and fork; aggregated rollups when fifty subagents run at once,
with drill-down; and step-by-step replay of any finished run.

**Datasets.** Builders turn the log into versioned datasets: supervised data from verified proofs
and successful trajectories; preference pairs from human edits at review, gate failures paired with
their fixes, and reviewer verdicts; and RLVR task sets.

**RLVR extraction** is designed around training provers on tasks derived from physicslib4. Given a
repository and commit, each proved declaration becomes a task: its environment is truncated to what
precedes it, with duplicate statements removed; its goal is the locked statement; its reward is the
gate's verification profile (compile, axioms, statement match, no style checks). Tasks export with
their per-fingerprint image, so the trainer is interchangeable. The same extractor is the
evaluation harness. Splits are by blueprint chapter or dependency cluster, never random, because
neighboring lemmas leak into each other; scores on declarations older than a model's training cutoff
are upper bounds. Decontamination against miniF2F, PutnamBench and ProofNet runs before any
evaluation.

Every record carries provenance and consent (section 12), so builders filter by consent, license
and provider terms.

## 12. Tenancy, security and deployment

**Tenancy** (ADR-0004). A tenant is a GitHub repository keyed by its numeric ID, owned by the
repository's owning account through its App installation. Roles derive from repository permissions:
maintainers approve locks and merges, writers start runs, readers observe, re-checked at every
approval, merge and push. Each project has a shared channel beside private sessions. Leases keep two
users' runs off the same node. Budgets and quotas exist per user, tenant and owning account, with
fair-share scheduling.

**Threat model** (ADR-0008) has two profiles behind one SandboxRunner interface.

- *Hosted:* tenants are adversaries, and building a repository means running their code. Builds and
  Lean processes run in gVisor sandboxes through Ray Sandboxes with networking disabled; Lake runs
  only offline; toolchains come from checksum-verified mirrors of allowlisted releases; dependency
  identity is URL plus commit; verdicts come from platform binaries only. Shared caches accept only
  platform-built artifacts, warm Lean processes are never reused across tenants or sessions, model
  prefix caches are salted per tenant, and user-registered MCP servers are tenant-scoped and
  untrusted. ADR-0008 has the full sharing table.
- *Local:* the operator is trusted, but model output is not, because it is elaborated before anyone
  reads it and can be steered by untrusted text. Model-written code runs in an OS-level sandbox (for
  example Anthropic's sandbox runtime: sandbox-exec on macOS, bubblewrap on Linux) with no network,
  writes confined to the worktree and a scratch directory, and credential paths unreadable. On by
  default, with a switch to turn it off; no virtual machine.

Ray is the substrate, not the isolation boundary (ADR-0005): it runs whatever it is given, so tenant
code never runs as a Ray task or actor, token authentication is on, and the dashboard, Jobs API and
Ray Client are never reachable by tenants. Repository text, fetched pages and MCP responses are
untrusted input to agents, and tool egress goes only to registered endpoints.

**Abuse and cost.** Hard budgets at the model gateway and the Lean router; sign-in before any spend;
bring-your-own-key for inference; sandbox limits outside user control; GitHub writes only where the
App is installed, with permission re-checked at each write.

**Data governance** (ADR-0014). Consent and data classification are recorded on every event at write
time. Nothing enters a shared model without opt-in, and anything trained on private data serves only
its tenant. Payloads are encrypted with per-tenant keys, so erasure is key destruction. Trained
weights cannot forget, so the consent text says so. GDPR applies to open registration; the consent
flow needs legal review before launch.

**Deployment modes.** One process on a laptop (SQLite, an in-process queue, local elan, Ollama,
the local sandbox), which is how prover-conductor is developed and what the desktop app embeds; a
self-hosted Ray cluster; and the hosted service. Where persistent stores live is deployment
configuration. An external security review and an invite-only beta come before public registration.

**Stack.** Python is the core language, because leanblueprint and plasTeX, LeanInteract,
PyPantograph, the Kimina client and the training stack are Python. TypeScript for the web client,
Tauri for the desktop shell.

## 13. Repository layout

Now:

```text
prover-conductor/
├── CLAUDE.md, README.md, LICENSE, pyproject.toml, uv.lock, .mcp.json
├── .claude/                  settings and hooks, generated ADR rules, skills, subagents
├── .github/                  CI, CODEOWNERS, issue and pull-request templates
├── docs/
│   ├── architecture.md       this document
│   ├── adr/                  decisions, invariants, and enforcement.yaml
│   ├── spikes/               experiments that settle open questions
│   └── specs/                interface and format specifications
├── scripts/                  ADR tooling
├── src/prover_conductor/     one subpackage per area, docstring stubs
├── tests/                    tests/meta checks repository conventions and tooling
├── lean/                     home of the Lean helper ConductorTools (from build step 2)
├── agent-library/            agent specs as data (ADR-0015)
└── policies/                 autonomy presets, gate profiles, routing policies
```

Added as the system grows: `spikes/` (experiment code, one directory per spike), `schemas/` (API,
event, agent, project and dataset schemas, from which Python and TypeScript types are generated),
`actions/gate/` (the gate as a GitHub Action), `apps/web/` and `apps/desktop/`, `deploy/` (local and
Ray cluster), `serving/`, `training/`, `evals/`, `tests/fixtures/repos/` (small Lean projects) and
`tests/adversarial/` (the gate's attack suite).

A target repository gets `.prover-conductor/project.toml` (gate profile, autonomy preset, approval
routing), `.prover-conductor/locks.json`, and `.github/workflows/prover-conductor-gate.yml`.

## 14. Plan

**Spikes** (`docs/spikes/`) run one at a time, in numeric order, each merged before the next
starts. SPIKE-01 to SPIKE-04 can change a decision: Lake-free fetch and the Mathlib artifact source;
sandbox cost for Lean workloads; statement-hash stability; Comparator at scale. SPIKE-05 to
SPIKE-08 fill in parameters: the Lean helper across versions; blueprint parsing on real projects;
provider terms and trace exposure; and comparing notes with Fuse.

**Build order.**

1. Repository, ADRs and Claude Code setup (this skeleton), then the verification session.
2. The Lean helper and the gate as a standalone CLI, test-first, starting with the adversarial
   suite, hostile-tenant cases included. The helper and hash prototyped in SPIKE-05 and SPIKE-03
   move into `lean/ConductorTools` here.
3. Backtest on physicslib4: run the gate on its history, decide between clean-up and ratchet, and
   bootstrap provisional locks.
4. The project graph and a drift report.
5. The RLVR task extractor, used first as the evaluation harness.
6. The first end-to-end loop: one user, CLI, prove-and-review preset, tool-integrated prover,
   events recorded.
7. Lemma-first decomposition.

Then durable workflows and the web client with inspection; dynamic agents; the multi-user cluster on
Ray with Ray Sandboxes; serving; training. An external security review and an invite-only beta come
before public registration.

## 15. Glossary

- **Attestation**: the signed record of a gate run: commit, fingerprint, gate version, stage
  results, tier and obligation status.
- **Certified**: the attestation tier issued after Comparator accepts a locked theorem on platform
  binaries.
- **Environment fingerprint**: hash of the toolchain, the resolved manifest and elaboration-affecting
  options.
- **Forfeit**: a structured failure report: diagnosis, attempts, proposed fix or decomposition.
- **Gate-passed**: the attestation tier for checks run in the tenant's environment.
- **Intent lock**: an approved statement plus its definition closure, protected by hash.
- **Negation**: a Lean-verified proof that a statement is false.
- **Obligation**: something a lock requires before its node counts as done, such as a non-vacuity
  witness.
- **Tenant**: a GitHub repository, keyed by numeric repository ID.
- **Working graph**: the blueprint graph plus helper lemmas not yet promoted to the public
  blueprint.

## 16. References

- Gödel's Poetry: https://arxiv.org/abs/2512.14252
- Goedel-Architect: https://arxiv.org/abs/2606.06468
- Lu, Tjoa, Cirac, multi-agent formalization of tensor network theory: https://arxiv.org/abs/2607.07857
- Numina's Fuse: https://lean.nyc/blog/numina-fuse
- TeXRA: https://texra.ai
- leanblueprint: https://github.com/PatrickMassot/leanblueprint
- LeanArchitect: https://github.com/hanwenzhu/LeanArchitect
- Comparator: https://github.com/leanprover/comparator
- lean-lsp-mcp: https://github.com/oOo0oOo/lean-lsp-mcp
- Ray Sandboxes: https://docs.ray.io/en/latest/ray-core/sandboxes.html
- Ray security and token authentication: https://docs.ray.io/en/latest/ray-security/index.html
- vLLM prefix caching and cache salting: https://docs.vllm.ai/en/stable/design/prefix_caching/
- Anthropic sandbox runtime: npm package `@anthropic-ai/sandbox-runtime`
- Claude Code documentation: https://code.claude.com/docs
