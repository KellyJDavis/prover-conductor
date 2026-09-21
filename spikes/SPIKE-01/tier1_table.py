"""Render work/tier1.jsonl (last record per project wins) as a markdown table."""

import json
from pathlib import Path

rows: dict[str, dict] = {}
for line in (Path(__file__).parent / "work/tier1.jsonl").read_text().splitlines():
    r = json.loads(line)
    rows[r["repo"]] = r

NOTES = {
    "sinhp/groupoid_model_in_lean4": (
        'other: conditional require of doc-gen4 (`meta if get_config? env = some "dev"`); '
        "manifest correctly omits it, so the naive lakefile/manifest compare is a false positive"
    ),
    "FredRaj3/SemicircleLaw": (
        "other: in-repo `path` package HammerCore inside fetched package Hammer; "
        "no network needed once Hammer is checked out"
    ),
    "ilpreterosso/LEANearized-RadiiPolynomial": (
        "other: absolute local `path` dependency (/Users/... on the author's machine); "
        "unfetchable, must fail onboarding"
    ),
}

print("| Project | Toolchain | Pkgs | Fetched with plain git | Classification |")
print("|---|---|---|---|---|")
for repo, r in sorted(rows.items()):
    fails = r.get("fetch_failures", [])
    ok = "yes" if r["outcome"] == "fetched" and not fails else "no"
    note = NOTES.get(repo, "none")
    if r.get("dep_lakefile_violations"):
        note += "; dep lakefile violation " + ",".join(r["dep_lakefile_violations"])
    print(f"| {repo} | {r['toolchain'].split(':')[1]} | {r.get('packages', '?')} | {ok} | {note} |")
