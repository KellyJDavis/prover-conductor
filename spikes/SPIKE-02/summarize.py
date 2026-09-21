"""Summarize work/results.jsonl: median and min-max per backend/workload."""

import json
import statistics as st
import sys
from collections import defaultdict
from pathlib import Path

ORDER = ["startup", "import", "heavy", "build"]
HEADER = [
    "workload",
    "backend",
    "n",
    "rc!=0",
    "wall s median",
    "wall s min-max",
    "cgroup peak MB median",
    "max RSS MB median",
]

rows: defaultdict[tuple[str, str], list[dict[str, object]]] = defaultdict(list)
path = Path(sys.argv[1] if len(sys.argv) > 1 else "work/results.jsonl")
for line in path.read_text().splitlines():
    r = json.loads(line)
    rows[(r["workload"], r["backend"])].append(r)

print("| " + " | ".join(HEADER) + " |")
print("|" + "---|" * len(HEADER))
for (w, b), rs in sorted(rows.items(), key=lambda k: (ORDER.index(k[0][0]), k[0][1])):
    ws = [float(r["wall_s"]) for r in rs]  # type: ignore[arg-type]
    pk = [float(r["cgroup_peak_mb"]) for r in rs]  # type: ignore[arg-type]
    rss = [int(r["maxrss_kb"]) / 1024 for r in rs if r["maxrss_kb"]]  # type: ignore[arg-type]
    failed = sum(r["rc"] != 0 for r in rs)
    cells = [
        w,
        b,
        str(len(rs)),
        str(failed),
        f"{st.median(ws):.3f}",
        f"{min(ws):.3f}-{max(ws):.3f}",
        f"{st.median(pk):.0f}",
        f"{st.median(rss) if rss else 0:.0f}",
    ]
    print("| " + " | ".join(cells) + " |")
