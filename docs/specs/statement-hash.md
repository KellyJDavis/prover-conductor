# Statement hash

Version: 0 (draft, from SPIKE-03). Prototype: `spikes/SPIKE-03/hash/`. Fixture suite:
`spikes/SPIKE-03/`. Changed only together with the code and tests that implement it.

Governs the hash an intent lock stores (ADR-0010, ADR-0019). The Lean helper computes it in the
pinned environment; the gate compares it.

## What is hashed

For a locked declaration D in a loaded environment:

1. **Root.** The type of D, and its value if D is a definition. D's own name is not hashed (a lock
   file is keyed by name), so renaming the locked theorem itself is benign.
2. **Closure.** The transitive closure of project-local constants mentioned by the root and by
   closure members, computed as a work list. Each member contributes:

   | Kind | Contribution |
   |---|---|
   | definition | kind, universe-parameter count, type, value, safety (safe, unsafe, partial) |
   | theorem | statement only |
   | opaque, axiom | type only |
   | inductive | type, constructor names and types, numParams, numIndices, isRec, unsafe, class flag, structure field names, `all` list |
   | constructor, recursor, `casesOn`, `brecOn`, `noConfusion` and similar | nothing; derived from the inductive |

3. **External references.** Constants that are not project-local are referenced by full name. They
   are listed separately as `externalReferences` (name, module, kind, `typeHash`) and are not part
   of `hash`.

**Project-local** means the first component of the constant's defining module name is one of the
configured local roots. The default root is the root of the module being hashed. Anything else,
including Mathlib and core, is external.

## Normalization

The hash is over the elaborated `Expr`, canonically serialized and hashed with SHA-256.

| Aspect | Treatment |
|---|---|
| Bound-variable names | dropped; bound variables are serialized by position |
| Binder info | all four kinds hashed (default, implicit, strict implicit, instance implicit); `--no-binder-infos` turns it off |
| Instance-implicit binder names | dropped; `[inst : C]` and `[C]` are equal, `[C]` and `(i : C)` differ |
| Universe parameter names | replaced by position in the declaration's `levelParams` list |
| `mdata` | dropped |
| Proofs | any subterm whose type is a `Prop` and which is a proof (`Meta.isProof`) is replaced by `_`, in the statement and in definition values |
| Private-name mangling | stripped |
| Internal auxiliary constants (matchers, `_f`, `_unary` and other `isInternalDetail` names) | referenced by a 16-hex content hash of their definition instead of by name |
| Local constant names | hashed; renaming a local constant changes the hash |
| Attributes (`simp`, `reducible`, `irreducible`, instance priority) | not hashed |
| Docstrings, comments, whitespace, declaration order, unrelated declarations, `open`, `variable` | not hashed; only the elaborated term counts |

Consequences that follow from hashing the elaborated term: local instances, notation shadowing,
coercions, autoImplicit and `open` resolution change the hash exactly when they change what the
statement elaborates to.

## Known limitations

- **Over-sensitivity.** No semantic normalization: `n + n` versus `2 * n`, `a > b` versus
  `b < a`, and `a ≠ b` versus `¬ (a = b)` all differ.
- **Anonymous instances.** Reordering two anonymous instances of one class changes the hash,
  because their generated names (`instAddV`, `instAddV_1`) follow declaration order.
- **External values.** A changed body of an external (Mathlib or core) definition is invisible to
  `hash` and to `typeHash`. Detecting it needs a separate mechanism (ADR-0019).
- **Attributes.** An `@[irreducible]` change alone is not detected.
- **Macro scopes** in names are not normalized; mutual and nested inductives, `where` and
  `let rec` are only lightly covered.
- Cost on large Mathlib definitions is unmeasured.

## Output

`stmthash --module M [--local-root R]... [--serialize] [--no-binder-infos] decl...` prints JSON:
`schema` (`statement-hash-spike/1`), `lean`, and `declarations[]`, each with `name`, `exists`,
`kind`, `hash`, `closure[]` (name, kind, per-entry hash), `externalReferences[]` and, with
`--serialize`, `serialization`.

The tool loads the environment with `loadExts := false` and never enables initializers, so hashing
does not run a module's `initialize` blocks. Whether that alone makes it safe to run on tenant
code is not established (see ADR-0019); ADR-0005 still requires the sandbox for tenant-controlled
Lean.
