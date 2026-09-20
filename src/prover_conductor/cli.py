"""The `conductor` command (ADR-0006). Only diagnostics exist so far."""

from __future__ import annotations

import argparse
import os
import platform
import shutil
import sys
from collections.abc import Sequence

from prover_conductor import __version__

# External tools the finished system uses, with the decision that brings each in.
TOOLS: tuple[tuple[str, str], ...] = (
    ("git", "internal git store and worktrees (ADR-0001)"),
    ("uv", "Python environment and tooling (ADR-0007)"),
    ("elan", "Lean toolchain manager (ADR-0003)"),
    ("lake", "Lean build tool (ADR-0003)"),
    ("ray", "compute substrate (ADR-0005)"),
    ("runsc", "gVisor, cluster sandboxes on Linux (ADR-0005)"),
    ("srt", "OS-level sandbox for local mode (ADR-0008, proposed)"),
)


def doctor() -> int:
    """Report which external tools are on PATH. Informational: never fails."""
    print(f"prover-conductor {__version__}, Python {platform.python_version()} on {sys.platform}")
    for tool, purpose in TOOLS:
        location = shutil.which(tool) or "not found"
        print(f"  {tool:<6} {location:<40} {purpose}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="conductor", description="Conduct agents that prove results in Lean."
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    commands = parser.add_subparsers(dest="command")
    commands.add_parser("doctor", help="report which external tools are available")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "doctor":
            code = doctor()
        else:
            parser.print_help()
            code = 0
        sys.stdout.flush()
    except BrokenPipeError:
        # The reader exited early (for example `conductor doctor | head -1`). Point stdout at
        # devnull so the interpreter's final flush doesn't raise again.
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        return 1
    return code


if __name__ == "__main__":
    raise SystemExit(main())
