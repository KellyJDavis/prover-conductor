"""Manifest-only dependency fetcher: plain git at pinned revisions, no Lake.

Reads a project's lake-manifest.json and materializes every package under a packages directory by
`git fetch --depth 1 <url> <rev>`. Refuses non-https URLs and hosts that resolve to loopback,
private, link-local, multicast, reserved or unspecified addresses, or to cloud metadata endpoints
(INV-0008-7).

Cloud releases: a package that sets `preferReleaseBuild := true` with an explicit `releaseRepo` and
`buildArchive` gets that archive from `<releaseRepo>/releases/download/<tag>/<archive>`, where the
tag is one that points at the pinned revision. Every redirect hop is checked like the first URL.

Known limit: the check resolves the host itself, then git resolves it again (DNS rebinding window).
A production fetcher would pin the resolved address for the fetch.
"""

import io
import ipaddress
import json
import re
import socket
import subprocess
import sys
import tarfile
import urllib.request
from collections.abc import Callable
from pathlib import Path
from urllib.parse import urlsplit

METADATA_HOSTS = {"metadata.google.internal", "metadata", "instance-data"}
METADATA_ADDRS = {
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("169.254.170.2"),
    ipaddress.ip_address("fd00:ec2::254"),
    ipaddress.ip_address("100.100.100.200"),
}

Resolver = Callable[..., list[tuple]]  # shape of socket.getaddrinfo


class RefusedAddress(ValueError):
    pass


def _addr_problem(addr: ipaddress.IPv4Address | ipaddress.IPv6Address) -> str | None:
    if isinstance(addr, ipaddress.IPv6Address) and addr.ipv4_mapped is not None:
        addr = addr.ipv4_mapped
    if addr in METADATA_ADDRS:
        return "cloud metadata address"
    if addr.is_loopback:
        return "loopback"
    if addr.is_link_local:
        return "link-local"
    if addr.is_private:
        return "private"
    if addr.is_multicast or addr.is_reserved or addr.is_unspecified:
        return "reserved"
    if not addr.is_global:
        return "non-global"
    return None


def check_url(url: str, resolver: Resolver = socket.getaddrinfo) -> None:
    """Raise RefusedAddress unless `url` is https and every address of its host is global."""
    parts = urlsplit(url)
    if parts.scheme != "https":
        raise RefusedAddress(f"scheme {parts.scheme!r} not allowed: {url}")
    if parts.username is not None or parts.password is not None:
        raise RefusedAddress(f"credentials in URL not allowed: {url}")
    host = parts.hostname
    if not host:
        raise RefusedAddress(f"no host: {url}")
    if host.lower().rstrip(".") in METADATA_HOSTS:
        raise RefusedAddress(f"cloud metadata host {host}")
    try:
        infos = resolver(host, parts.port or 443, proto=socket.IPPROTO_TCP)
    except socket.gaierror as e:
        raise RefusedAddress(f"cannot resolve {host}: {e}") from e
    if not infos:
        raise RefusedAddress(f"{host} resolves to nothing")
    for info in infos:
        addr = ipaddress.ip_address(info[4][0].split("%")[0])
        problem = _addr_problem(addr)
        if problem:
            raise RefusedAddress(f"{host} -> {addr}: {problem}")


def _git(*args: str, cwd: Path) -> None:
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True)


def check_path_package(pkg: dict, project: Path) -> None:
    """A `path` package is acceptable only when it lies inside the project tree and exists."""
    root = project.resolve()
    target = (root / pkg["dir"]).resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"path dependency escapes the project: {pkg['dir']}")
    if not target.is_dir():
        raise ValueError(f"path dependency missing after fetch: {pkg['dir']}")


def fetch_package(pkg: dict, dest: Path, resolver: Resolver = socket.getaddrinfo) -> None:
    url, rev = pkg["url"], pkg["rev"]
    check_url(url, resolver)
    if (dest / ".git").exists():
        return
    dest.mkdir(parents=True, exist_ok=True)
    _git("init", "-q", cwd=dest)
    _git("remote", "add", "origin", url, cwd=dest)
    _git("fetch", "-q", "--depth", "1", "origin", rev, cwd=dest)
    _git("checkout", "-q", "--detach", "FETCH_HEAD", cwd=dest)


RELEASE_REPO = re.compile(r'releaseRepo\??\s*(?::=|=)\s*"([^"]+)"')
BUILD_ARCHIVE = re.compile(r'buildArchive\??\s*(?::=|=)\s*"([^"]+)"')
PREFER_RELEASE = re.compile(r"preferReleaseBuild\s*(?::=|=)\s*true")
MAX_ARCHIVE_BYTES = 2 * 1024**3


class CheckedRedirect(urllib.request.HTTPRedirectHandler):
    """Refuse a redirect whose target fails check_url (an allowed host can bounce to a bad one)."""

    def __init__(self, resolver: Resolver = socket.getaddrinfo) -> None:
        self.resolver = resolver

    def redirect_request(self, req, fp, code, msg, headers, newurl):  # type: ignore[no-untyped-def]
        check_url(newurl, self.resolver)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def find_release(pkg_dir: Path) -> tuple[str, str] | None:
    """Return (releaseRepo, buildArchive) when the lakefile explicitly asks for a cloud release."""
    for name in ("lakefile.lean", "lakefile.toml"):
        f = pkg_dir / name
        if not f.exists():
            continue
        text = f.read_text(errors="replace")
        repo, archive = RELEASE_REPO.search(text), BUILD_ARCHIVE.search(text)
        if PREFER_RELEASE.search(text) and repo and archive:
            return repo.group(1), archive.group(1)
    return None


def tags_at_head(pkg_dir: Path) -> list[str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=pkg_dir, check=True, capture_output=True, text=True
    ).stdout.strip()
    out = subprocess.run(
        ["git", "ls-remote", "--tags", "origin"],
        cwd=pkg_dir,
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    tags: list[str] = []
    for line in out.splitlines():
        sha, ref = line.split("\t")
        if sha == head:
            tags.append(ref.removeprefix("refs/tags/").removesuffix("^{}"))
    return sorted(set(tags))


def extract_archive(data: bytes, dest: Path) -> int:
    """Unpack a tar.gz into dest; the `data` filter rejects absolute paths, `..` and links out."""
    dest.mkdir(parents=True, exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
        tar.extractall(dest, filter="data")
        return len(tar.getnames())


def fetch_release(
    pkg_dir: Path,
    resolver: Resolver = socket.getaddrinfo,
    opener=None,
) -> dict | None:
    rel = find_release(pkg_dir)
    if rel is None:
        return None
    repo, archive = rel
    opener = opener or urllib.request.build_opener(CheckedRedirect(resolver))
    last_error = "no tag points at the pinned revision"
    for tag in tags_at_head(pkg_dir):
        url = f"{repo.rstrip('/')}/releases/download/{tag}/{archive}"
        try:
            check_url(url, resolver)
            with opener.open(url, timeout=120) as resp:
                data = resp.read(MAX_ARCHIVE_BYTES + 1)
            if len(data) > MAX_ARCHIVE_BYTES:
                raise ValueError("archive too large")
            n = extract_archive(data, pkg_dir / ".lake" / "build")
            return {"url": url, "bytes": len(data), "entries": n}
        except (OSError, ValueError, tarfile.TarError) as e:
            last_error = f"{url}: {e}"
    raise ValueError(last_error)


def fetch_manifest(project: Path, resolver: Resolver = socket.getaddrinfo) -> list[dict]:
    """Fetch every package of project/lake-manifest.json into project/.lake/packages.

    Git packages first, then `path` packages, which may live inside a fetched package.
    """
    manifest = json.loads((project / "lake-manifest.json").read_text())
    pkgs_dir = project / manifest.get("packagesDir", ".lake/packages")
    ordered = sorted(manifest["packages"], key=lambda p: p.get("type", "git") == "path")
    results = []
    for pkg in ordered:
        name = pkg["name"].strip("\xab\xbb")  # Lake writes names like <<doc-gen4>>
        kind = pkg.get("type", "git")
        try:
            if kind == "git":
                fetch_package(pkg, pkgs_dir / name, resolver)
                rel = fetch_release(pkgs_dir / name, resolver)
                if rel:
                    results.append({"name": name, "ok": True, "type": "release", **rel})
            elif kind == "path":
                check_path_package(pkg, project)
            else:
                raise ValueError(f"unsupported package type {kind!r}")
            results.append({"name": name, "ok": True, "type": kind})
        except (RefusedAddress, ValueError, subprocess.CalledProcessError) as e:
            detail = e.stderr.strip() if isinstance(e, subprocess.CalledProcessError) else str(e)
            results.append({"name": name, "ok": False, "type": kind, "error": detail})
    return results


if __name__ == "__main__":
    print(json.dumps(fetch_manifest(Path(sys.argv[1])), indent=1))
