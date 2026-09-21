"""Build the statement-hash tool and run it on fixture modules (SPIKE-03)."""

import json
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any

HERE = Path(__file__).parent
HASH_DIR = HERE / "hash"
WORK = HERE / "work" / "cases"


@dataclass(frozen=True)
class Setup:
    """A toolchain, the tool built with it, and extra LEAN_PATH entries (e.g. Mathlib)."""

    hash_dir: Path = HASH_DIR
    extra_lean_path: tuple[str, ...] = ()

    @property
    def tool(self) -> Path:
        return self.hash_dir / ".lake" / "build" / "bin" / "stmthash"


DEFAULT = Setup()


def _run(cmd: list[str], cwd: Path, env: dict[str, str] | None = None) -> str:
    proc = subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True, timeout=900, check=False
    )
    if proc.returncode != 0:
        raise RuntimeError(f"{cmd} failed ({proc.returncode}):\n{proc.stdout}\n{proc.stderr}")
    return proc.stdout


def build_tool(setup: Setup = DEFAULT) -> None:
    _run(["lake", "build", "stmthash"], setup.hash_dir)


def setup_for_toolchain(toolchain: str, extra_lean_path: tuple[str, ...] = ()) -> Setup:
    """Copy the package sources to work/ pinned to `toolchain` and build them there."""
    hash_dir = HERE / "work" / f"hash-{toolchain.replace('/', '-').replace(':', '-')}"
    if hash_dir.exists():
        shutil.rmtree(hash_dir)
    hash_dir.mkdir(parents=True)
    for name in ("StatementHash", "Main.lean", "lakefile.toml"):
        src = HASH_DIR / name
        if src.is_dir():
            shutil.copytree(src, hash_dir / name)
        else:
            shutil.copy(src, hash_dir / name)
    (hash_dir / "lean-toolchain").write_text(toolchain + "\n")
    setup = Setup(hash_dir, extra_lean_path)
    build_tool(setup)
    return setup


def sysroot(setup: Setup = DEFAULT) -> Path:
    # cwd = the package dir so elan resolves the toolchain from its lean-toolchain file
    return Path(_run(["lean", "--print-prefix"], setup.hash_dir).strip())


def _lean_path(setup: Setup, out: Path) -> str:
    return os.pathsep.join([*setup.extra_lean_path, str(out)])


def compile_variant(name: str, files: str | dict[str, str], setup: Setup = DEFAULT) -> Path:
    """Compile the modules of one variant into WORK/name; returns the directory."""
    if isinstance(files, str):
        files = {"Fix": files}
    out = WORK / name
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    env = {**os.environ, "LEAN_PATH": _lean_path(setup, out)}
    lean = str(sysroot(setup) / "bin" / "lean")
    for mod, text in files.items():
        (out / f"{mod}.lean").write_text(text, encoding="utf-8")
        _run([lean, "-o", f"{mod}.olean", f"{mod}.lean"], out, env)
    return out


def run_tool(
    out: Path,
    decls: tuple[str, ...],
    args: tuple[str, ...] = (),
    module: str = "Fix",
    serialize: bool = False,
    setup: Setup = DEFAULT,
) -> dict[str, dict[str, Any]]:
    env = {
        **os.environ,
        "LEAN_PATH": _lean_path(setup, out),
        "LEAN_SYSROOT": str(sysroot(setup)),
    }
    cmd = [str(setup.tool), "--module", module, *args]
    if serialize:
        cmd.append("--serialize")
    stdout = _run([*cmd, *decls], out, env)
    doc = json.loads(stdout)
    return {d["name"]: d for d in doc["declarations"]}
