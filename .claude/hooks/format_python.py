#!/usr/bin/env python3
"""PostToolUse hook: format Python files that Claude Code edits (ADR-0007). Never blocks."""

from __future__ import annotations

import contextlib
import json
import os
import subprocess
import sys
from pathlib import Path


def find_checkout(start: Path, marker: str) -> Path | None:
    """Nearest directory at or above start that holds this repository's hook `marker`.

    Works for the main checkout and for every git worktree of it. Claude Code keeps
    CLAUDE_PROJECT_DIR at the checkout where the session started even after Claude moves into a
    worktree, so hooks locate the checkout from the file or directory they act on instead.
    """
    for directory in (start, *start.parents):
        if (directory / ".claude" / "hooks" / marker).is_file():
            return directory
    return None


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0
    if not isinstance(payload, dict):
        return 0
    tool_input = payload.get("tool_input")
    raw = tool_input.get("file_path") if isinstance(tool_input, dict) else None
    if not isinstance(raw, str) or not raw.endswith(".py"):
        return 0
    base = Path(payload.get("cwd") or os.environ.get("CLAUDE_PROJECT_DIR") or ".")
    target = (Path(raw) if Path(raw).is_absolute() else base / raw).resolve()
    root = find_checkout(target.parent, "format_python.py")
    if root is None or not target.is_file():
        return 0
    rel = target.relative_to(root).as_posix()
    with contextlib.suppress(OSError, subprocess.SubprocessError):
        subprocess.run(
            ["uv", "run", "--quiet", "ruff", "format", rel],
            cwd=root,
            capture_output=True,
            check=False,
            timeout=120,
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
