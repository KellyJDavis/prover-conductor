"""SPIKE-03: the statement hash is stable under benign edits and changes under meaning changes.

Needs a Lean toolchain (leanprover/lean4:v4.33.1 via elan); builds the tool in spikes/SPIKE-03/hash.
Run: uv run pytest -m lean spikes/SPIKE-03
"""

import hashlib
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from cases import CASES, Case
from harness import HERE, Setup, build_tool, compile_variant, run_tool, setup_for_toolchain

pytestmark = pytest.mark.lean


@pytest.fixture(scope="session", autouse=True)
def tool() -> None:
    build_tool()


def observe(case: Case) -> tuple[list[str], list[str]]:
    """Per-declaration comparison keys of the two variants."""
    keys: list[list[str]] = []
    for variant, files in (("before", case.before), ("after", case.after)):
        path = compile_variant(f"{case.id}/{variant}", files)
        names = case.decls if variant == "before" or not case.after_decls else case.after_decls
        res = run_tool(path, names, case.args)
        row: list[str] = []
        for d in names:
            assert res[d]["exists"], f"{d} missing in {variant}"
            if case.externals:
                row.append(repr(res[d]["externalReferences"]))
            else:
                row.append(res[d]["hash"])
        keys.append(row)
    return keys[0], keys[1]


@pytest.mark.parametrize("case", CASES, ids=[c.id for c in CASES])
def test_case(case: Case) -> None:
    before, after = observe(case)
    observed = "same" if before == after else "differ"
    if case.gap:
        # a known limitation: the observed outcome is NOT the wanted one, and is pinned here
        wanted = case.expect
        assert observed != wanted, f"gap no longer present: {case.gap}"
        return
    if case.kind == "benign":
        assert observed == "same", case.note
    elif case.kind == "meaning":
        assert observed == "differ", case.note
    else:
        assert observed == case.expect, case.note


def test_case_counts() -> None:
    benign = [c for c in CASES if c.kind == "benign"]
    meaning = [c for c in CASES if c.kind == "meaning"]
    assert len(benign) >= 10
    assert len(meaning) >= 10


def test_hash_is_sha256_of_serialization_and_deterministic() -> None:
    case = next(c for c in CASES if c.id == "b05_change_closure_lemma_proof")
    path = compile_variant("selfcheck", case.before)
    first = run_tool(path, ("thm",), serialize=True)["thm"]
    second = run_tool(path, ("thm",), serialize=True)["thm"]
    assert first == second
    assert hashlib.sha256(first["serialization"].encode()).hexdigest() == first["hash"]


def test_missing_declaration_reported() -> None:
    path = compile_variant("missing", "theorem thm : True := trivial\n")
    res = run_tool(path, ("nope",))
    assert res["nope"] == {"name": "nope", "exists": False}


def test_theorem_closure_excludes_proof_only_dependencies() -> None:
    case = next(c for c in CASES if c.id == "b05_change_closure_lemma_proof")
    path = compile_variant("closure", case.before)
    entries = {e["name"] for e in run_tool(path, ("thm",))["thm"]["closure"]}
    assert "half" in entries
    assert "half_le" not in entries


def test_external_references_listed_with_module() -> None:
    files = {
        "Lib": "def libval : Nat := 1\n",
        "Fix": "import Lib\ntheorem thm : libval = libval := rfl\n",
    }
    path = compile_variant("externals", files)
    d = run_tool(path, ("thm",))["thm"]
    ext = {e["name"]: e for e in d["externalReferences"]}
    assert ext["libval"]["module"] == "Lib"
    assert ext["Eq"]["module"].startswith("Init")
    assert "libval" not in {e["name"] for e in d["closure"]}


def test_initializers_of_inspected_module_do_not_run() -> None:
    marker = HERE / "work" / "initializer-ran.txt"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.unlink(missing_ok=True)
    text = (
        f'initialize initMarker : Unit <- IO.FS.writeFile "{marker}" "ran"\n'
        "theorem thm : True := trivial\n"
    )
    path = compile_variant("init", text)
    marker.unlink(missing_ok=True)  # compiling alone does not run it; be sure
    res = run_tool(path, ("thm",))
    assert res["thm"]["exists"]
    assert not marker.exists()


# ---------------------------------------------------------------- Mathlib (optional)
# Set SPIKE03_MATHLIB to a BUILT Mathlib checkout whose toolchain is installed in elan; the tool is
# rebuilt from the same sources with that toolchain (also a cross-version check).

MATHLIB_HEADER = "import Mathlib\n"
ML_BEFORE = (
    MATHLIB_HEADER
    + """
def mysq (n : Nat) : Nat := n * n
theorem thm {G : Type*} [inst : Group G] (a b : G) : a * b * b\u207b\u00b9 = a := by simp
theorem thm2 (n : Nat) : \u2211 i \u2208 Finset.range (n + 1), i = n * (n + 1) / 2 := by sorry
theorem thm3 (n : Nat) : mysq n = n * n := rfl
"""
)
ML_BENIGN = (
    MATHLIB_HEADER
    + """
def mysq (n : Nat) : Nat := n * n
theorem thm {H : Type _} [Group H] (x y : H) : x * y * y\u207b\u00b9 = x := by group
theorem thm2 (m : Nat) : \u2211 j \u2208 Finset.range (m + 1), j = m * (m + 1) / 2 := by
  sorry
theorem thm3 (n : Nat) : mysq n = n * n := by simp [mysq]
"""
)
ML_MEANING = (
    MATHLIB_HEADER
    + """
def mysq (n : Nat) : Nat := n * n + 1
theorem thm {G : Type*} [inst : CommGroup G] (a b : G) : a * b * b\u207b\u00b9 = a := by simp
theorem thm2 (n : Nat) : \u2211 i \u2208 Finset.range n, i = n * (n + 1) / 2 := by sorry
theorem thm3 (n : Nat) : mysq n = n * n := sorry
"""
)


@pytest.fixture(scope="module")
def mathlib() -> Setup:
    root = os.environ.get("SPIKE03_MATHLIB")
    if not root:
        pytest.skip("set SPIKE03_MATHLIB to a built Mathlib checkout to run the Mathlib cases")
    rootp = Path(root)
    toolchain = (rootp / "lean-toolchain").read_text().strip()
    entries = [rootp / ".lake" / "build" / "lib" / "lean"]
    entries += sorted((rootp / ".lake" / "packages").glob("*/.lake/build/lib/lean"))
    return setup_for_toolchain(toolchain, tuple(str(e) for e in entries))


def test_mathlib_benign_and_meaning_changes(mathlib: Setup) -> None:
    names = ("thm", "thm2", "thm3")
    res: dict[str, dict[str, dict]] = {}  # type: ignore[type-arg]
    for label, text in (("before", ML_BEFORE), ("benign", ML_BENIGN), ("meaning", ML_MEANING)):
        path = compile_variant(f"mathlib/{label}", text, mathlib)
        res[label] = run_tool(path, names, setup=mathlib)
    for n in names:
        assert res["before"][n]["hash"] == res["benign"][n]["hash"], n
        assert res["before"][n]["hash"] != res["meaning"][n]["hash"], n
    # Mathlib constants are external references, listed with their module
    ext = {e["name"]: e["module"] for e in res["before"]["thm2"]["externalReferences"]}
    assert ext["Finset.sum"].startswith("Mathlib")
    assert "mysq" in {e["name"] for e in res["before"]["thm3"]["closure"]}
