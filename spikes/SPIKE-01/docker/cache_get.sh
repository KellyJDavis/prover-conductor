#!/usr/bin/env bash
# Networked artifact-placement step: run Mathlib's own `cache` exe against the fetched project.
# usage: cache_get.sh <project dir under work/> <toolchain tag>
set -euo pipefail
proj="$1"; tag="$2"
start=$(date +%s)
docker run --rm --name "cacheget-$(basename "$proj")" \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -e MATHLIB_NO_CACHE_ON_UPDATE=1 \
  -v "$PWD/$proj":/work/project -w /work/project "spike01-lean:$tag" \
  bash -c 'lake exe cache get 2>&1 | tail -25'
echo "cache_get wall seconds: $(( $(date +%s) - start ))"
du -sh "$proj/.lake" | tail -1
