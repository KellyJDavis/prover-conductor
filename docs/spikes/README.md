# Spikes

Time-boxed experiments that settle open questions in proposed ADRs. Run one with
`/spike SPIKE-NN` in Claude Code, or by hand following the protocol in
`.claude/skills/spike/SKILL.md`: confirm the method and time box first, work on a branch named
`spike/SPIKE-NN`, record every measurement with the command that produced it, and end with
implications for each ADR the spike informs. Spikes never change an ADR's status.

Run spikes one at a time, in numeric order: start a spike only after the previous spike's pull
request is merged. Sequential runs keep branches from conflicting, keep ADR numbers from
colliding, and keep other work from distorting measurements. SPIKE-08 is a conversation with the
Numina team and can happen whenever it suits.

A spike keeps everything under `spikes/SPIKE-NN/`, with clones, builds and downloads in
`spikes/SPIKE-NN/work/`, which git ignores. Outside that directory it changes only its own spike
file and new files in `docs/specs/`, unless its exit criteria name another path. It never edits
`pyproject.toml` or `uv.lock`.

Spikes 01 to 04 can change a decision; 05 to 08 mostly fill in parameters.

| ID | Question | Informs | Can change a decision | Owner |
|---|---|---|---|---|
| SPIKE-01 | Can dependencies be fetched without running Lake? Where do Mathlib artifacts come from? | ADR-0008, ADR-0009 | yes | Claude Code |
| SPIKE-02 | What do gVisor and the local sandbox cost for Lean builds and sessions? | ADR-0005, ADR-0008 | yes | Claude Code |
| SPIKE-03 | What exactly does a statement hash cover, and is it stable? | ADR-0010 | yes | Claude Code, lean-helper |
| SPIKE-04 | What does Comparator cost at scale, and on which versions does it run? | ADR-0010 | yes | Claude Code |
| SPIKE-05 | Can one Lean helper build across the support window? | ADR-0003, ADR-0009 | parameters | Claude Code, lean-helper |
| SPIKE-06 | How faithfully does leanblueprint's parser read real blueprints? | ADR-0012 | parameters | Claude Code |
| SPIKE-07 | What do launch providers allow and expose? | ADR-0013, ADR-0014, ADR-0016 | parameters | owner and Claude Code |
| SPIKE-08 | How do Fuse's checks and isolation compare with ours? | ADR-0008, ADR-0011 | parameters | owner, with Numina |
