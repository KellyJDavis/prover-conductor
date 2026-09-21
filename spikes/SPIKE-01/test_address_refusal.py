"""SPIKE-01 exit criterion: the fetcher refuses loopback, private, link-local and cloud metadata
addresses (INV-0008-7). Uses stub resolvers; the literal-encoding cases use the real resolver but
need no network.
"""

import socket
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from fetcher import RefusedAddress, check_url


def resolver_for(*addrs: str):
    def resolve(host, port, **_kw):
        return [
            (socket.AF_INET6 if ":" in a else socket.AF_INET, socket.SOCK_STREAM, 6, "", (a, port))
            for a in addrs
        ]

    return resolve


@pytest.mark.parametrize(
    "addr",
    [
        "127.0.0.1",
        "127.5.5.5",
        "::1",
        "10.0.0.5",
        "172.16.3.4",
        "192.168.1.1",
        "169.254.10.10",
        "fe80::1",
        "fd12:3456::1",
        "169.254.169.254",
        "fd00:ec2::254",
        "100.100.100.200",
        "0.0.0.0",
        "::ffff:127.0.0.1",
        "::ffff:10.1.2.3",
        "100.64.0.1",
        "224.0.0.1",
    ],
)
def test_refuses_resolved_address(addr: str) -> None:
    with pytest.raises(RefusedAddress):
        check_url("https://example.org/repo.git", resolver_for(addr))


def test_refuses_when_any_address_is_bad() -> None:
    with pytest.raises(RefusedAddress):
        check_url("https://example.org/r.git", resolver_for("140.82.112.3", "10.0.0.1"))


@pytest.mark.parametrize(
    "url",
    [
        "https://localhost/r.git",
        "https://[::1]/r.git",
        "https://127.0.0.1/r.git",
        "https://169.254.169.254/latest/meta-data/",
        "https://metadata.google.internal/computeMetadata/v1/",
        "https://2130706433/r.git",
        "https://0x7f.0.0.1/r.git",
        "https://127.1/r.git",
        "https://017700000001/r.git",
    ],
)
def test_refuses_literal_hosts_with_real_resolver(url: str) -> None:
    with pytest.raises(RefusedAddress):
        check_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "http://github.com/o/r.git",
        "git://github.com/o/r.git",
        "ssh://git@github.com/o/r.git",
        "file:///etc/passwd",
        "https://user:pw@github.com/o/r.git",
        "https://github.com@127.0.0.1/r.git",
    ],
)
def test_refuses_scheme_and_credential_tricks(url: str) -> None:
    with pytest.raises(RefusedAddress):
        check_url(url, resolver_for("140.82.112.3"))


def test_unresolvable_host_is_refused() -> None:
    def fail(*_a, **_k):
        raise socket.gaierror("nope")

    with pytest.raises(RefusedAddress):
        check_url("https://no-such-host.invalid/r.git", fail)


def test_accepts_public_address() -> None:
    check_url("https://github.com/leanprover-community/mathlib4", resolver_for("140.82.112.3"))
    check_url("https://github.com/o/r", resolver_for("2606:50c0:8000::154"))
