"""SPIKE-02: network-less gVisor sandboxes reach nothing (INV-0005-2).

Runs docker/probe.sh in a privileged Docker container three ways and checks the outcome:
  control  : no sandbox, default Docker network  -> internet and gateway must be REACHED
             (otherwise the probes prove nothing)
  gvisor   : runsc --network=none                -> every probe must be BLOCKED
  gvisor-h : runsc --network=host (control for runsc itself, informational only)

Needs Docker and image spike02-gvisor; marked network because the control talks to the internet.
Run: uv run --with pytest pytest spikes/SPIKE-02/test_network.py -s
"""

import subprocess
from pathlib import Path

import pytest

pytestmark = pytest.mark.network
HERE = Path(__file__).parent
RUNSC = "runsc --platform=systrap --ignore-cgroups --host-uds=none --overlay2=none"


SERVICE = (
    "mkdir -p /srv/www && echo hi > /srv/www/index.html && "
    "(cd /srv/www && python3 -m http.server 8080 --bind 0.0.0.0 >/dev/null 2>&1 &) && "
    "sleep 1 && "
    "export SVC_IP=$(hostname -i | awk '{print $1}') && "
)


def run(inner: str) -> dict[str, str]:
    cmd = [
        "docker",
        "run",
        "--rm",
        "--privileged",
        "-v",
        f"{HERE}/docker/probe.sh:/probe.sh:ro",
        "spike02-gvisor",
        "bash",
        "-c",
        SERVICE + inner,
    ]
    out = subprocess.run(cmd, capture_output=True, text=True, timeout=300, check=True).stdout
    print(out)
    return {p[1]: p[2] for p in (ln.split() for ln in out.splitlines()) if p[0] == "PROBE"}


def test_control_reaches_network() -> None:
    res = run("/probe.sh")
    assert res["internet-ip-tcp"] == "REACHED"
    assert res["internet-dns-name"] == "REACHED"
    assert res["internal-service-eth0-ip"] == "REACHED"  # positive control for the internal probe


def test_gvisor_network_none_reaches_nothing() -> None:
    res = run(f"{RUNSC} --network=none do /probe.sh")
    reached = [k for k, v in res.items() if v != "BLOCKED"]
    assert len(res) >= 9
    assert not reached, f"reached from a network=none sandbox: {reached}"
