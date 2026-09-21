"""SPIKE-02 macOS: native vs @anthropic-ai/sandbox-runtime (srt). Appends to work/results-mac.jsonl.
usage: source ~/.nvm/nvm.sh; nvm use 20; python3 mac_bench.py <reps>   (from spikes/SPIKE-02)"""

import json
import re
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
PROJ = HERE / "work/physicslib4-mac"
SRT = [str(HERE / "work/srt/node_modules/.bin/srt"), "-s", str(HERE / "srt-settings.json"), "-c"]
MIN = ".lake/build/lib/lean/Physicslib4/Spacetime/Minkowski"
WL = {
    "startup": "true",
    "import": f"lake env lean {HERE}/fixtures/import_mathlib.lean",
    "heavy": "lake env lean .lake/packages/mathlib/Mathlib/Analysis/Calculus/ContDiff/Basic.lean",
    "build": "lake build Physicslib4.Spacetime.Minkowski",
}


def clean_build():
    for ext in ("olean", "ilean", "trace", "hash", "olean.hash", "ilean.hash"):
        (PROJ / f"{MIN}.{ext}").unlink(missing_ok=True)
    for p in (PROJ / ".lake/build/ir/Physicslib4/Spacetime").glob("Minkowski.*"):
        p.unlink()


def run(backend, wl):
    if wl == "build":
        clean_build()
    # `time -l` runs OUTSIDE the sandbox (it fails on sysctl inside); it reports the largest
    # resident set among all descendants, which for srt also includes srt's own node process.
    inner = WL[wl]
    argv = ["/usr/bin/time", "-l"] + (["bash", "-c", inner] if backend == "bare" else [*SRT, inner])
    t0 = time.perf_counter()
    p = subprocess.run(argv, cwd=PROJ, capture_output=True, text=True)
    wall = time.perf_counter() - t0
    m = re.search(r"(\d+)\s+maximum resident set size", p.stderr)
    return dict(
        backend=backend,
        workload=wl,
        rc=p.returncode,
        wall_s=round(wall, 3),
        maxrss_mb=round(int(m.group(1)) / 1048576, 1) if m else None,
    )


reps = int(sys.argv[1])
with open(HERE / "work/results-mac.jsonl", "a") as out:
    for backend in ("bare", "srt"):
        for wl in WL:
            for _ in range(reps):
                r = run(backend, wl)
                print(json.dumps(r), flush=True)
                out.write(json.dumps(r) + "\n")
