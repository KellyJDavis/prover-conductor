"""The ADR numbering helper sees drafts on every branch (ADR-0000)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import next_adr_number


def git(root: Path, *args: str) -> None:
    subprocess.run(
        ["git", "-c", "user.email=t@example.com", "-c", "user.name=t", *args],
        cwd=root,
        check=True,
        capture_output=True,
    )


def commit_adr(root: Path, name: str) -> None:
    path = root / "docs" / "adr" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("---\n---\n", encoding="utf-8")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", name)


def test_counts_drafts_on_other_branches_and_reports_collisions(tmp_path: Path) -> None:
    git(tmp_path, "init", "-q", "-b", "main")
    commit_adr(tmp_path, "0000-first.md")
    git(tmp_path, "switch", "-q", "-c", "spike-a")
    commit_adr(tmp_path, "0001-from-a.md")
    git(tmp_path, "switch", "-q", "main")
    git(tmp_path, "switch", "-q", "-c", "spike-b")
    commit_adr(tmp_path, "0001-from-b.md")
    git(tmp_path, "switch", "-q", "main")

    usage = next_adr_number.collect_usage(tmp_path)
    assert next_adr_number.next_free(usage) == 2
    assert set(next_adr_number.collisions(usage)[1]) == {"0001-from-a.md", "0001-from-b.md"}
    assert 0 not in next_adr_number.collisions(usage)
