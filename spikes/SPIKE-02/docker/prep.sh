#!/usr/bin/env bash
# Prep (networked, not measured): place Mathlib artifacts and build physicslib4 so that the
# workloads can run with the network off. usage: prep.sh   (run from spikes/SPIKE-02)
set -euo pipefail
docker run --rm --name spike02-prep \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -e MATHLIB_NO_CACHE_ON_UPDATE=1 \
  -v "$PWD/work/physicslib4":/work/project -w /work/project spike02-gvisor \
  bash -c 'time lake exe cache get 2>&1 | tail -5; time lake build 2>&1 | tail -5; du -sh .lake'
