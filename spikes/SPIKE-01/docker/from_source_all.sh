#!/usr/bin/env bash
cd "$(dirname "$0")/.."
docker/from_source.sh physicslib4-src https://github.com/physicslib/physicslib4 v4.32.0
docker/from_source.sh bt-src https://github.com/bergschaf/lean-banach-tarski multi
echo FROMSOURCE-ALL-DONE >> work/fromsource.results
