"""SPIKE-02: Ray Sandboxes (ray.experimental.sandbox, Ray 2.58, alpha) on Lean workloads.
Runs inside a privileged container (image spike02-ray) with work/rootfs.tar mounted at /data.
Uses the local SandboxRuntime (same backend the Sandbox actor wraps). Prints JSON lines."""

import json
import os
import sys
import time
from pathlib import Path

from ray.experimental.sandbox.runtime import SandboxRuntime

os.environ["RAY_SANDBOX_IGNORE_CGROUPS"] = "1"
IMG = "/data/rootfs.tar"
ENV = {
    "PATH": "/opt/elan/bin:/usr/local/bin:/usr/bin:/bin",
    "ELAN_HOME": "/opt/elan",
    "HOME": "/root",
    "GIT_CONFIG_COUNT": "1",
    "GIT_CONFIG_KEY_0": "safe.directory",
    "GIT_CONFIG_VALUE_0": "*",
}
MIN = ".lake/build/lib/lean/Physicslib4/Spacetime/Minkowski"
WL = {
    "startup": "true",
    "import": "lake env lean /work/fixtures/import_mathlib.lean",
    "heavy": "lake env lean .lake/packages/mathlib/Mathlib/Analysis/Calculus/ContDiff/Basic.lean",
    "build": (
        f"rm -f {MIN}.* .lake/build/ir/Physicslib4/Spacetime/Minkowski.*; "
        "lake build Physicslib4.Spacetime.Minkowski"
    ),
}
reps = int(sys.argv[1]) if len(sys.argv) > 1 else 3


def emit(**kw):
    print(json.dumps(kw), flush=True)


rt = SandboxRuntime()
t = time.perf_counter()
rt.pull_image(IMG, timeout_seconds=1800)
emit(step="pull_image(extract tar)", wall_s=round(time.perf_counter() - t, 2))
for rep in range(reps):
    t = time.perf_counter()
    sid = rt.create(
        IMG,
        workdir="/work/project",
        env=ENV,
        network="none",
        readonly=False,
        rootless=False,
        timeout_seconds=600,
    )
    emit(step="create", rep=rep, wall_s=round(time.perf_counter() - t, 3))
    try:
        rt.exec(sid, "mkdir -p /work/fixtures", timeout=30)
        rt.write_file(
            sid,
            "/work/fixtures/import_mathlib.lean",
            Path("/tmp/fx/import_mathlib.lean").read_text(),
        )
        for wl, cmd in WL.items():
            t = time.perf_counter()
            r = rt.exec(sid, cmd, timeout=900)
            emit(
                step="exec",
                workload=wl,
                rep=rep,
                wall_s=round(time.perf_counter() - t, 3),
                exit=getattr(r, "exit_code", None),
                in_sandbox_s=round(getattr(r, "duration_seconds", 0), 3),
            )
            if getattr(r, "exit_code", 0) != 0:
                emit(err=str(getattr(r, "stderr", ""))[-300:])
        if rep == 0:
            probe = Path("/probe.sh").read_text()
            rt.write_file(sid, "/tmp/probe.sh", probe)
            r = rt.exec(sid, "bash /tmp/probe.sh", timeout=120)
            emit(step="probe", out=str(getattr(r, "stdout", r)))
    finally:
        t = time.perf_counter()
        rt.delete(sid)
        emit(step="delete", wall_s=round(time.perf_counter() - t, 3))
