---
id: SPIKE-01
title: Lake-free fetch and the source of Mathlib artifacts
informs: [ADR-0008, ADR-0009]
status: open
---

## Question

Can every dependency of a supported project be fetched from `lake-manifest.json` alone, with
plain git at pinned revisions, so that Lake never runs with network access? Where should Mathlib
build artifacts come from: Mathlib's upstream cache, or platform builds per Mathlib commit, and
at what cost?

## Why it matters

Resolving a Lake workspace elaborates `lakefile.lean`, and packages can declare `post_update`
hooks; Mathlib's uses one to sync the toolchain and fetch its cache. Running Lake in a networked
stage hands user code a connection (ADR-0008).

## Method

1. Corpus: physicslib4, plus the public projects listed in leanblueprint's README that use a
   supported toolchain (ADR-0003).
2. For each project, fetch with a manifest-only fetcher (git at each package's `rev`, no Lake).
   Then, with networking disabled, place Mathlib artifacts and run `lake build`.
3. Classify every failure: manifest out of sync with the lakefile, missing package, dependence on
   a `post_update` hook, other.
4. For two Mathlib commits, measure fetching upstream artifacts against building Mathlib from
   source on a platform builder.
5. Write a unit test showing that the fetcher refuses loopback, private, link-local and cloud
   metadata addresses.

## Exit criteria

- A table of projects and outcomes with every failure classified.
- A recommendation for the Mathlib artifact source, with measured costs.
- The address-refusal test passes.

## Time box

Set when starting; suggested five working days.

## Results

Not started.

## Implications for ADRs

Not started.
