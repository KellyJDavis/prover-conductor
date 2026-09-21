"""SPIKE-03 fixture cases: pairs (before, after) of small Lean modules.

Every module is compiled as `Fix` (so the module name is identical before and after) and the
declarations in `decls` are hashed.  `kind` is what the hash SHOULD do:

- "benign":  hash equal before and after
- "meaning": hash differs
- "design":  the outcome follows a design decision (documented in the case note)
- "extra":   informative cases (semantic equivalences, external changes)

`expect` is the outcome the design specifies ("same" or "differ").  `gap` is set when the observed
behaviour is NOT what one would want; the test then asserts the observed behaviour and the gap text
is reported in the findings.

Sources are ASCII: the lambda sign is written with a unicode escape where a case needs it.
"""

from dataclasses import dataclass, field
from textwrap import dedent


@dataclass
class Case:
    id: str
    kind: str
    before: str | dict[str, str]
    after: str | dict[str, str]
    decls: tuple[str, ...] = ("thm",)
    # declaration names in the after variant, if different (rename of the locked declaration)
    after_decls: tuple[str, ...] = ()
    expect: str = "same"
    note: str = ""
    gap: str = ""
    # extra command line arguments for the tool, e.g. ("--no-binder-infos",)
    args: tuple[str, ...] = field(default_factory=tuple)
    # compare only the external reference list rather than the hash
    externals: bool = False


def src(text: str) -> str:
    return dedent(text).lstrip("\n")


BASE = src("""
    def double (n : Nat) : Nat := n + n
    theorem thm (n : Nat) (h : 0 < n) : n < double n := by unfold double; omega
""")

LAMBDA = "\u03bb"

CASES: list[Case] = []


def add(**kw: object) -> None:
    CASES.append(Case(**kw))  # type: ignore[arg-type]


# ---------------------------------------------------------------- benign
add(
    id="b01_bound_variable_rename",
    kind="benign",
    before=src("""
        theorem thm (n : Nat) : forall k : Nat, n + k = k + n := by intro k; omega
    """),
    after=src("""
        theorem thm (m : Nat) : forall j : Nat, m + j = j + m := by intro j; omega
    """),
    note="binder names are dropped",
)
add(
    id="b02_whitespace_and_comments",
    kind="benign",
    before=BASE,
    after=src("""
        /-! module doc -/
        -- a comment
        def double
            (n : Nat) : Nat :=
          n + n   -- trailing

        /- block -/
        theorem thm
            (n : Nat)
            (h : 0 < n) :
            n < double n := by
          unfold double
          omega
    """),
)
add(
    id="b03_reorder_unrelated",
    kind="benign",
    before=src("""
        def other (n : Nat) : Nat := n * 3
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    after=src("""
        def double (n : Nat) : Nat := n + n
        def other (n : Nat) : Nat := n * 3
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
)
add(
    id="b04_change_locked_proof",
    kind="benign",
    before=BASE,
    after=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) (h : 0 < n) : n < double n := by
          simp only [double]
          omega
    """),
)
add(
    id="b05_change_closure_lemma_proof",
    kind="benign",
    before=src("""
        theorem half_le (n : Nat) : n / 2 <= n := by omega
        def half (n : Nat) : { m : Nat // m <= n } := \u27e8n / 2, half_le n\u27e9
        theorem thm (n : Nat) : (half n).val <= n := (half n).property
    """),
    after=src("""
        theorem half_le (n : Nat) : n / 2 <= n := Nat.div_le_self n 2
        def half (n : Nat) : { m : Nat // m <= n } := \u27e8n / 2, half_le n\u27e9
        theorem thm (n : Nat) : (half n).val <= n := (half n).property
    """),
    note="the lemma is only used inside a proof term in a def value: erased, not in closure",
)
add(
    id="b06_change_proof_inside_def_value",
    kind="benign",
    before=src("""
        def half (n : Nat) : { m : Nat // m <= n } := \u27e8n / 2, by omega\u27e9
        theorem thm (n : Nat) : (half n).val <= n := (half n).property
    """),
    after=src("""
        def half (n : Nat) : { m : Nat // m <= n } := \u27e8n / 2, Nat.div_le_self n 2\u27e9
        theorem thm (n : Nat) : (half n).val <= n := (half n).property
    """),
    note="proof arguments inside definition values are erased",
)
add(
    id="b07_universe_param_rename",
    kind="benign",
    before=src("""
        universe u
        def Twice {A : Type u} (f : A -> A) (a : A) : A := f (f a)
        theorem thm.{v} {B : Type v} (b : B) : Twice id b = b := rfl
    """),
    after=src("""
        universe w
        def Twice {G : Type w} (g : G -> G) (a : G) : G := g (g a)
        theorem thm.{z} {B : Type z} (b : B) : Twice id b = b := rfl
    """),
    note="universe parameters are canonicalized by position in the declaration's level params",
)
add(
    id="b08_instance_binder_rename",
    kind="benign",
    before=src("""
        theorem thm {A : Type} [inst : Inhabited A] : exists a : A, a = default :=
          \u27e8default, rfl\u27e9
    """),
    after=src("""
        theorem thm {A : Type} [i : Inhabited A] : exists a : A, a = default :=
          \u27e8default, rfl\u27e9
    """),
)
add(
    id="b08b_instance_binder_anonymous",
    kind="benign",
    before=src("""
        theorem thm {A : Type} [inst : Inhabited A] : exists a : A, a = default :=
          \u27e8default, rfl\u27e9
    """),
    after=src("""
        theorem thm {A : Type} [Inhabited A] : exists a : A, a = default :=
          \u27e8default, rfl\u27e9
    """),
)
add(
    id="b09_add_unrelated_declaration",
    kind="benign",
    before=BASE,
    after=BASE
    + src("""
        def unrelated (s : String) : Nat := s.length
        structure Foo where (a : Nat)
        theorem unrelated_thm : 1 + 1 = 2 := rfl
    """),
)
add(
    id="b10_docstring_change",
    kind="benign",
    before=src("""
        /-- Doubling. -/
        def double (n : Nat) : Nat := n + n
        /-- old docstring -/
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    after=src("""
        /-- Doubling, described differently. -/
        def double (n : Nat) : Nat := n + n
        /-- A totally different docstring. -/
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
)
add(
    id="b11_unrelated_variable_in_scope",
    kind="benign",
    before=BASE,
    after=src("""
        variable (unused : Nat) {B : Type} [Inhabited B]
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) (h : 0 < n) : n < double n := by unfold double; omega
    """),
    note="variables not mentioned by the statement are not included by Lean",
)
add(
    id="b12_unused_open",
    kind="benign",
    before=BASE,
    after="open List Nat in\n" + BASE.replace("def double", "def double", 1) + "\nopen String\n",
    note="'open Nat in' is wrapped around the first def only; the statement resolves the same",
)
add(
    id="b13_lambda_spelling",
    kind="benign",
    before=src("""
        def adder (k : Nat) : Nat -> Nat := fun x => x + k
        theorem thm (k : Nat) : adder k 0 = k := by simp [adder]
    """),
    after=src("""
        def adder (k : Nat) : Nat -> Nat := %s x => x + k
        theorem thm (k : Nat) : adder k 0 = k := by simp [adder]
    """)
    % LAMBDA,
)
add(
    id="b14_section_wrapping",
    kind="benign",
    before=BASE,
    after="section Helpers\n" + BASE + "end Helpers\n",
    note="section (unlike namespace) does not change names",
)
add(
    id="b15_private_helper",
    kind="benign",
    before=src("""
        def helper (n : Nat) : Nat := n + 1
        theorem thm (n : Nat) : helper n = n + 1 := rfl
    """),
    after=src("""
        private def helper (n : Nat) : Nat := n + 1
        theorem thm (n : Nat) : helper n = n + 1 := rfl
    """),
    note="private-name mangling (_private.Fix.0.helper) is stripped",
)
add(
    id="b16_tactic_vs_term_proof",
    kind="benign",
    before=src("""
        theorem thm (a b : Nat) : a + b = b + a := Nat.add_comm a b
    """),
    after=src("""
        theorem thm (a b : Nat) : a + b = b + a := by
          induction a with
          | zero => simp
          | succ n ih => omega
    """),
)
add(
    id="b17_binder_grouping",
    kind="benign",
    before=src("""
        theorem thm (a b : Nat) (c : Nat) : a + b + c = c + b + a := by omega
    """),
    after=src("""
        theorem thm (a : Nat) (b : Nat) (c : Nat) : a + b + c = c + b + a := by omega
    """),
)
add(
    id="b18_auto_bound_vs_explicit_implicit",
    kind="benign",
    before=src("""
        theorem thm (x : A) : x = x := rfl
    """),
    after=src("""
        theorem thm.{u} {A : Sort u} (x : A) : x = x := rfl
    """),
    note="auto-bound universe u_1 / binder name A versus explicit ones: same canonical form",
)
add(
    id="b19_attributes_on_closure_def",
    kind="benign",
    before=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    after=src("""
        @[simp, reducible] def double (n : Nat) : Nat := n + n
        @[irreducible] def unusedIrr (n : Nat) : Nat := n
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    note="attributes (simp, reducible, irreducible) are not in the hash: DESIGN choice",
)
add(
    id="b20_notation_alias",
    kind="benign",
    before=src("""
        def double (n : Nat) : Nat := n + n
        local notation "dbl " x => double x
        theorem thm (n : Nat) : (dbl n) = n + n := rfl
    """),
    after=src("""
        def double (n : Nat) : Nat := n + n
        local notation "twice! " x:max => double x
        theorem thm (n : Nat) : (twice! n) = n + n := rfl
    """),
    note="different notation, same elaborated term",
)
add(
    id="b21_set_option_and_deriving",
    kind="benign",
    before=src("""
        structure P where (x y : Nat)
        theorem thm (p : P) : p.x + p.y = p.y + p.x := by omega
    """),
    after=src("""
        set_option maxHeartbeats 400000
        structure P where (x y : Nat)
          deriving Repr, DecidableEq, Inhabited
        theorem thm (p : P) : p.x + p.y = p.y + p.x := by omega
    """),
    note="derived instances are new constants that the statement does not mention",
)
add(
    id="b22_match_syntax_variants",
    kind="benign",
    before=src("""
        def f : Nat -> Nat
          | 0 => 1
          | n + 1 => f n * 2
        theorem thm : f 3 = 8 := by decide
    """),
    after=src("""
        def f (k : Nat) : Nat :=
          match k with
          | 0 => 1
          | n + 1 => f n * 2
        theorem thm : f 3 = 8 := by decide
    """),
    note="equation-compiler pattern definition vs match; aux matchers/_f hashed by content",
)
add(
    id="b23_theorem_keyword_vs_def_proof_term",
    kind="benign",
    before=src("""
        theorem thm (p q : Prop) (hp : p) (hq : q) : p /\\ q := And.intro hp hq
    """),
    after=src("""
        theorem thm (p q : Prop) (hp : p) (hq : q) : And p q := by exact \u27e8hp, hq\u27e9
    """),
    note="/\\ notation and And p q elaborate identically",
)

# ---------------------------------------------------------------- meaning-changing
add(
    id="m01_weaken_hypothesis",
    kind="meaning",
    before=BASE,
    after=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) (h : 0 <= n) : n < double n + 1 := by unfold double; omega
    """),
)
add(
    id="m02_strengthen_conclusion",
    kind="meaning",
    before=src("""
        theorem thm (a b : Nat) (h : a <= b) : a < b + 1 := by omega
    """),
    after=src("""
        theorem thm (a b : Nat) (h : a <= b) : a <= b + 1 := by omega
    """),
)
add(
    id="m03_change_closure_def_body",
    kind="meaning",
    before=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : double n = n + n := by unfold double; rfl
    """),
    after=src("""
        def double (n : Nat) : Nat := n + n + 1
        theorem thm (n : Nat) : double n = n + n := by sorry
    """),
    note="theorem text unchanged; only the definition in its closure changed (proof sorried)",
)
add(
    id="m04_change_structure_field_type",
    kind="meaning",
    before=src("""
        structure Cfg where
          size : Nat
          flag : Bool
        theorem thm (c : Cfg) : c.size = c.size := rfl
    """),
    after=src("""
        structure Cfg where
          size : Int
          flag : Bool
        theorem thm (c : Cfg) : c.size = c.size := rfl
    """),
)
add(
    id="m05_add_structure_field",
    kind="meaning",
    before=src("""
        structure Cfg where
          size : Nat
        theorem thm (c : Cfg) : c.size = c.size := rfl
    """),
    after=src("""
        structure Cfg where
          size : Nat
          extra : Nat := 0
        theorem thm (c : Cfg) : c.size = c.size := rfl
    """),
)
add(
    id="m06_local_instance_changes_elaboration",
    kind="meaning",
    before=src("""
        theorem thm (a b : Nat) : a + b = b + a := Nat.add_comm a b
    """),
    after=src("""
        instance : Add Nat := \u27e8Nat.mul\u27e9
        theorem thm (a b : Nat) : a + b = b + a := Nat.mul_comm a b
    """),
    note="text of the theorem statement is unchanged; the instance argument of HAdd differs",
)
add(
    id="m07_shadow_notation",
    kind="meaning",
    before=src("""
        theorem thm (a b : Nat) : a + b = b + a := Nat.add_comm a b
    """),
    after=src("""
        local macro_rules | `($a + $b) => `(Nat.mul $a $b)
        theorem thm (a b : Nat) : a + b = b + a := Nat.mul_comm a b
    """),
    note="same text, different elaboration through macro_rules on +",
)
add(
    id="m08_implicit_vs_explicit",
    kind="meaning",
    before=src("""
        theorem thm (n : Nat) (h : n = 1) : n + 0 = 1 := by omega
    """),
    after=src("""
        theorem thm {n : Nat} (h : n = 1) : n + 0 = 1 := by omega
    """),
    note="binder info is in the hash: the signature seen by users of the theorem changed",
)
add(
    id="m09_numeric_literal",
    kind="meaning",
    before=src("""
        theorem thm (n : Nat) (h : n = 2) : n + 2 = 4 := by omega
    """),
    after=src("""
        theorem thm (n : Nat) (h : n = 2) : n + 3 = 5 := by omega
    """),
)
add(
    id="m10_swap_argument_order",
    kind="meaning",
    before=src("""
        theorem thm (a b : Nat) (h : a <= b) : a - b = 0 := by omega
    """),
    after=src("""
        theorem thm (b a : Nat) (h : a <= b) : a - b = 0 := by omega
    """),
    note="binder names ignored, so this is a different statement: (b a) reads a-b as v1-v0",
)
add(
    id="m11_universe_level_structure",
    kind="meaning",
    before=src("""
        universe u
        theorem thm (A : Type u) (a : A) : a = a := rfl
    """),
    after=src("""
        theorem thm (A : Type) (a : A) : a = a := rfl
    """),
    note="universe polymorphic -> monomorphic",
)
add(
    id="m11b_type_vs_sort",
    kind="meaning",
    before=src("""
        universe u
        theorem thm (A : Type u) (a : A) : a = a := rfl
    """),
    after=src("""
        universe u
        theorem thm (A : Sort u) (a : A) : a = a := rfl
    """),
    note="Type u vs Sort u: strictly stronger statement",
)
add(
    id="m12_instance_argument_class",
    kind="meaning",
    before=src("""
        theorem thm {a : Type} [Inhabited a] : exists x : a, x = x := \u27e8default, rfl\u27e9
    """),
    after=src("""
        theorem thm {a : Type} [Nonempty a] : exists x : a, x = x :=
          let \u27e8v\u27e9 := \u2039Nonempty a\u203a; \u27e8v, rfl\u27e9
    """),
)
add(
    id="m13_inst_implicit_to_explicit",
    kind="meaning",
    before=src("""
        theorem thm {a : Type} [Inhabited a] : exists x : a, x = default :=
          \u27e8default, rfl\u27e9
    """),
    after=src("""
        theorem thm {a : Type} (i : Inhabited a) : exists x : a, x = default :=
          \u27e8default, rfl\u27e9
    """),
    note="instance-implicit binder info matters",
)
add(
    id="m14_auto_implicit_differs",
    kind="meaning",
    before=src("""
        variable {A : Type}
        theorem thm (xs : List A) : xs.length = xs.length := rfl
    """),
    after=src("""
        theorem thm (xs : List A) : xs.length = xs.length := rfl
    """),
    note="auto-bound A becomes universe polymorphic (Sort u_1) instead of Type",
)
add(
    id="m15_def_to_opaque",
    kind="meaning",
    before=src("""
        def c : Nat := 5
        theorem thm : c = 5 := rfl
    """),
    after=src("""
        opaque c : Nat
        theorem thm : c = 5 := sorry
    """),
    note="the closure loses c's value: opaque is a different kind of constant",
)
add(
    id="m16_change_instance_value",
    kind="meaning",
    before=src("""
        structure V where (x : Nat)
        instance : Add V := \u27e8fun a b => \u27e8a.x + b.x\u27e9\u27e9
        theorem thm (a b : V) : (a + b).x = a.x + b.x := rfl
    """),
    after=src("""
        structure V where (x : Nat)
        instance : Add V := \u27e8fun a b => \u27e8a.x * b.x\u27e9\u27e9
        theorem thm (a b : V) : (a + b).x = a.x + b.x := sorry
    """),
    note="statement text and elaborated statement identical; the local instance body changed",
)
add(
    id="m17_change_conclusion_relation",
    kind="meaning",
    before=src("""
        theorem thm (a b : Nat) (h : a < b) : a <= b := by omega
    """),
    after=src("""
        theorem thm (a b : Nat) (h : a < b) : a < b := h
    """),
)
add(
    id="m18_open_changes_resolution",
    kind="meaning",
    before=src("""
        namespace A
        def val : Nat := 1
        end A
        namespace B
        def val : Nat := 2
        end B
        open A in
        theorem thm : val = 1 := rfl
    """),
    after=src("""
        namespace A
        def val : Nat := 1
        end A
        namespace B
        def val : Nat := 2
        end B
        open B in
        theorem thm : val = 1 := sorry
    """),
    note="name resolution through `open` yields a different constant",
)
add(
    id="m19_structure_to_class",
    kind="meaning",
    before=src("""
        structure Pt where (x : Nat)
        theorem thm (p : Pt) : p.x = p.x := rfl
    """),
    after=src("""
        class Pt where (x : Nat)
        theorem thm (p : Pt) : p.x = p.x := rfl
    """),
    note="class flag is in the inductive entry (affects instance resolution)",
)
add(
    id="m20_inductive_constructor_added",
    kind="meaning",
    before=src("""
        inductive Color | red | green
        theorem thm : Color.red = Color.red := rfl
    """),
    after=src("""
        inductive Color | red | green | blue
        theorem thm : Color.red = Color.red := rfl
    """),
)
add(
    id="m21_coercion_instance_changed",
    kind="meaning",
    before=src("""
        structure W where (n : Nat)
        instance : Coe Nat W := \u27e8fun n => \u27e8n\u27e9\u27e9
        theorem thm (k : Nat) : ((k : Nat) : W).n = k := rfl
    """),
    after=src("""
        structure W where (n : Nat)
        instance : Coe Nat W := \u27e8fun n => \u27e8n + 1\u27e9\u27e9
        theorem thm (k : Nat) : ((k : Nat) : W).n = k := sorry
    """),
)
add(
    id="m22_structure_field_rename",
    kind="meaning",
    before=src("""
        structure Cfg where
          size : Nat
        theorem thm (c : Cfg) : c.size = c.size := rfl
    """),
    after=src("""
        structure Cfg where
          count : Nat
        theorem thm (c : Cfg) : c.count = c.count := rfl
    """),
    note="field names are part of the structure entry (and projections are referenced by name)",
)

# ---------------------------------------------------------------- design decisions
add(
    id="d01_rename_local_def",
    kind="design",
    expect="differ",
    before=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    after=src("""
        def twice (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : twice n = n + n := rfl
    """),
    note="local constants are referenced by name: renaming is NOT benign (re-approval)",
)
add(
    id="d02_rename_locked_theorem_itself",
    kind="design",
    expect="same",
    decls=("thm",),
    after_decls=("thm_renamed",),
    before=src("""
        theorem thm (n : Nat) : n + 0 = n := rfl
    """),
    after=src("""
        theorem thm_renamed (n : Nat) : n + 0 = n := rfl
    """),
    note="the root name is not part of its hash (the lock file keys by name)",
)
add(
    id="d03_binder_info_off",
    kind="design",
    expect="same",
    args=("--no-binder-infos",),
    before=src("""
        theorem thm (n : Nat) (h : n = 1) : n + 0 = 1 := by omega
    """),
    after=src("""
        theorem thm {n : Nat} (h : n = 1) : n + 0 = 1 := by omega
    """),
    note="with --no-binder-infos, implicit vs explicit is invisible (rejected as default)",
)

# ---------------------------------------------------------------- extras / limitations
add(
    id="x01_semantically_equal_def_body",
    kind="extra",
    expect="differ",
    before=src("""
        def double (n : Nat) : Nat := n + n
        theorem thm (n : Nat) : double n = n + n := rfl
    """),
    after=src("""
        def double (n : Nat) : Nat := 2 * n
        theorem thm (n : Nat) : double n = n + n := by unfold double; omega
    """),
    note="extensionally equal body, different term: hash differs (conservative, by design)",
)
add(
    id="x02_semantically_equal_statement",
    kind="extra",
    expect="differ",
    before=src("""
        theorem thm (a b : Nat) : a > b -> b < a := fun h => h
    """),
    after=src("""
        theorem thm (a b : Nat) : b < a -> b < a := fun h => h
    """),
    note="GT.gt a b is defeq to LT.lt b a but a different term: over-sensitive, by design",
)
add(
    id="x03_ne_vs_not_eq",
    kind="extra",
    expect="differ",
    before=src("""
        theorem thm (a b : Nat) (h : a \u2260 b) : b \u2260 a := fun e => h e.symm
    """),
    after=src("""
        theorem thm (a b : Nat) (h : \u00ac a = b) : \u00ac b = a := fun e => h e.symm
    """),
    note="Ne vs Not/Eq: same meaning, different terms",
)
add(
    id="x04_anonymous_instance_name_swap",
    kind="extra",
    expect="same",
    gap="anonymous instances get auto names (instAddV, instAddV_1) by declaration order; "
    "reordering two instances of the same class swaps their names and changes the hash",
    before=src("""
        structure V where (x : Nat)
        instance : Add V := \u27e8fun a b => \u27e8a.x + b.x\u27e9\u27e9
        instance (priority := low) : Add V := \u27e8fun a b => \u27e8a.x * b.x\u27e9\u27e9
        theorem thm (a b : V) : (a + b).x = a.x + b.x := rfl
    """),
    after=src("""
        structure V where (x : Nat)
        instance (priority := low) : Add V := \u27e8fun a b => \u27e8a.x * b.x\u27e9\u27e9
        instance : Add V := \u27e8fun a b => \u27e8a.x + b.x\u27e9\u27e9
        theorem thm (a b : V) : (a + b).x = a.x + b.x := rfl
    """),
    note="reordering instance declarations: ideally benign (same elaborated statement)",
)
add(
    id="x05_external_body_change_invisible",
    kind="extra",
    expect="differ",
    before={
        "Lib": src("""
            def libval : Nat := 1
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    after={
        "Lib": src("""
            def libval : Nat := 2
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    note="Lib is outside the local root: its VALUE change is invisible (type hash only)",
    gap="a changed external definition VALUE changes neither hash nor externals typeHash",
)
add(
    id="x06_external_type_change_visible_in_externals",
    kind="extra",
    expect="differ",
    externals=True,
    before={
        "Lib": src("""
            def libval : Nat := 1
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    after={
        "Lib": src("""
            def libval : Int := 1
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    note="the external's type changed: the externalReferences typeHash differs",
)
add(
    id="x07_local_def_in_second_module",
    kind="extra",
    expect="differ",
    args=("--local-root", "Fix", "--local-root", "Lib"),
    before={
        "Lib": src("""
            def libval : Nat := 1
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    after={
        "Lib": src("""
            def libval : Nat := 2
        """),
        "Fix": src("""
            import Lib
            theorem thm : libval = libval := rfl
        """),
    },
    note="with Lib declared project-local, its value change IS detected",
)
add(
    id="x08_rename_universe_in_def_value",
    kind="extra",
    expect="same",
    before=src("""
        def idd.{u} {A : Sort u} (a : A) : A := a
        theorem thm : idd 1 = 1 := rfl
    """),
    after=src("""
        def idd.{w} {A : Sort w} (a : A) : A := a
        theorem thm : idd 1 = 1 := rfl
    """),
)
add(
    id="x09_universe_param_order_swap",
    kind="extra",
    expect="differ",
    before=src("""
        def pair.{u, v} (A : Type u) (B : Type v) : Type (max u v) := A \u00d7 B
        theorem thm : pair.{0, 0} Nat Nat = (Nat \u00d7 Nat) := rfl
    """),
    after=src("""
        def pair.{v, u} (A : Type u) (B : Type v) : Type (max u v) := A \u00d7 B
        theorem thm : pair.{0, 0} Nat Nat = (Nat \u00d7 Nat) := sorry
    """),
    note="swapping the declared level-parameter order changes the signature: differs",
)
add(
    id="x10_irreducible_via_opaque_wrapper_kind",
    kind="extra",
    expect="same",
    before=src("""
        def c : Nat := 5
        theorem thm : c + 0 = c := rfl
    """),
    after=src("""
        @[irreducible] def c : Nat := 5
        theorem thm : c + 0 = c := by simp
    """),
    note="@[irreducible] alone does not change the hash (documented decision)",
)
