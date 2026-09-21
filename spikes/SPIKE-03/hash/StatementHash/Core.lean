import Lean
import StatementHash.Sha256

/-!
# Statement hash (SPIKE-03 prototype)

Hashes the elaborated statement of a declaration plus the transitive closure of the
project-local constants it mentions.  See `docs/specs/statement-hash.md` for the specification
and the reasons behind each normalization.
-/

open Lean Meta

namespace StatementHash

structure Config where
  /-- A constant is project-local iff the first component of its module name is one of these. -/
  localRoots : Array Name
  /-- Include binder infos (default, implicit, strict implicit, inst implicit) in the hash. -/
  binderInfos : Bool := true

structure Ctx where
  cfg : Config
  lps : Array Name := #[]
  stack : Array FVarId := #[]

structure ExtRef where
  name : String
  module : String
  kind : String
  deriving Inhabited

structure St where
  queue : Array Name := #[]
  seen : NameSet := {}
  externals : Std.HashMap Name ExtRef := {}
  auxCache : Std.HashMap Name String := {}
  cache : Std.HashMap Expr String := {}

abbrev M := ReaderT Ctx (StateRefT St MetaM)

/-- Name as it appears in the serialization: private-name mangling removed. -/
def canon (n : Name) : Name := (privateToUserName? n).getD n

def moduleOf? (env : Environment) (n : Name) : Option Name :=
  (env.getModuleIdxFor? n).map fun i => env.header.moduleNames[i.toNat]!

def isLocalConst (env : Environment) (cfg : Config) (n : Name) : Bool :=
  match moduleOf? env n with
  | some m => cfg.localRoots.contains m.getRoot
  | none => true

/-- Compiler/elaborator generated helpers whose names are unstable: referenced by content. -/
def isAuxConst (env : Environment) (n : Name) : Bool :=
  let u := canon n
  Meta.isMatcherCore env n || u.isInternalDetail ||
    (match u with
     | .str _ s => s.startsWith "proof_" || s.startsWith "match_"
     | _ => false)

def constKind : ConstantInfo → String
  | .axiomInfo _ => "axiom"
  | .defnInfo _ => "def"
  | .thmInfo _ => "thm"
  | .opaqueInfo _ => "opaque"
  | .quotInfo _ => "quot"
  | .inductInfo _ => "inductive"
  | .ctorInfo _ => "ctor"
  | .recInfo _ => "rec"

def biStr (cfg : Config) : BinderInfo → String
  | .default => ""
  | bi => if cfg.binderInfos then
      (match bi with
       | .implicit => "{}"
       | .strictImplicit => "{{}}"
       | .instImplicit => "[]"
       | .default => "")
    else ""

def serLevel (lps : Array Name) : Level → String
  | .zero => "0"
  | .succ l => s!"(s {serLevel lps l})"
  | .max a b => s!"(max {serLevel lps a} {serLevel lps b})"
  | .imax a b => s!"(imax {serLevel lps a} {serLevel lps b})"
  | .param n => match lps.findIdx? (· == n) with
    | some i => s!"u{i}"
    | none => s!"u?{n}"
  | .mvar _ => "?"

def enqueue (n : Name) : M Unit :=
  modify fun s => if s.seen.contains n then s else { s with queue := s.queue.push n }

def isProofSafe (e : Expr) : M Bool := do
  try Meta.isProof e catch _ => pure false

mutual

partial def ser (e : Expr) : M String := do
  let e := e.consumeMData
  if let some s := (← get).cache[e]? then return s
  let s ← serCore e
  modify fun st => { st with cache := st.cache.insert e s }
  return s

partial def serCore (e : Expr) : M String := do
  let ctx ← read
  match e with
  | .bvar i => return s!"(bvar {i})"
  | .mvar _ => return "?mvar"
  | .sort l => return s!"(Sort {serLevel ctx.lps l})"
  | .lit (.natVal n) => return s!"(nat {n})"
  | .lit (.strVal s) => return s!"(str {s.quote})"
  | .mdata _ b => ser b
  | .forallE n t b bi =>
    let ts ← ser t
    withLocalDecl n bi t fun x => do
      let bs ← withReader (fun c => { c with stack := c.stack.push x.fvarId! }) (ser (b.instantiate1 x))
      return s!"(pi{biStr ctx.cfg bi} {ts} {bs})"
  | _ =>
    -- proofs are erased: only their existence (by typing) matters
    if ← isProofSafe e then return "_"
    match e with
    | .fvar id =>
      match ctx.stack.findIdx? (· == id) with
      | some i => return s!"v{i}"
      | none => return "(fvar?)"
    | .const n ls =>
      let r ← refConst n
      return s!"(c {r} [{",".intercalate (ls.map (serLevel ctx.lps))}])"
    | .app .. =>
      let f ← ser e.getAppFn
      let args ← e.getAppArgs.mapM ser
      return s!"(app {f} {" ".intercalate args.toList})"
    | .lam n t b bi =>
      let ts ← ser t
      withLocalDecl n bi t fun x => do
        let bs ← withReader (fun c => { c with stack := c.stack.push x.fvarId! }) (ser (b.instantiate1 x))
        return s!"(lam{biStr ctx.cfg bi} {ts} {bs})"
    | .letE n t v b _ =>
      let ts ← ser t
      let vs ← ser v
      withLetDecl n t v fun x => do
        let bs ← withReader (fun c => { c with stack := c.stack.push x.fvarId! }) (ser (b.instantiate1 x))
        return s!"(let {ts} {vs} {bs})"
    | .proj s i b =>
      let r ← refConst s
      let bs ← ser b
      return s!"(proj {r} {i} {bs})"
    | _ => return "?"

partial def noteExternal (n : Name) : M Unit := do
  let env ← getEnv
  let some ci := env.find? n | return
  let m := (moduleOf? env n).getD .anonymous
  let r : ExtRef := { name := (canon n).toString, module := m.toString, kind := constKind ci }
  modify fun s => { s with externals := s.externals.insert n r }

partial def refConst (n : Name) : M String := do
  let env ← getEnv
  let cfg := (← read).cfg
  if !isLocalConst env cfg n then
    noteExternal n
    return (canon n).toString
  if isAuxConst env n then
    return s!"aux:{← auxHash n}"
  enqueue n
  return (canon n).toString

partial def auxHash (n : Name) : M String := do
  if let some h := (← get).auxCache[n]? then return h
  let saved := (← get).cache
  modify fun s => { s with cache := {} }
  let (k, b) ← entryOf n
  modify fun s => { s with cache := saved }
  let h := ((sha256Hex s!"{k}|{b}").toList.take 16).foldl (fun acc c => acc.push c) ""
  modify fun s => { s with auxCache := s.auxCache.insert n h }
  return h

/-- (kind, canonical body) of a constant, in the context of its own universe parameters. -/
partial def entryOf (n : Name) : M (String × String) := do
  let env ← getEnv
  let some ci := env.find? n | return ("missing", "")
  withReader (fun c => { c with lps := ci.levelParams.toArray, stack := #[] }) do
    let hdr := s!"ups={ci.levelParams.length}"
    if isAuxRecursor env n || isNoConfusion env n then
      enqueue n.getPrefix
      return ("derived", "")
    match ci with
    | .axiomInfo v => return ("axiom", s!"{hdr} T={← ser v.type}")
    | .thmInfo v => return ("thm", s!"{hdr} T={← ser v.type}")
    | .opaqueInfo v => return ("opaque", s!"{hdr} T={← ser v.type} unsafe={v.isUnsafe}")
    | .defnInfo v =>
      let sf := match v.safety with | .safe => "safe" | .unsafe => "unsafe" | .partial => "partial"
      return ("def", s!"{hdr} T={← ser v.type} V={← ser v.value} {sf}")
    | .quotInfo _ => return ("quot", "")
    | .recInfo _ =>
      enqueue n.getPrefix
      return ("rec", "")
    | .ctorInfo v =>
      enqueue v.induct
      return ("ctor", s!"of {(canon v.induct)} idx={v.cidx}")
    | .inductInfo v =>
      for a in v.all do enqueue a
      let mut cs : Array String := #[]
      for c in v.ctors do
        match env.find? c with
        | some (.ctorInfo cv) =>
          cs := cs.push s!"{(canon c)}:{← ser cv.type}"
        | _ => pure ()
      let fields := match getStructureInfo? env n with
        | some si => ",".intercalate (si.fieldNames.toList.map toString)
        | none => "-"
      let csS := "; ".intercalate cs.toList
      let allS := ",".intercalate (v.all.map fun a => (canon a).toString)
      let ty ← ser v.type
      return ("inductive",
        s!"{hdr} T={ty} np={v.numParams} ni={v.numIndices} rec={v.isRec} unsafe={v.isUnsafe} class={isClass env n} fields=[{fields}] ctors=[{csS}] all=[{allS}]")

end

structure Entry where
  key : String
  kind : String
  body : String
  hash : String

structure Result where
  kind : String
  hash : String
  entries : Array Entry
  externals : Array (ExtRef × String)
  serialization : String

/-- Hash of one declaration in `env`; `none` if it does not exist. -/
def hashDecl (cfg : Config) (root : Name) : MetaM (Option Result) := do
  let env ← getEnv
  let some _ := env.find? root | return none
  let act : M Result := do
    let (rk, rb) ← entryOf root
    let mut entries : Array Entry :=
      #[{ key := "@root", kind := rk, body := rb, hash := sha256Hex s!"{rk}|{rb}" }]
    repeat
      let s ← get
      let some n := s.queue.find? (fun n => !s.seen.contains n) | break
      modify fun s => { s with seen := s.seen.insert n, queue := s.queue.filter (· != n) }
      if n == root then continue
      let (k, b) ← entryOf n
      let e : Entry := { key := (canon n).toString, kind := k, body := b, hash := sha256Hex (k ++ "|" ++ b) }
      entries := entries.push e
    let sorted := entries.qsort (fun a b => a.key < b.key)
    let text := "\n".intercalate (sorted.toList.map fun e => s!"{e.key}\t{e.kind}\t{e.body}")
    -- external types, hashed without following their own references
    let exts := (← get).externals.toList.toArray.qsort (fun a b => a.2.name < b.2.name)
    let mut extOut : Array (ExtRef × String) := #[]
    for (n, r) in exts do
      let saved ← get
      let some ci := env.find? n | continue
      let th ← withReader (fun c => { c with lps := ci.levelParams.toArray, stack := #[] }) do
        modify fun s => { s with cache := {} }
        ser ci.type
      set saved
      extOut := extOut.push (r, sha256Hex th)
    return { kind := rk, hash := sha256Hex text, entries := sorted, externals := extOut,
             serialization := text }
  let (r, _) ← (act.run { cfg }).run {}
  return some r

end StatementHash
