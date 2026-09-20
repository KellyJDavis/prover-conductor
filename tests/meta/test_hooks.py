"""Claude Code hooks: INV-0000-3 (accepted ADRs, ADR statuses and generated rules are protected)."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HOOK = ROOT / ".claude" / "hooks" / "protect_adrs.py"


def run_hook(project: Path, tool_input: Mapping[str, object]) -> subprocess.CompletedProcess[str]:
    payload = {
        "hook_event_name": "PreToolUse",
        "tool_name": "Edit",
        "cwd": str(project),
        "tool_input": dict(tool_input),
    }
    env = {**os.environ, "CLAUDE_PROJECT_DIR": str(project)}
    return subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        capture_output=True,
        text=True,
        env=env,
        check=False,
    )


def make_checkout(directory: Path) -> Path:
    """A directory the hook recognizes as a checkout of this repository."""
    marker = directory / ".claude" / "hooks" / "protect_adrs.py"
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text("", encoding="utf-8")
    return directory


def write_adr(project: Path, status: str) -> Path:
    make_checkout(project)
    path = project / "docs" / "adr" / "0001-example.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"---\nid: ADR-0001\nstatus: {status}\n---\n\nBody\n", encoding="utf-8")
    return path


def test_hook_is_registered_for_file_tools() -> None:
    """INV-0000-3: settings.json runs protect_adrs.py before Edit and Write."""
    settings = json.loads((ROOT / ".claude" / "settings.json").read_text(encoding="utf-8"))
    groups = settings["hooks"]["PreToolUse"]
    registered = [
        group["matcher"]
        for group in groups
        if any("protect_adrs.py" in hook["command"] for hook in group["hooks"])
    ]
    assert registered
    assert all("Edit" in matcher and "Write" in matcher for matcher in registered)


def test_blocks_edits_to_accepted_adrs(tmp_path: Path) -> None:
    path = write_adr(tmp_path, "accepted")
    result = run_hook(tmp_path, {"file_path": str(path), "old_string": "Body", "new_string": "X"})
    assert result.returncode == 2
    assert "supersession" in result.stderr


def test_allows_edits_to_proposed_adrs(tmp_path: Path) -> None:
    path = write_adr(tmp_path, "proposed")
    result = run_hook(tmp_path, {"file_path": str(path), "old_string": "Body", "new_string": "X"})
    assert result.returncode == 0


def test_blocks_status_changes(tmp_path: Path) -> None:
    path = write_adr(tmp_path, "proposed")
    edit = {
        "file_path": str(path),
        "old_string": "status: proposed",
        "new_string": "status: accepted",
    }
    assert run_hook(tmp_path, edit).returncode == 2


def test_blocks_new_adrs_written_as_accepted(tmp_path: Path) -> None:
    make_checkout(tmp_path)
    path = tmp_path / "docs" / "adr" / "0002-new.md"
    content = "---\nid: ADR-0002\nstatus: accepted\n---\n"
    assert run_hook(tmp_path, {"file_path": str(path), "content": content}).returncode == 2


def test_blocks_generated_rules(tmp_path: Path) -> None:
    make_checkout(tmp_path)
    rule = tmp_path / ".claude" / "rules" / "adr" / "0001-example.md"
    assert run_hook(tmp_path, {"file_path": str(rule), "content": "x"}).returncode == 2


def test_ignores_files_outside_any_checkout(tmp_path: Path) -> None:
    project = make_checkout(tmp_path / "project")
    outside = tmp_path / "elsewhere" / "docs" / "adr" / "0001-example.md"
    assert run_hook(project, {"file_path": str(outside), "content": "x"}).returncode == 0


def test_protects_accepted_adrs_inside_a_worktree(tmp_path: Path) -> None:
    """INV-0000-3 holds after Claude moves into a worktree: CLAUDE_PROJECT_DIR still names the
    main checkout, so the hook must locate the checkout from the edited file."""
    main = make_checkout(tmp_path / "main")
    worktree = main / ".claude" / "worktrees" / "spike-01"
    path = write_adr(worktree, "accepted")
    edit = {"file_path": str(path), "old_string": "Body", "new_string": "X"}
    assert run_hook(main, edit).returncode == 2
