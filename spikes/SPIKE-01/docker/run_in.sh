#!/usr/bin/env bash
# usage: run_in.sh <none|bridge> <project dir under work/> <toolchain tag> <bash command>
set -uo pipefail
net="$1"; proj="$2"; tag="$3"; cmd="$4"
exec docker run --rm --network "$net" \
  -e GIT_CONFIG_COUNT=1 -e GIT_CONFIG_KEY_0=safe.directory -e GIT_CONFIG_VALUE_0='*' \
  -v "$PWD/$proj":/work/project -w /work/project "spike01-lean:$tag" bash -c "$cmd"
