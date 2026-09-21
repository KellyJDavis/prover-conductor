#!/usr/bin/env bash
# Clean from-source Mathlib build, nothing else running: fresh clone + manifest fetch, NO cache,
# `lake build Mathlib` with --network none. Appends one line to work/fromsource.results.
# usage: from_source.sh <name> <git url> <toolchain tag>
set -uo pipefail
name="$1"; url="$2"; tag="$3"
here="$(cd "$(dirname "$0")" && pwd)"; cd "$here/.."
[ "$(docker ps -q | wc -l | tr -d ' ')" = "0" ] || { echo "other containers running: abort"; exit 2; }
rm -rf "work/$name"; git clone -q --depth 1 "$url" "work/$name"
uv run --no-project python fetcher.py "work/$name" | grep -c '"ok": true'
rev=$(python3 -c "import json;print([p['rev'] for p in json.load(open('work/$name/lake-manifest.json'))['packages'] if p['name']=='mathlib'][0])")
t0=$(date +%s)
"$here/run_in.sh" none "work/$name" "$tag" 'lake build Mathlib 2>&1 | tail -4; exit ${PIPESTATUS[0]}' > "work/fromsource-$name.log" 2>&1; rc=$?
t1=$(date +%s)
echo "FROMSOURCE $name mathlib=$rev toolchain=$tag build_rc=$rc wall=$((t1-t0))s lake_size=$(du -sh work/$name/.lake | cut -f1)" | tee -a work/fromsource.results
