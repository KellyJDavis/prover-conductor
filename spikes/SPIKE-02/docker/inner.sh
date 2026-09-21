#!/usr/bin/env bash
# Runs inside the privileged container. usage: inner.sh <backend> <workload>
# backend: bare | gvisor ; workload: startup | import | heavy | build
set -uo pipefail
backend="$1"; wl="$2"
cd /work/project
export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=safe.directory GIT_CONFIG_VALUE_0='*'
MOD=Physicslib4.Spacetime.Minkowski
case "$wl" in
  startup) cmd='true' ;;
  import)  cmd='lake env lean /work/fixtures/import_mathlib.lean' ;;
  heavy)   cmd='lake env lean .lake/packages/mathlib/Mathlib/Analysis/Calculus/ContDiff/Basic.lean' ;;
  build)   cmd="lake build $MOD"
           b=.lake/build/lib/lean/Physicslib4/Spacetime/Minkowski
           rm -f $b.olean $b.ilean $b.trace $b.hash $b.olean.hash $b.ilean.hash
           rm -f .lake/build/ir/Physicslib4/Spacetime/Minkowski.* ;;
esac
case "$backend" in
  bare)   wrap=() ;;
  gvisor) wrap=(runsc --platform="${PLATFORM:-systrap}" --network=none --ignore-cgroups --host-uds=none --overlay2=none do) ;;
esac
t0=$(date +%s.%N)
"${wrap[@]}" /usr/bin/time -f 'maxrss_kb=%M' -o /tmp/time.out bash -c "$cmd" > /tmp/out.log 2>&1
rc=$?
t1=$(date +%s.%N)
peak=$(cat /sys/fs/cgroup/memory.peak)
rss=$(sed -n 's/.*maxrss_kb=//p' /tmp/time.out | tail -1)
python3 - <<PY
import json
print(json.dumps(dict(backend="$backend", workload="$wl", rc=$rc, wall_s=round($t1-$t0,3),
  maxrss_kb="${rss:-}" or None, cgroup_peak_mb=round($peak/1048576,1))))
PY
[ $rc -ne 0 ] && tail -5 /tmp/out.log >&2
exit 0
