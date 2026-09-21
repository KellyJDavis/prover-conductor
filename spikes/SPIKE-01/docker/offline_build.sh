#!/usr/bin/env bash
# Offline stage: lake build with NO network. Proves the network is off before building.
# usage: offline_build.sh <project dir under work/> <toolchain tag> [lake args...]
set -uo pipefail
proj="$1"; tag="$2"; shift 2
start=$(date +%s)
docker run --rm --network none --name "offline-$(basename "$proj")" \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -v "$PWD/$proj":/work/project -w /work/project "spike01-lean:$tag" \
  bash -c '
    if curl -sS -m 5 -o /dev/null https://github.com 2>/dev/null; then echo "NETWORK-UP: ABORT"; exit 99; fi
    echo "network check: github.com unreachable (expected)"
    lake --version; lean --version
    lake build '"$*"' 2>&1 | tail -40; echo "lake build exit: ${PIPESTATUS[0]}"
    git -C /work/project status --short | head -5
  '
echo "offline wall seconds: $(( $(date +%s) - start ))"
