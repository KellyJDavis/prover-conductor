"""Probe candidate corpus repositories: toolchain, lakefile flavour, manifest presence.

Candidates are derived from the project list in leanblueprint's README (github.io URLs map to
owner/repo). Read-only: uses the GitHub contents API through `gh`. Prints one JSON object per line.
"""

import base64
import json
import subprocess
import sys

CANDIDATES = [
    "leanprover-community/sphere-eversion",
    "leanprover-community/liquid",
    "b-mehta/unit-fractions",
    "leanprover-community/flt-regular",
    "YaelDillies/LeanAPAP",
    "teorth/pfr",
    "remydegenne/testing-lower-bounds",
    "leanprover-community/con-nf",
    "AlexKontorovich/PrimeNumberTheoremAnd",
    "pitmonticone/FLT3",
    "ImperialCollegeLondon/FLT",
    "fpvandoorn/carleson",
    "emilyriehl/infinity-cosmos",
    "teorth/expdb",
    "teorth/equational_theories",
    "sinhp/groupoid_model_in_lean4",
    "thefundamentaltheor3m/Sphere-Packing-Lean",
    "bergschaf/Localic-Caratheodory-Extensions",
    "bergschaf/lean-banach-tarski",
    "Command-Master/lean-bourgain",
    "FredRaj3/SemicircleLaw",
    "ivan-sergeyev/seymour",
    "leastauthority/STIR",
    "RemyDegenne/CLT",
    "RemyDegenne/brownian-motion",
    "Verified-zkEVM/ArkLib",
    "YaelDillies/ChandraFurstLipton",
    "YaelDillies/LeanCamCombi",
    "YaelDillies/Toric",
    "acmepjz/lean-iwasawa",
    "ahhwuhu/zeta_3_irrational",
    "b-mehta/ABC-Exceptions",
    "fpvandoorn/BonnAnalysis",
    "kkytola/ExtremeValueProject",
    "mo271/FormalBook",
    "oliver-butterley/SpectralThm",
    "ilpreterosso/LEANearized-RadiiPolynomial",
    "physicslib/physicslib4",
]


def gh(path: str) -> str | None:
    r = subprocess.run(["gh", "api", path, "--jq", ".content"], capture_output=True, text=True)
    if r.returncode != 0:
        return None
    return base64.b64decode(r.stdout.strip()).decode()


def probe(repo: str) -> dict[str, object]:
    meta = subprocess.run(
        ["gh", "api", f"repos/{repo}", "--jq", "[.default_branch,.pushed_at,.archived]|@tsv"],
        capture_output=True,
        text=True,
    )
    if meta.returncode != 0:
        return {"repo": repo, "error": "repo not found or not readable"}
    branch, pushed, archived = meta.stdout.strip().split("\t")
    tc = gh(f"repos/{repo}/contents/lean-toolchain")
    has_lean = gh(f"repos/{repo}/contents/lakefile.lean") is not None
    has_toml = gh(f"repos/{repo}/contents/lakefile.toml") is not None
    return {
        "repo": repo,
        "branch": branch,
        "pushed": pushed[:10],
        "archived": archived == "true",
        "toolchain": tc.strip() if tc else None,
        "lakefile.lean": has_lean,
        "lakefile.toml": has_toml,
        "manifest": gh(f"repos/{repo}/contents/lake-manifest.json") is not None,
    }


if __name__ == "__main__":
    for repo in CANDIDATES:
        print(json.dumps(probe(repo)), flush=True)
    sys.exit(0)
