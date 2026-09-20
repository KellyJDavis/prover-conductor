"""Print the next ADR number that is free on every branch (ADR-0000).

Parallel sessions draft ADRs on different branches, so "the next number in docs/adr/" on one
branch can already be taken on another. This looks at the working tree and at every local and
remote branch, and also reports numbers that different branches use for different ADRs. Run
`git fetch` first so remote branches are current.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ADR_PATH = re.compile(r"^docs/adr/(\d{4})-[^/]+\.md$")

# number -> ADR file name -> places (working tree or branch names) that have it
Usage = dict[int, dict[str, set[str]]]


def _git(root: Path, *args: str) -> str:
    done = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, check=True)
    return done.stdout


def collect_usage(root: Path) -> Usage:
    usage: Usage = {}

    def add(rel_path: str, where: str) -> None:
        match = ADR_PATH.match(rel_path)
        if match:
            name = rel_path.rsplit("/", 1)[-1]
            usage.setdefault(int(match.group(1)), {}).setdefault(name, set()).add(where)

    for path in sorted((root / "docs" / "adr").glob("*.md")):
        add(path.relative_to(root).as_posix(), "working tree")
    refs = _git(root, "for-each-ref", "--format=%(refname)", "refs/heads", "refs/remotes")
    for ref in refs.split():
        if ref.endswith("/HEAD"):
            continue
        where = ref.removeprefix("refs/heads/").removeprefix("refs/remotes/")
        for rel_path in _git(root, "ls-tree", "-r", "--name-only", ref, "--", "docs/adr").split():
            add(rel_path, where)
    return usage


def next_free(usage: Usage) -> int:
    return max(usage, default=-1) + 1


def collisions(usage: Usage) -> dict[int, dict[str, set[str]]]:
    return {number: names for number, names in usage.items() if len(names) > 1}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Print the next ADR number free on all branches.")
    parser.add_argument("--root", type=Path, default=ROOT, help="repository root")
    args = parser.parse_args(argv)
    usage = collect_usage(Path(args.root).resolve())
    for number, names in sorted(collisions(usage).items()):
        print(f"collision: ADR-{number:04d} is used by {len(names)} different files:")
        for name, places in sorted(names.items()):
            print(f"  {name}: {', '.join(sorted(places))}")
    print(f"next free: ADR-{next_free(usage):04d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
