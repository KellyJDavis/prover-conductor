"""Compare work/ext-old-*.json against work/ext-new-*.json (SPIKE-03 follow-up)."""

import json
from pathlib import Path

W = Path(__file__).parent / "work"


def load(label: str, mode: str) -> dict[str, dict[str, str]]:
    doc = json.loads((W / f"ext-{label}-{mode}.json").read_text())
    return {d["name"]: {e["name"]: e["hash"] for e in d["closure"]} for d in doc["declarations"]}


for mode in ("deep", "mathlib-only"):
    old, new = load("old", mode), load("new", mode)
    print(f"== {mode}")
    for n in sorted(old):
        o, m = old[n], new[n]
        keys = set(o) | set(m)
        # ignore the locked declaration itself and project-local helper (only s14 uses myEnergy)
        gone = sum(1 for k in keys if k not in o or k not in m)
        chg = sum(1 for k in keys if k in o and k in m and o[k] != m[k])
        print(
            f"{n}: old={len(o)} new={len(m)} added/removed={gone} changed={chg} "
            f"-> {'INVALIDATED' if gone or chg else 'stable'}"
        )
