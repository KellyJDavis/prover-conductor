"""Does loading an environment run a module's `initialize` block? (SPIKE-03 follow-up)

Positive control: with initializers enabled and extensions loaded the block runs. The statement-hash
tool's configuration (initializers not enabled, loadExts := false) must not run it.
"""

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from harness import DEFAULT, HERE, sysroot

pytestmark = pytest.mark.lean

CASES = [
    (("enable", "exts"), True),  # positive control
    (("enable", "noexts"), False),
    (("no", "exts"), None),  # importModules refuses; the block must not run either
    (("no", "noexts"), False),  # the statement-hash tool's configuration
]


@pytest.mark.parametrize(("args", "expect_run"), CASES)
def test_initializer_runs_only_when_enabled(
    args: tuple[str, str], expect_run: bool | None, tmp_path: Path
) -> None:
    for name in ("Evil.lean", "probe.lean"):
        shutil.copy(HERE / "init_probe" / name, tmp_path / name)
    root = sysroot(DEFAULT)
    lean = str(root / "bin" / "lean")
    env = {**os.environ, "LEAN_PATH": str(tmp_path), "LEAN_SYSROOT": str(root)}
    for name in ("Evil", "probe"):
        subprocess.run(
            [lean, "-o", f"{name}.olean", f"{name}.lean"], cwd=tmp_path, env=env, check=True
        )
    assert not (tmp_path / "marker-init.txt").exists(), "initializer ran at compile time"
    proc = subprocess.run(
        [lean, "--run", "probe.lean", *args],
        cwd=tmp_path,
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    ran = (tmp_path / "marker-init.txt").exists()
    if expect_run is None:
        assert not ran and "must be run before" in proc.stdout
    else:
        assert ran is expect_run, proc.stdout
