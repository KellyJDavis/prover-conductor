"""Validate ADRs and the enforcement of their invariants (ADR-0000, INV-0000-1, INV-0000-5).

Enforcement is recorded in docs/adr/enforcement.yaml. Exit status 1 on errors. An invariant
without enforcement is reported as debt; it is an error only when its ADR is accepted, its entry
declares a scope, and real code exists in that scope.
"""

from __future__ import annotations

import argparse
import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import adr_tools
from adr_tools import Adr, Enforcement

ROOT = Path(__file__).resolve().parents[1]
TEST_REF = re.compile(r"^test:(?P<path>[^:]+\.py)::(?P<name>[A-Za-z_]\w*)$")
CI_REF = re.compile(r"^ci:(?P<path>[^#]+)#(?P<step>[A-Za-z_][\w-]*)$")
# Where invariant IDs may be referenced; every reference must name a defined invariant.
REFERENCE_ROOTS = ("tests", "src", "scripts", ".claude/hooks", ".github")
REFERENCE_FILES = ("pyproject.toml",)
REFERENCE_SUFFIXES = (".py", ".yml", ".yaml", ".toml")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)
    debts: list[str] = field(default_factory=list)
    adr_count: int = 0
    invariant_count: int = 0
    enforced_count: int = 0


@dataclass
class _Context:
    root: Path
    contracts: dict[str, dict[str, Any]]
    settings_text: str
    codeowner_patterns: set[str]
    files: list[str] | None = None

    def governed_code(self, patterns: tuple[str, ...]) -> list[str]:
        if self.files is None:
            self.files = list(adr_tools.repo_files(self.root))
        return [
            path
            for path in self.files
            if adr_tools.matches(path, patterns) and not adr_tools.is_trivial(self.root, path)
        ]


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8") if path.is_file() else ""


def _load_context(root: Path) -> _Context:
    contracts: dict[str, dict[str, Any]] = {}
    pyproject = root / "pyproject.toml"
    if pyproject.is_file():
        data = tomllib.loads(pyproject.read_text(encoding="utf-8"))
        for contract in data.get("tool", {}).get("importlinter", {}).get("contracts", []):
            if isinstance(contract, dict) and "id" in contract:
                contracts[str(contract["id"])] = contract
    patterns: set[str] = set()
    for line in _read(root / ".github" / "CODEOWNERS").splitlines():
        stripped = line.strip()
        if stripped and not stripped.startswith("#"):
            patterns.add(stripped.split()[0])
    return _Context(
        root=root,
        contracts=contracts,
        settings_text=_read(root / ".claude" / "settings.json"),
        codeowner_patterns=patterns,
    )


def reference_problem(root: Path, ref: str, invariant_id: str, ctx: _Context) -> str | None:
    """Return why an enforcement reference is invalid, or None if it checks out."""
    if ref.startswith("test:"):
        match = TEST_REF.match(ref)
        if match is None:
            return "malformed reference; expected test:<path>.py::<test_name>"
        path, name = match.group("path"), match.group("name")
        source = _read(root / path)
        if not source:
            return f"test file {path} does not exist"
        if not re.search(rf"^\s*def {re.escape(name)}\(", source, re.MULTILINE):
            return f"test {name} not found in {path}"
        if invariant_id not in source:
            return f"{path} does not mention {invariant_id}"
        return None
    if ref.startswith("import-linter:"):
        contract_id = ref.removeprefix("import-linter:")
        contract = ctx.contracts.get(contract_id)
        if contract is None:
            return f"no import-linter contract with id '{contract_id}' in pyproject.toml"
        if invariant_id not in str(contract.get("name", "")):
            return f"import-linter contract '{contract_id}' does not mention {invariant_id}"
        return None
    if ref.startswith("hook:"):
        rel = ref.removeprefix("hook:")
        if not (root / rel).is_file():
            return f"hook {rel} does not exist"
        if Path(rel).name not in ctx.settings_text:
            return f"hook {rel} is not registered in .claude/settings.json"
        return None
    if ref.startswith("ci:"):
        match = CI_REF.match(ref)
        if match is None:
            return "malformed reference; expected ci:<workflow path>#<step id>"
        path, step = match.group("path"), match.group("step")
        text = _read(root / path)
        if not text:
            return f"workflow {path} does not exist"
        if not re.search(rf"^\s*(?:-\s+)?id:\s*{re.escape(step)}\s*$", text, re.MULTILINE):
            return f"step id '{step}' not found in {path}"
        if invariant_id not in text:
            return f"{path} does not mention {invariant_id}"
        return None
    if ref.startswith("codeowners:"):
        pattern = ref.removeprefix("codeowners:")
        if pattern not in ctx.codeowner_patterns:
            return f".github/CODEOWNERS has no entry for {pattern}"
        return None
    return f"unknown enforcement kind in '{ref}'"


def _check_identity(adrs: list[Adr], report: Report) -> None:
    seen_adrs: set[str] = set()
    seen_invariants: set[str] = set()
    for adr in adrs:
        if adr.id in seen_adrs:
            report.errors.append(f"{adr.rel_path}: duplicate ADR id {adr.id}")
        seen_adrs.add(adr.id)
        for invariant in adr.invariants:
            if invariant.id in seen_invariants:
                report.errors.append(f"{adr.rel_path}: duplicate invariant id {invariant.id}")
            seen_invariants.add(invariant.id)


def _check_links(root: Path, adrs: list[Adr], report: Report) -> None:
    ids = {adr.id for adr in adrs}
    for adr in adrs:
        for other in adr.depends_on:
            if other not in ids:
                report.errors.append(f"{adr.id}: depends_on names unknown {other}")
        if adr.superseded_by is not None and adr.superseded_by not in ids:
            report.errors.append(f"{adr.id}: superseded_by names unknown {adr.superseded_by}")
        for spike in adr.settled_by:
            if not adr_tools.SPIKE_ID.match(spike):
                report.errors.append(f"{adr.id}: settled_by entry '{spike}' is not SPIKE-NN")
            elif not list((root / "docs" / "spikes").glob(f"{spike}-*.md")):
                report.errors.append(f"{adr.id}: no docs/spikes/{spike}-*.md for settled_by")


def _check_index(root: Path, adrs: list[Adr], report: Report) -> None:
    lines = _read(root / "docs" / "adr" / "README.md").splitlines()
    for adr in adrs:
        row = next((line for line in lines if f"| {adr.id} |" in line), None)
        if row is None:
            report.errors.append(f"docs/adr/README.md: index has no row for {adr.id}")
        elif f"| {adr.status} |" not in row:
            report.errors.append(f"docs/adr/README.md: index row for {adr.id} lacks '{adr.status}'")


def _check_enforcement(
    root: Path, adrs: list[Adr], enforcement: dict[str, Enforcement], report: Report
) -> None:
    defined = {invariant.id for adr in adrs for invariant in adr.invariants}
    for invariant_id in sorted(set(enforcement) - defined):
        report.errors.append(
            f"{adr_tools.ENFORCEMENT_FILE}: {invariant_id} is not defined by any ADR"
        )
    ctx = _load_context(root)
    for adr in adrs:
        if adr.status not in adr_tools.ACTIVE_STATUSES:
            continue
        for invariant in adr.invariants:
            report.invariant_count += 1
            entry = enforcement.get(invariant.id)
            refs = entry.refs if entry else ()
            if refs:
                problems = [
                    problem
                    for ref in refs
                    if (problem := reference_problem(root, ref, invariant.id, ctx)) is not None
                ]
                report.errors.extend(f"{adr.id} {invariant.id}: {p}" for p in problems)
                if not problems:
                    report.enforced_count += 1
                continue
            scope = entry.scope if entry else ()
            governed = ctx.governed_code(scope) if adr.status == "accepted" and scope else []
            if governed:
                more = f" and {len(governed) - 1} more" if len(governed) > 1 else ""
                report.errors.append(
                    f"{adr.id} {invariant.id}: not enforced, but code exists in its scope "
                    f"({governed[0]}{more}); add the enforcing test and record it in "
                    f"{adr_tools.ENFORCEMENT_FILE}"
                )
            else:
                scoped = " (scoped)" if scope else ""
                report.debts.append(f"{adr.id} ({adr.status}) {invariant.id}: not enforced{scoped}")


def _reference_files(root: Path) -> list[Path]:
    files = [root / name for name in REFERENCE_FILES if (root / name).is_file()]
    for rel in adr_tools.repo_files(root):
        if rel.startswith(tuple(f"{prefix}/" for prefix in REFERENCE_ROOTS)) and rel.endswith(
            REFERENCE_SUFFIXES
        ):
            files.append(root / rel)
    return files


def _check_references(root: Path, adrs: list[Adr], report: Report) -> None:
    defined = {invariant.id for adr in adrs for invariant in adr.invariants}
    for path in _reference_files(root):
        text = path.read_text(encoding="utf-8", errors="replace")
        for ref in sorted(set(adr_tools.INV_REF.findall(text)) - defined):
            rel = path.relative_to(root).as_posix()
            report.errors.append(f"{rel}: mentions unknown invariant {ref}")


def run_checks(root: Path) -> Report:
    report = Report()
    adrs, parse_errors = adr_tools.load_adrs(root)
    enforcement, enforcement_errors = adr_tools.load_enforcement(root)
    report.errors.extend(parse_errors)
    report.errors.extend(enforcement_errors)
    report.adr_count = len(adrs)
    _check_identity(adrs, report)
    _check_links(root, adrs, report)
    _check_index(root, adrs, report)
    _check_enforcement(root, adrs, enforcement, report)
    _check_references(root, adrs, report)
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ADRs and invariant enforcement.")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    parser.add_argument("--quiet", action="store_true", help="print errors only")
    args = parser.parse_args(argv)
    report = run_checks(Path(args.root).resolve())
    for error in report.errors:
        print(f"error: {error}")
    if not args.quiet:
        for debt in report.debts:
            print(f"debt:  {debt}")
        print(
            f"{report.adr_count} ADRs; {report.invariant_count} invariants in active ADRs: "
            f"{report.enforced_count} enforced, {len(report.debts)} not yet; "
            f"{len(report.errors)} errors"
        )
    return 1 if report.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
