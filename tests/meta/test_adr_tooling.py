"""ADR tooling: INV-0000-1, INV-0000-2 and INV-0000-5, on this repository and on fixtures."""

from __future__ import annotations

from pathlib import Path

import adr_tools
import check_invariants
import gen_adr_rules
import pytest

ROOT = Path(__file__).resolve().parents[2]
# Fixture IDs are assembled at runtime so this file never mentions an undefined invariant.
PREFIX = "INV-"
FIXTURE_ID = PREFIX + "0001-1"


def test_repository_passes_invariant_check() -> None:
    """INV-0000-1: every enforcement reference exists and every entry names a defined invariant."""
    report = check_invariants.run_checks(ROOT)
    assert report.errors == []


def test_generated_rules_are_current() -> None:
    """INV-0000-2: .claude/rules/adr matches what gen_adr_rules.py generates."""
    assert gen_adr_rules.main(["--check", "--root", str(ROOT)]) == 0


def write_adr(
    root: Path, *, status: str, applies_to: str = "src/pkg/**", enforced_by: str | None = None
) -> None:
    adr_dir = root / "docs" / "adr"
    adr_dir.mkdir(parents=True, exist_ok=True)
    (adr_dir / "README.md").write_text(f"| ADR-0001 | {status} | Example |\n", encoding="utf-8")
    lines = [
        "---",
        "id: ADR-0001",
        "title: Example",
        f"status: {status}",
        "date: 2026-09-20",
        "summary: An example decision.",
        "applies_to:",
        f'  - "{applies_to}"',
        "invariants:",
        f"  - id: {FIXTURE_ID}",
        "    text: Something checkable.",
    ]
    if enforced_by is not None:
        lines.append(f"    enforced_by: {enforced_by}")
    lines += ["revisit_when: Never.", "---", "", "## Context", ""]
    (adr_dir / "0001-example.md").write_text("\n".join(lines), encoding="utf-8")


def write_enforcement(
    root: Path, *, refs: tuple[str, ...] = (), scope: tuple[str, ...] = ()
) -> None:
    lines = [f"{FIXTURE_ID}:", "  enforced_by:" + ("" if refs else " []")]
    lines += [f"    - {ref}" for ref in refs]
    if scope:
        lines.append("  scope:")
        lines += [f'    - "{glob}"' for glob in scope]
    path = root / adr_tools.ENFORCEMENT_FILE
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_code(root: Path, rel_path: str = "src/pkg/impl.py") -> None:
    path = root / rel_path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("VALUE = 1\n", encoding="utf-8")


def errors(root: Path) -> list[str]:
    return check_invariants.run_checks(root).errors


def test_unscoped_debt_is_only_a_warning(tmp_path: Path) -> None:
    write_adr(tmp_path, status="accepted")
    write_code(tmp_path)
    report = check_invariants.run_checks(tmp_path)
    assert report.errors == []
    assert len(report.debts) == 1


def test_scoped_debt_is_an_error(tmp_path: Path) -> None:
    """INV-0000-5: real code in an entry's scope makes an accepted invariant's enforcement due."""
    write_adr(tmp_path, status="accepted")
    write_enforcement(tmp_path, scope=("src/pkg/**",))
    package = tmp_path / "src" / "pkg"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text('"""Docstring only."""\n', encoding="utf-8")
    assert errors(tmp_path) == []
    write_code(tmp_path)
    assert any("code exists in its scope" in error for error in errors(tmp_path))


def test_scope_does_not_bind_proposed_adrs(tmp_path: Path) -> None:
    write_adr(tmp_path, status="proposed")
    write_enforcement(tmp_path, scope=("src/pkg/**",))
    write_code(tmp_path)
    assert errors(tmp_path) == []


def test_enforcing_test_must_mention_the_invariant(tmp_path: Path) -> None:
    write_adr(tmp_path, status="accepted")
    write_enforcement(tmp_path, refs=("test:tests/test_example.py::test_example",))
    (tmp_path / "tests").mkdir()
    test_file = tmp_path / "tests" / "test_example.py"
    test_file.write_text("def test_example():\n    pass\n", encoding="utf-8")
    assert any("does not mention" in error for error in errors(tmp_path))
    test_file.write_text(f'def test_example():\n    """{FIXTURE_ID}"""\n', encoding="utf-8")
    assert errors(tmp_path) == []


def test_missing_enforcing_test_is_an_error(tmp_path: Path) -> None:
    write_adr(tmp_path, status="accepted")
    write_enforcement(tmp_path, refs=("test:tests/test_gone.py::test_gone",))
    assert any("does not exist" in error for error in errors(tmp_path))


def test_entries_must_name_defined_invariants(tmp_path: Path) -> None:
    write_adr(tmp_path, status="proposed")
    path = tmp_path / adr_tools.ENFORCEMENT_FILE
    path.write_text(f"{PREFIX}0042-7:\n  enforced_by: []\n", encoding="utf-8")
    assert any("not defined by any ADR" in error for error in errors(tmp_path))


@pytest.mark.parametrize("status", ["proposed", "accepted"])
def test_adrs_carry_no_enforced_by(tmp_path: Path, status: str) -> None:
    write_adr(tmp_path, status=status, enforced_by="TODO")
    assert any("carries enforced_by" in error for error in errors(tmp_path))


def test_references_to_unknown_invariants_are_errors(tmp_path: Path) -> None:
    write_adr(tmp_path, status="proposed")
    (tmp_path / "tests").mkdir()
    stale = tmp_path / "tests" / "test_stale.py"
    stale.write_text(f'"""Enforces {PREFIX}0042-7."""\n', encoding="utf-8")
    assert any("unknown invariant" in error for error in errors(tmp_path))


def test_index_must_list_each_adr_with_its_status(tmp_path: Path) -> None:
    write_adr(tmp_path, status="proposed")
    readme = tmp_path / "docs" / "adr" / "README.md"
    readme.write_text("| ADR-0001 | accepted | Example |\n", encoding="utf-8")
    assert any("README.md" in error for error in errors(tmp_path))


def test_malformed_frontmatter_is_an_error(tmp_path: Path) -> None:
    adr_dir = tmp_path / "docs" / "adr"
    adr_dir.mkdir(parents=True)
    (adr_dir / "0001-broken.md").write_text("no frontmatter here\n", encoding="utf-8")
    assert any("frontmatter" in error for error in errors(tmp_path))


def test_worktrees_are_not_scanned(tmp_path: Path) -> None:
    write_adr(tmp_path, status="accepted", applies_to="**/*.py")
    write_enforcement(tmp_path, scope=("**/*.py",))
    write_code(tmp_path, ".claude/worktrees/spike-01/impl.py")
    assert errors(tmp_path) == []


def test_generated_rule_is_path_scoped(tmp_path: Path) -> None:
    write_adr(tmp_path, status="accepted")
    assert gen_adr_rules.main(["--root", str(tmp_path)]) == 0
    rule_path = tmp_path / ".claude" / "rules" / "adr" / "0001-example.md"
    rule = rule_path.read_text(encoding="utf-8")
    assert rule.startswith('---\npaths:\n  - "src/pkg/**"\n---\n')
    assert "Binding for the files that loaded this rule." in rule
    assert f"- {FIXTURE_ID}: Something checkable.\n" in rule
    assert adr_tools.ENFORCEMENT_FILE in rule
    assert gen_adr_rules.main(["--check", "--root", str(tmp_path)]) == 0
    rule_path.write_text(rule + "hand edit\n", encoding="utf-8")
    assert gen_adr_rules.main(["--check", "--root", str(tmp_path)]) == 1


def test_globs_support_double_star_and_braces() -> None:
    assert adr_tools.matches("src/pkg/sub/mod.py", ["src/pkg/**"])
    assert adr_tools.matches("a/b/c.lean", ["**/*.lean"])
    assert adr_tools.matches("c.lean", ["**/*.lean"])
    assert adr_tools.matches("deploy/ray.yaml", ["deploy/*.{yaml,yml}"])
    assert not adr_tools.matches("src/other/mod.py", ["src/pkg/**"])
    assert not adr_tools.matches("src/pkg/sub/mod.py", ["src/pkg/*"])
