"""Names and license: INV-0006-1, INV-0006-2, INV-0006-3."""

from __future__ import annotations

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))


def test_distribution_and_command_names() -> None:
    """INV-0006-1: distribution prover-conductor, console command conductor."""
    assert PYPROJECT["project"]["name"] == "prover-conductor"
    assert PYPROJECT["project"]["scripts"] == {"conductor": "prover_conductor.cli:main"}


def test_import_package_name() -> None:
    """INV-0006-2: the import package is prover_conductor; no top-level conductor module."""
    assert (ROOT / "src" / "prover_conductor" / "__init__.py").is_file()
    wheel = PYPROJECT["tool"]["hatch"]["build"]["targets"]["wheel"]
    assert wheel["packages"] == ["src/prover_conductor"]
    assert not (ROOT / "src" / "conductor").exists()
    assert not (ROOT / "src" / "conductor.py").exists()


def test_license_is_apache_2() -> None:
    """INV-0006-3: Apache-2.0 metadata and the full license text."""
    assert PYPROJECT["project"]["license"] == "Apache-2.0"
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "Apache License" in text
    assert "Version 2.0, January 2004" in text
    assert "END OF TERMS AND CONDITIONS" in text
