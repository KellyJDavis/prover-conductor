"""SPIKE-03 follow-up: what would hashing external definition values cost and invalidate?

Usage: python ext_values.py <label> <mathlib-root> [<packages-root>]
Runs the tool on ext_sample.lean with every library root treated as local ("deep") and with core
treated as external ("mathlib-only"), writes work/ext-<label>-<mode>.json and prints timings.
"""

import json
import os
import subprocess
import sys
import time
from pathlib import Path

from harness import HERE, Setup, compile_variant, setup_for_toolchain, sysroot

NAMES = tuple(f"s{i:02d}" for i in range(1, 17))
CORE = ["Init", "Std", "Lean"]
LIBS = [
    "Mathlib",
    "Batteries",
    "Aesop",
    "Qq",
    "Plausible",
    "ProofWidgets",
    "ImportGraph",
    "LeanSearchClient",
    "Cli",
]


def main(label: str, root: str, pkgs: str | None) -> None:
    rootp = Path(root)
    pk = Path(pkgs) if pkgs else rootp / ".lake" / "packages"
    entries = [rootp / ".lake" / "build" / "lib" / "lean"]
    entries += sorted(pk.glob("*/.lake/build/lib/lean"))
    entries = list(dict.fromkeys(entries))
    toolchain = (rootp / "lean-toolchain").read_text().strip()
    setup: Setup = setup_for_toolchain(toolchain, tuple(str(e) for e in entries))
    src = (HERE / "ext_sample.lean").read_text(encoding="utf-8")
    out = compile_variant(f"ext-{label}", {"Fix": src}, setup)
    env = {
        **os.environ,
        "LEAN_PATH": os.pathsep.join([*map(str, entries), str(out)]),
        "LEAN_SYSROOT": str(sysroot(setup)),
    }
    for mode, roots in (
        ("deep", ["Fix", *LIBS, *CORE]),
        ("mathlib-only", ["Fix", *LIBS]),
        ("shallow", ["Fix"]),
    ):
        cmd = [str(setup.tool), "--module", "Fix"]
        for r in roots:
            cmd += ["--local-root", r]
        t = time.time()
        proc = subprocess.run([*cmd, *NAMES], cwd=out, env=env, capture_output=True, text=True)
        dt = time.time() - t
        if proc.returncode != 0:
            print(mode, "FAILED", proc.stderr[-500:])
            continue
        doc = json.loads(proc.stdout)
        (HERE / "work" / f"ext-{label}-{mode}.json").write_text(proc.stdout)
        sizes = [len(d["closure"]) for d in doc["declarations"] if d["exists"]]
        print(
            f"{label} {mode}: {dt:.1f}s lean={doc['lean']} closure sizes min/median/max="
            f"{min(sizes)}/{sorted(sizes)[len(sizes) // 2]}/{max(sizes)}"
        )


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else None)
