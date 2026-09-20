"""Development conventions: INV-0007-1."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_lean_tests_excluded_by_default() -> None:
    """INV-0007-1: `lean` and `network` markers exist and the default run excludes both."""
    options = PYPROJECT["tool"]["pytest"]["ini_options"]
    markers = " ".join(options["markers"])
    assert "lean:" in markers
    assert "network:" in markers
    assert "not lean" in options["addopts"]
    assert "not network" in options["addopts"]
