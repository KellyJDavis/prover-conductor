"""Shallow comparison: current design (external types only) across the two Mathlib revisions."""

import json
from pathlib import Path

W = Path(__file__).parent / "work"


def load(label: str) -> dict[str, tuple[str, dict[str, str]]]:
    docs = json.loads((W / f"ext-{label}-shallow.json").read_text())["declarations"]
    return {
        d["name"]: (d["hash"], {e["name"]: e["typeHash"] for e in d["externalReferences"]})
        for d in docs
    }


old, new = load("old"), load("new")
for k in sorted(old):
    (ho, eo), (hn, en) = old[k], new[k]
    changed = [e for e in eo if e in en and eo[e] != en[e]]
    missing = [e for e in eo if e not in en]
    print(
        k,
        "hash same" if ho == hn else "hash DIFF",
        f"ext={len(eo)} type-changed={len(changed)} missing={len(missing)}",
        (changed + missing)[:3],
    )
