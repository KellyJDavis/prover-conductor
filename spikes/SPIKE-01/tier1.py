"""Tier 1: manifest-only fetch and classification for every in-window corpus project.

Per project: shallow-clone the default branch, compare the lakefile's direct requires with the
manifest's non-inherited packages, fetch every manifest package with fetcher.py (plain git at
pinned revisions), then classify each dependency's lakefile flavour and post_update use.
Writes one JSON object per project to work/tier1.jsonl.

Usage: uv run --no-project python tier1.py [repo ...]   (default: all in-window probe results)
"""

import json
import re
import subprocess
import sys
import tomllib
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from fetcher import fetch_manifest

HERE = Path(__file__).parent
WORK = HERE / "work"
GUILLEMETS = chr(0xAB) + chr(0xBB)  # Lake writes names like <<doc-gen4>>
REQUIRE = rf"^require\s+(?:[\w.{GUILLEMETS}]+/)?[\"{GUILLEMETS[0]}]?([\w-]+)"
TOOLCHAIN = re.compile(r"leanprover/lean4:v(\d+)\.(\d+)\.(\d+)(-rc\d+)?")


def in_window(toolchain: str | None) -> bool:
    m = TOOLCHAIN.fullmatch(toolchain or "")
    return bool(m) and (int(m[1]), int(m[2]), int(m[3])) >= (4, 24, 0)


def direct_requires(project: Path) -> tuple[set[str], str]:
    toml_file, lean_file = project / "lakefile.toml", project / "lakefile.lean"
    if toml_file.exists():
        req = tomllib.loads(toml_file.read_text()).get("require", [])
        return {r["name"].strip(GUILLEMETS) for r in req}, "toml"
    text = lean_file.read_text()
    names = set(re.findall(REQUIRE, text, re.M))
    return names, "lean"


def classify_dep(pkg_dir: Path) -> dict:
    lean, toml = (pkg_dir / "lakefile.lean").exists(), (pkg_dir / "lakefile.toml").exists()
    hooks = [
        f.name
        for f in (pkg_dir / "lakefile.lean", pkg_dir / "lakefile.toml")
        if f.exists() and "post_update" in f.read_text(errors="replace")
    ]
    return {"lean": lean, "toml": toml, "post_update": hooks}


def run(repo: str) -> dict:
    out: dict = {"repo": repo}
    proj = WORK / repo.replace("/", "__")
    try:
        if not proj.exists():
            subprocess.run(
                ["git", "clone", "-q", "--depth", "1", f"https://github.com/{repo}", str(proj)],
                check=True,
                capture_output=True,
                text=True,
            )
        out["commit"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=proj, capture_output=True, text=True
        ).stdout.strip()
        tc = (proj / "lean-toolchain").read_text().strip()
        out["toolchain"] = tc
        if not in_window(tc):
            out["outcome"] = "excluded: toolchain outside window at HEAD"
            return out
        manifest = json.loads((proj / "lake-manifest.json").read_text())
        pkgs = manifest["packages"]
        out["packages"] = len(pkgs)
        out["mathlib_rev"] = next((p["rev"] for p in pkgs if p["name"] == "mathlib"), None)
        direct = {p["name"].strip(GUILLEMETS) for p in pkgs if not p.get("inherited")}
        wanted, flavour = direct_requires(proj)
        out["lakefile"] = flavour
        out["missing_from_manifest"] = sorted(wanted - direct)
        out["manifest_not_in_lakefile"] = sorted(direct - wanted)
        res = fetch_manifest(proj)
        out["fetch_failures"] = [r for r in res if not r["ok"]]
        deps = {}
        for r in res:
            pkg_dir = proj / ".lake/packages" / r["name"]
            if r["ok"] and r["type"] == "git":
                deps[r["name"]] = classify_dep(pkg_dir)
        out["deps"] = deps
        out["dep_lakefile_violations"] = sorted(
            n for n, d in deps.items() if d["lean"] == d["toml"]
        )
        out["post_update_deps"] = sorted(n for n, d in deps.items() if d["post_update"])
        out["non_git_or_odd_urls"] = sorted(
            p["name"]
            for p in pkgs
            if p.get("type", "git") != "git" or not p["url"].startswith("https://")
        )
        out["outcome"] = "fetched"
    except Exception as e:
        out["outcome"] = "error"
        out["error"] = f"{type(e).__name__}: {getattr(e, 'stderr', '') or e}".strip()[:500]
    return out


if __name__ == "__main__":
    WORK.mkdir(exist_ok=True)
    repos = sys.argv[1:] or [
        r["repo"]
        for r in map(json.loads, (HERE / "probe.jsonl").read_text().splitlines())
        if "error" not in r
        and in_window(r["toolchain"])
        and r["manifest"]
        and (r["lakefile.lean"] != r["lakefile.toml"])
    ]
    with ThreadPoolExecutor(4) as ex, open(WORK / "tier1.jsonl", "a") as f:
        for res in ex.map(run, repos):
            f.write(json.dumps(res) + "\n")
            f.flush()
            print(res["repo"], res["outcome"], flush=True)
