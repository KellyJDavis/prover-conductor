"""SPIKE-01: cloud-release fetching keeps the address rules (INV-0008-7) and unpacks safely.

No network: redirects are exercised through the handler directly, archives are built in memory.
"""

import io
import ipaddress
import socket
import sys
import tarfile
import urllib.request
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent))
from fetcher import CheckedRedirect, RefusedAddress, extract_archive, find_release

RELEASE_URL = "https://github.com/o/r/releases/download/v1/a.tar.gz"


def public(host, port, **_kw):
    """Resolve names to a public address, as a resolver would; IP literals resolve to themselves."""
    try:
        addr = str(ipaddress.ip_address(host))
    except ValueError:
        addr = "140.82.112.3"
    family = socket.AF_INET6 if ":" in addr else socket.AF_INET
    return [(family, socket.SOCK_STREAM, 6, "", (addr, port))]


@pytest.mark.parametrize(
    "target",
    [
        "https://127.0.0.1/x",
        "https://169.254.169.254/latest/meta-data/",
        "https://metadata.google.internal/x",
        "http://release-assets.githubusercontent.com/x",
        "https://user:pw@release-assets.githubusercontent.com/x",
    ],
)
def test_redirect_to_bad_target_is_refused(target: str) -> None:
    handler = CheckedRedirect(public)
    req = urllib.request.Request(RELEASE_URL)
    with pytest.raises(RefusedAddress):
        handler.redirect_request(req, None, 302, "Found", {}, target)


def test_redirect_to_public_target_is_allowed() -> None:
    handler = CheckedRedirect(public)
    req = urllib.request.Request(RELEASE_URL)
    new = handler.redirect_request(req, None, 302, "Found", {}, "https://assets.example.org/x")
    assert new is not None


def make_tar(members: dict[str, bytes]) -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tar.addfile(info, io.BytesIO(data))
    return buf.getvalue()


def test_extract_ok(tmp_path: Path) -> None:
    assert extract_archive(make_tar({"lib/a.olean": b"x"}), tmp_path) == 1
    assert (tmp_path / "lib/a.olean").read_bytes() == b"x"


@pytest.mark.parametrize("name", ["../evil", "a/../../evil"])
def test_extract_refuses_path_escape(tmp_path: Path, name: str) -> None:
    dest = tmp_path / "dest"
    with pytest.raises((tarfile.TarError, ValueError)):
        extract_archive(make_tar({name: b"x"}), dest)
    assert not (tmp_path / "evil").exists()


def test_extract_neutralizes_absolute_path(tmp_path: Path) -> None:
    """The `data` filter strips a leading slash, so the member lands inside dest."""
    dest = tmp_path / "dest"
    extract_archive(make_tar({"/tmp-spike01-abs/evil": b"x"}), dest)
    assert (dest / "tmp-spike01-abs/evil").exists()
    assert not Path("/tmp-spike01-abs").exists()


def test_extract_refuses_symlink_escape(tmp_path: Path) -> None:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        info = tarfile.TarInfo("link")
        info.type = tarfile.SYMTYPE
        info.linkname = "/etc"
        tar.addfile(info)
    with pytest.raises((tarfile.TarError, ValueError)):
        extract_archive(buf.getvalue(), tmp_path / "dest")


PROOFWIDGETS = (
    "package proofwidgets where\n"
    "  preferReleaseBuild := true\n"
    '  buildArchive? := "ProofWidgets4.tar.gz"\n'
    '  releaseRepo := "https://github.com/leanprover-community/ProofWidgets4"\n'
)


@pytest.mark.parametrize(
    ("lakefile", "expected"),
    [
        (
            PROOFWIDGETS,
            ("https://github.com/leanprover-community/ProofWidgets4", "ProofWidgets4.tar.gz"),
        ),
        ("package duper where\n  preferReleaseBuild := false\n", None),
        ("package auto where\n  preferReleaseBuild := true\n", None),
    ],
)
def test_find_release(tmp_path: Path, lakefile: str, expected: tuple[str, str] | None) -> None:
    (tmp_path / "lakefile.lean").write_text(lakefile)
    assert find_release(tmp_path) == expected
