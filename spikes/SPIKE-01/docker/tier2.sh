#!/usr/bin/env bash
# Tier 2 pipeline for one already-fetched project (see tier1.py): Lake never has network.
#   1. offline: build Mathlib's `cache` exe          (--network none)
#   2. network: run the `cache` binary alone         (lake replaced by a canary, paths set by hand)
#   3. offline: lake build, capped at $LIMIT seconds (--network none)
# usage: tier2.sh <dir under work/> <image tag>; appends one RESULT line to work/tier2.results
set -uo pipefail
proj="$1"; tag="$2"; LIMIT="${LIMIT:-2700}"
here="$(cd "$(dirname "$0")" && pwd)"; cd "$here/.."
log="work/tier2-$proj.log"; : > "$log"; rm -f "work/$proj/LAKE_CALLED"
t0=$(date +%s)
"$here/run_in.sh" none "work/$proj" "$tag" 'lake build cache 2>&1 | tail -3' >>"$log" 2>&1; rc1=$?
t1=$(date +%s)
"$here/run_in.sh" bridge "work/$proj" "$tag" '
tcbin=$(dirname "$(elan which lean)")
for f in /opt/elan/bin/lake "$tcbin/lake"; do
  printf "#!/bin/sh\necho \"lake called: \$*\" >> /work/project/LAKE_CALLED\ncase \"\$*\" in *:release*) exit 0;; esac\nexit 1\n" > "$f"; chmod +x "$f"
done
src=""; lib=""
for d in /work/project/.lake/packages/*/; do src="$src:${d%/}"; lib="$lib:${d%/}/.lake/build/lib/lean"; done
export LEAN_SRC_PATH="/work/project${src}" LEAN_PATH="/work/project/.lake/build/lib/lean${lib}"
.lake/packages/mathlib/.lake/build/bin/cache get 2>&1 | tr "\r" "\n" | grep -v "^Downloaded:" | tail -8 | cut -c1-240
exit ${PIPESTATUS[0]}' >>"$log" 2>&1; rc2=$?
t2=$(date +%s)
canary=no
if [ -f "work/$proj/LAKE_CALLED" ]; then
  if grep -qv ":release" "work/$proj/LAKE_CALLED"; then canary=OTHER; else canary=release-only-shimmed; fi
fi
"$here/run_in.sh" none "work/$proj" "$tag" \
  "curl -sS -m 5 -o /dev/null https://github.com 2>/dev/null && { echo NETWORK-UP; exit 99; }
   timeout $LIMIT lake build 2>&1 | tail -25; exit \${PIPESTATUS[0]}" >>"$log" 2>&1; rc3=$?
t3=$(date +%s)
echo "RESULT $proj cache_exe_build_rc=$rc1 ($((t1-t0))s) cache_get_rc=$rc2 ($((t2-t1))s) lake_called=$canary offline_build_rc=$rc3 ($((t3-t2))s) lake_size=$(du -sh "work/$proj/.lake" | cut -f1)" | tee -a work/tier2.results
