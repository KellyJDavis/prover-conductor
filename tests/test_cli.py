"""Smoke tests for the `conductor` command."""

from __future__ import annotations

import pytest

from prover_conductor import cli


def test_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit) as exit_info:
        cli.main(["--version"])
    assert exit_info.value.code == 0
    assert capsys.readouterr().out.startswith("conductor ")


def test_doctor_lists_tools(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["doctor"]) == 0
    output = capsys.readouterr().out
    assert "elan" in output
    assert "lake" in output
