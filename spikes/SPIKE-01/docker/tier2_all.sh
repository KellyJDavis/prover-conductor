#!/usr/bin/env bash
# Run tier2.sh over the tier 2 corpus, one project at a time (Docker disk and CPU are shared).
cd "$(dirname "$0")/.."
for p in bergschaf__lean-banach-tarski sinhp__groupoid_model_in_lean4 kkytola__ExtremeValueProject \
         RemyDegenne__CLT AlexKontorovich__PrimeNumberTheoremAnd fpvandoorn__carleson \
         YaelDillies__LeanAPAP; do
  docker/tier2.sh "$p" multi
done
echo "TIER2-ALL-DONE" >> work/tier2.results
