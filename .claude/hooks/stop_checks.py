#!/usr/bin/env python3
"""Stop hook (INV-0000-1, INV-0000-2): run the ADR checks once per turn.

Failing checks exit 2, which keeps Claude working with the output as feedback. Changes to accepted
ADRs in the working tree (for example made through shell commands, which bypass the PreToolUse
hook) are reported to the user without blocking, because the owner may have made them.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

CHECKS = (
    ["uv", "run", "--quiet", "python", "scripts/gen_adr_rules.py", "--check"],
    ["uv", "run", "--quiet", "python", "scripts/check_invariants.py", "--quiet"],
)
ACCEPTED = re.compile(r"^status:\s*accepted\s*$", re.MULTILINE)
ADR_FILE = re.compile(r"^docs/adr/\d{4}-[^/]+\.md$")


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


def run(command: list[str], root: Path) -> tuple[int, str]:
    """Run a command; a missing tool counts as success so the hook never blocks on setup."""
    try:
        done = subprocess.run(
            command, cwd=root, capture_output=True, text=True, check=False, timeout=300
        )
    except (OSError, subprocess.SubprocessError) as exc:
        return 0, f"(skipped: {exc})"
    return done.returncode, (done.stdout + done.stderr).strip()


def changed_accepted_adrs(root: Path) -> list[str]:
    code, out = run(["git", "diff", "--name-only", "HEAD", "--", "docs/adr"], root)
    if code != 0:
        return []
    changed: list[str] = []
    for rel in out.splitlines():
        if not ADR_FILE.match(rel):
            continue
        code, at_head = run(["git", "show", f"HEAD:{rel}"], root)
        if code == 0 and ACCEPTED.search(at_head.split("\n---\n", 1)[0]):
            changed.append(rel)
    return changed


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        payload = {}
    if isinstance(payload, dict) and payload.get("stop_hook_active"):
        return 0
    cwd = payload.get("cwd") if isinstance(payload, dict) else None
    start = Path(cwd or os.environ.get("CLAUDE_PROJECT_DIR") or ".").resolve()
    root = find_checkout(start, "stop_checks.py")
    if root is None:
        return 0
    failures: list[str] = []
    for command in CHECKS:
        code, output = run(command, root)
        if code != 0:
            failures.append(f"$ {' '.join(command[3:])}\n{output}")
    if failures:
        print(
            "ADR checks failed. Fix them before finishing (after editing an ADR, run "
            "`uv run python scripts/gen_adr_rules.py`):\n\n" + "\n\n".join(failures),
            file=sys.stderr,
        )
        return 2
    changed = changed_accepted_adrs(root)
    if changed:
        message = (
            "Accepted ADRs changed in the working tree: "
            + ", ".join(changed)
            + ". Accepted ADRs change only by supersession; review before committing."
        )
        print(json.dumps({"systemMessage": message}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
