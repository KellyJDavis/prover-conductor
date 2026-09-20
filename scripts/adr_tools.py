"""Parsing and path matching shared by the ADR scripts (ADR-0000)."""

from __future__ import annotations

import ast
import datetime as dt
import os
import re
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ADR_FILE = re.compile(r"^(\d{4})-[a-z0-9]+(?:-[a-z0-9]+)*\.md$")
ADR_ID = re.compile(r"^ADR-\d{4}$")
INV_ID = re.compile(r"^INV-(\d{4})-([1-9]\d*)$")
INV_REF = re.compile(r"\bINV-\d{4}-\d+\b")
SPIKE_ID = re.compile(r"^SPIKE-\d{2}$")
STATUSES = frozenset({"proposed", "accepted", "superseded", "rejected"})
ACTIVE_STATUSES = frozenset({"proposed", "accepted"})
NON_ADR_DOCS = frozenset({"README.md", "template.md"})
GENERATED_RULES_DIR = ".claude/rules/adr"
ENFORCEMENT_FILE = "docs/adr/enforcement.yaml"
SKIP_DIRS = frozenset(
    {
        ".git",
        ".venv",
        "venv",
        "node_modules",
        ".lake",
        "__pycache__",
        ".ruff_cache",
        ".pytest_cache",
        ".mypy_cache",
        ".import_linter_cache",
        ".tox",
        "build",
        "dist",
    }
)
TRIVIAL_NAMES = frozenset({".gitkeep", "py.typed"})
# Claude Code puts --worktree checkouts here; they are other branches, not this checkout.
SKIP_PATHS = frozenset({".claude/worktrees"})


class AdrError(ValueError):
    """An ADR file that cannot be parsed or fails schema validation."""


@dataclass(frozen=True)
class Invariant:
    id: str
    text: str


@dataclass(frozen=True)
class Enforcement:
    """One entry of docs/adr/enforcement.yaml."""

    invariant_id: str
    refs: tuple[str, ...]
    scope: tuple[str, ...]


@dataclass(frozen=True)
class Adr:
    path: Path
    rel_path: str
    id: str
    number: str
    title: str
    status: str
    date: str
    summary: str
    applies_to: tuple[str, ...]
    depends_on: tuple[str, ...]
    open_questions: tuple[str, ...]
    settled_by: tuple[str, ...]
    superseded_by: str | None
    invariants: tuple[Invariant, ...]
    revisit_when: str

    @property
    def slug(self) -> str:
        return self.path.stem


def split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """Split a Markdown file into its YAML frontmatter mapping and its body."""
    if not text.startswith("---\n"):
        raise AdrError("file does not start with YAML frontmatter ('---')")
    end = text.find("\n---\n", 4)
    if end == -1:
        raise AdrError("frontmatter is not closed with '---'")
    try:
        data = yaml.safe_load(text[4:end])
    except yaml.YAMLError as exc:
        raise AdrError(f"invalid YAML frontmatter: {exc}") from exc
    if not isinstance(data, dict):
        raise AdrError("frontmatter is not a mapping")
    return {str(key): value for key, value in data.items()}, text[end + 5 :]


def _text(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if isinstance(value, dt.date):
        return value.isoformat()
    if not isinstance(value, str) or not value.strip():
        raise AdrError(f"field '{key}' must be a non-empty string")
    return " ".join(value.split())


def _texts(data: dict[str, Any], key: str) -> tuple[str, ...]:
    value = data.get(key)
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AdrError(f"field '{key}' must be a list")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise AdrError(f"field '{key}' must contain only non-empty strings")
        items.append(item.strip())
    return tuple(items)


def _invariants(data: dict[str, Any], number: str) -> tuple[Invariant, ...]:
    value = data.get("invariants")
    if value is None:
        return ()
    if not isinstance(value, list):
        raise AdrError("field 'invariants' must be a list")
    result: list[Invariant] = []
    for position, item in enumerate(value, start=1):
        if not isinstance(item, dict):
            raise AdrError(f"invariant #{position} must be a mapping")
        entry = {str(key): val for key, val in item.items()}
        if "enforced_by" in entry:
            raise AdrError(
                f"invariant #{position} carries enforced_by; ADRs carry no enforcement, "
                f"record it in {ENFORCEMENT_FILE}"
            )
        unknown = sorted(set(entry) - {"id", "text"})
        if unknown:
            raise AdrError(f"invariant #{position} has unknown fields: {', '.join(unknown)}")
        invariant = Invariant(id=_text(entry, "id"), text=_text(entry, "text"))
        match = INV_ID.match(invariant.id)
        if match is None or match.group(1) != number:
            raise AdrError(f"invariant id '{invariant.id}' must look like INV-{number}-<n>")
        result.append(invariant)
    return tuple(result)


def parse_adr(path: Path, root: Path) -> Adr:
    """Parse and validate one ADR file."""
    name_match = ADR_FILE.match(path.name)
    if name_match is None:
        raise AdrError("file name must look like NNNN-lowercase-slug.md")
    number = name_match.group(1)
    data, _body = split_frontmatter(path.read_text(encoding="utf-8"))
    adr_id = _text(data, "id")
    if adr_id != f"ADR-{number}":
        raise AdrError(f"id '{adr_id}' does not match the file number {number}")
    status = _text(data, "status")
    if status not in STATUSES:
        raise AdrError(f"status '{status}' is not one of {', '.join(sorted(STATUSES))}")
    superseded_by = data.get("superseded_by")
    if superseded_by is not None and not (
        isinstance(superseded_by, str) and ADR_ID.match(superseded_by)
    ):
        raise AdrError("superseded_by must be an ADR id or null")
    if status == "superseded" and superseded_by is None:
        raise AdrError("a superseded ADR must set superseded_by")
    applies_to = _texts(data, "applies_to")
    if status in ACTIVE_STATUSES and not applies_to:
        raise AdrError("a proposed or accepted ADR needs at least one applies_to glob")
    return Adr(
        path=path,
        rel_path=path.relative_to(root).as_posix(),
        id=adr_id,
        number=number,
        title=_text(data, "title"),
        status=status,
        date=_text(data, "date"),
        summary=_text(data, "summary"),
        applies_to=applies_to,
        depends_on=_texts(data, "depends_on"),
        open_questions=_texts(data, "open_questions"),
        settled_by=_texts(data, "settled_by"),
        superseded_by=superseded_by,
        invariants=_invariants(data, number),
        revisit_when=_text(data, "revisit_when"),
    )


def load_adrs(root: Path) -> tuple[list[Adr], list[str]]:
    """Parse every ADR under docs/adr; return the ADRs and one error string per bad file."""
    adr_dir = root / "docs" / "adr"
    adrs: list[Adr] = []
    errors: list[str] = []
    if not adr_dir.is_dir():
        return adrs, ["docs/adr: directory is missing"]
    for path in sorted(adr_dir.glob("*.md")):
        if path.name in NON_ADR_DOCS:
            continue
        try:
            adrs.append(parse_adr(path, root))
        except AdrError as exc:
            errors.append(f"{path.relative_to(root).as_posix()}: {exc}")
    return adrs, errors


def load_enforcement(root: Path) -> tuple[dict[str, Enforcement], list[str]]:
    """Parse docs/adr/enforcement.yaml; return its entries by invariant ID, and errors."""
    path = root / ENFORCEMENT_FILE
    if not path.is_file():
        return {}, []
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except yaml.YAMLError as exc:
        return {}, [f"{ENFORCEMENT_FILE}: invalid YAML: {exc}"]
    if data is None:
        return {}, []
    if not isinstance(data, dict):
        return {}, [f"{ENFORCEMENT_FILE}: must map invariant IDs to entries"]
    entries: dict[str, Enforcement] = {}
    errors: list[str] = []
    for key, value in data.items():
        invariant_id = str(key)
        where = f"{ENFORCEMENT_FILE}: {invariant_id}"
        if INV_ID.match(invariant_id) is None:
            errors.append(f"{where}: key is not an invariant ID")
            continue
        if not isinstance(value, dict):
            errors.append(f"{where}: entry must be a mapping")
            continue
        entry = {str(k): v for k, v in value.items()}
        unknown = sorted(set(entry) - {"enforced_by", "scope"})
        if unknown:
            errors.append(f"{where}: unknown fields {', '.join(unknown)}")
            continue
        try:
            refs, scope = _texts(entry, "enforced_by"), _texts(entry, "scope")
        except AdrError as exc:
            errors.append(f"{where}: {exc}")
            continue
        entries[invariant_id] = Enforcement(invariant_id=invariant_id, refs=refs, scope=scope)
    return entries, errors


def expand_braces(pattern: str) -> list[str]:
    """Expand one level of {a,b} alternatives, recursively."""
    match = re.search(r"\{([^{}]*)\}", pattern)
    if match is None:
        return [pattern]
    head, tail = pattern[: match.start()], pattern[match.end() :]
    expanded: list[str] = []
    for alternative in match.group(1).split(","):
        expanded.extend(expand_braces(head + alternative + tail))
    return expanded


def glob_regex(pattern: str) -> re.Pattern[str]:
    """Translate a glob with ** support into a regular expression over POSIX paths."""
    parts: list[str] = []
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            parts.append("(?:.*/)?")
            i += 3
        elif pattern.startswith("**", i):
            parts.append(".*")
            i += 2
        elif pattern[i] == "*":
            parts.append("[^/]*")
            i += 1
        elif pattern[i] == "?":
            parts.append("[^/]")
            i += 1
        else:
            parts.append(re.escape(pattern[i]))
            i += 1
    return re.compile("^" + "".join(parts) + "$")


def matches(rel_path: str, patterns: Iterable[str]) -> bool:
    return any(
        glob_regex(expanded).match(rel_path)
        for pattern in patterns
        for expanded in expand_braces(pattern)
    )


def repo_files(root: Path) -> Iterator[str]:
    """Yield repository files as POSIX paths relative to root, skipping tool directories."""
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = Path(dirpath).relative_to(root).as_posix()
        prefix = "" if rel_dir == "." else f"{rel_dir}/"
        dirnames[:] = sorted(
            d for d in dirnames if d not in SKIP_DIRS and f"{prefix}{d}" not in SKIP_PATHS
        )
        for name in sorted(filenames):
            yield (Path(dirpath) / name).relative_to(root).as_posix()


def _is_docstring(node: ast.stmt) -> bool:
    return (
        isinstance(node, ast.Expr)
        and isinstance(node.value, ast.Constant)
        and isinstance(node.value.value, str)
    )


def is_trivial(root: Path, rel_path: str) -> bool:
    """True for files that don't count as governed code: docs, markers, docstring-only modules."""
    if rel_path.startswith(GENERATED_RULES_DIR + "/"):
        return True
    name = rel_path.rsplit("/", 1)[-1]
    if name in TRIVIAL_NAMES or name.endswith(".md"):
        return True
    if name.endswith(".py"):
        try:
            tree = ast.parse((root / rel_path).read_text(encoding="utf-8"))
        except (SyntaxError, UnicodeDecodeError):
            return False
        return not tree.body or (len(tree.body) == 1 and _is_docstring(tree.body[0]))
    return False
