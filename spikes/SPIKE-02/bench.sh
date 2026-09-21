#!/usr/bin/env bash
# usage: bench.sh <reps> <backend...>   (from spikes/SPIKE-02). Appends JSON lines to work/results.jsonl
set -uo pipefail
reps=$1; shift
for backend in "$@"; do for wl in startup import heavy build; do for i in $(seq "$reps"); do
  docker run --rm --privileged --cpus=8 --memory=14g \
    -v spike02-proj:/work/project -v "$PWD/fixtures":/work/fixtures:ro -v "$PWD/docker/inner.sh":/inner.sh:ro \
    spike02-gvisor /inner.sh "$backend" "$wl" | tee -a work/results.jsonl
done; done; done
