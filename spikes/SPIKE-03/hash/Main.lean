import StatementHash.Core

open Lean StatementHash

/-- `stmthash --module M [--local-root R]... [--serialize] [--no-binder-infos] decl...`
Environment lookup uses LEAN_PATH (and LEAN_SYSROOT for the core library). -/
def main (args : List String) : IO UInt32 := do
  let mut modules : Array Name := #[]
  let mut roots : Array Name := #[]
  let mut decls : Array Name := #[]
  let mut serialize := false
  let mut bi := true
  let mut rest := args
  while !rest.isEmpty do
    match rest with
    | "--module" :: m :: t => modules := modules.push m.toName; rest := t
    | "--local-root" :: r :: t => roots := roots.push r.toName; rest := t
    | "--serialize" :: t => serialize := true; rest := t
    | "--no-binder-infos" :: t => bi := false; rest := t
    | d :: t => decls := decls.push d.toName; rest := t
    | [] => pure ()
  if modules.isEmpty then
    IO.eprintln "usage: stmthash --module M [--local-root R]... [--serialize] decl..."
    return 2
  if roots.isEmpty then roots := modules.map (·.getRoot)
  initSearchPath (← findSysroot)
  -- Deliberately NOT calling enableInitializersExecution: `initialize` blocks of the
  -- inspected project must not run.
  let env ← importModules (modules.map fun m => { module := m }) {}
  let cfg : Config := { localRoots := roots, binderInfos := bi }
  let mut out : Array Json := #[]
  for d in decls do
    let ctx : Core.Context := { fileName := "<stmthash>", fileMap := default }
    let r ← ((hashDecl cfg d).run').toIO ctx { env }
    match r with
    | (none, _) => out := out.push (Json.mkObj [("name", d.toString), ("exists", false)])
    | (some r, _) =>
      let ents := r.entries.map fun e => Json.mkObj
        [("name", e.key), ("kind", e.kind), ("hash", e.hash)]
      let exts := r.externals.map fun (x, th) => Json.mkObj
        [("name", x.name), ("module", x.module), ("kind", x.kind), ("typeHash", th)]
      let base : List (String × Json) :=
        [("name", d.toString), ("exists", true), ("kind", r.kind), ("hash", r.hash),
         ("closure", Json.arr ents), ("externalReferences", Json.arr exts)]
      out := out.push (Json.mkObj (if serialize then base ++ [("serialization", Json.str r.serialization)] else base))
  IO.println (Json.mkObj [("schema", "statement-hash-spike/1"),
    ("lean", Lean.versionString), ("declarations", Json.arr out)]).compress
  return 0
