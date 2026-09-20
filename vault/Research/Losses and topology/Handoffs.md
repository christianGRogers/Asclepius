---
tags: [research/loss, handoff]
status: living
updated: 2026-09-19
---

# Handoffs

Findings that fell outside "losses, topology and post-processing" and belong to
another topic owner. One line each, no follow-up done here.

- **Metrics / evaluation owner:** `src/segtrain/metrics.py` currently computes Dice,
  NSD and HD95 only. It has no connected-component count (β₀) and no per-component
  class-purity check. Both are needed to catch the two distinct failure modes in
  [[Largest-component post-processing is wrong for coronaries]] (fragment deletion)
  and [[Enforcing per-branch connectivity so fragments are not assigned to the wrong branch]]
  (fragment mislabelling) — a per-voxel-pooled confusion matrix will not surface
  either.
- **Class schema owner:** the TopCoW cbDice result (0 Dice on small communicating
  arteries under plain Dice+CE, rescued to ~40 by any centerline term) is a warning
  about what happens to whatever branch classes end up smallest/rarest in the final
  schema — worth a line in the class-schema note about expecting near-zero baseline
  Dice on the rarest chosen classes.
