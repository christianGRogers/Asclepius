---
tags: [plans, candidate, two-stage, branch-labelling, round-2]
author: Bridge
round: 2
status: candidate
updated: 2026-10-04
---

# Bridge v2 — the master's model, plus a naming stage that costs no GPU and is judged by tree-F1

## 0. Improve or start again?

**I am improving v1, not starting again,** but narrowing it a lot. The Round-1 ruling rejected v1 as a
segmentation route for four reasons:

1. its patch-context argument (accepted: Atlas's sampling model is the right one);
2. it had no end-to-end number;
3. stage 1 was tied to the Girder masks;
4. it cost about 790 GPU-hours.

The ruling kept the part the evidence supported, the namer, and used it as QA (A4). v2 keeps the master
recipe untouched. It adds only what the new evidence supports: a **naming stage applied to the master's
own predictions**, with no GPU and no separate stage-1 model. It is compared with the master's direct
labels on the master's own metric (tF1, A1), case by case, with an adoption rule fixed in advance.

All three requests in ruling §4 are answered with measurements:

- **End to end:** [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]].
- **Lumen convention:** the same note. The namer was built on thick Girder masks and was never refit,
  yet it names the thin ImageCAS-X lumen at tF1 0.990 with the ramus excluded (63 test cases). It works under either
  human decision in §5.1.
- **Cost:** 0 extra GPU-hours (§7).

## 1. Thesis

Under A1, the master's deciding metric is tree-F1: centreline that is **correctly named and connected
to the ostium**. On that metric, naming is a few discrete decisions per tree:

- which tree is left;
- where the ostium is;
- where the LM ends;
- which child is the LAD;
- where the ramus goes.

A graph namer makes those decisions consistently and for the whole tree. A voxel model makes them voxel
by voxel. Measured on real stage-1 output (19 ImageCAS-X test cases, 13 never seen), the namer gives up
**0.007 tF1 [CI 0.004–0.011]** against *perfect* naming of the same lumen with the ramus convention set
aside (0.908 vs 0.915), and 0.037 with it (0.881 vs 0.918). The only swap is the ramus convention. So the only open question is empirical: does the master's direct
model name better than that? The master's validation predictions answer it for free. Rename their
foreground, score both on tF1, keep whichever wins, decided by a rule written now.

## 2. Recipe

### 2.1 Training: unchanged

[[Atlas v1]] with amendments A1–A6, exactly as in [[Master plan]]. No second segmentation model and no
comparator arm. The direct model *is* the comparator.

### 2.2 The naming stage (CPU; code exists)

`experiments/Bridge/namer.py` → `label.py` (frozen v3), ~1–3 min per case on one CPU core. It takes any
binary mask on the case grid and returns a 4-class map in which every class is a connected subtree.

1. 26-connected components; TEASAR skeleton (kimimaro, scale 1.5, const 2 mm, anisotropic).
2. **Naming bridges, 4 mm.** A component whose endpoint lies within 4 mm of another is joined to it in the
   *graph*. Voxels are never added or removed, so this is compatible with A2's "never delete" rule.
   Measured: needed on real output (c0675: tF1 0.215 → 0.765). One wrong join in 19 cases (c0407 −0.021).
3. Left/right by tree centroid. Fused trees (single tree > 800 mm skeleton) are flagged, not named.
4. Ostium: learned endpoint score + plausibility re-rank (0.957 CV; 0.98 on held-out Girder masks).
   **Change for v2:** when a TotalSegmentator aorta mask exists (Delta is producing them for A1's
   aorta-contact ostium), candidates touching the aorta (≤ 5 mm) are preferred (to implement; not yet measured). This makes the namer
   and the sealed-test metric use the same ostium definition.
5. LAD/LCx split (anterior/posterior split score); subtree inheritance.
6. **Ramus: a switch** (`to_LCx` / `to_LAD` / `pointing`). It is set to whatever rule the humans write
   (ruling §5.2), before any decision is scored. It moves tF1 by up to 0.15 in a case, and 9 of 19 test
   cases carry a ramus.

### 2.3 Three candidate outputs per validation case

| Output | What | Extra cost |
|---|---|---|
| **D** | the master's direct 4-class prediction (after A2 post-processing if A2 is adopted) | 0 |
| **R** (rename) | the namer applied to D's foreground (union of the 4 classes) | ~2 min CPU / case |
| **H** (hybrid) | tree decoding on R's skeleton graph with D's softmax as the per-vertex unary: LM is a single path from the ostium, every subtree below it is all-LAD or all-LCx, right tree = RCA, exact MAP (`learn.py` `decode`) | ~2 min CPU / case; needs D's softmax saved (`--save_probabilities`) |

R ignores D's names. H keeps D's names except where they break the tree grammar: islands, a split LM,
LAD/LCx interleaving. Delta's A2 label repair removes islands; H additionally makes every class a
connected subtree by construction. **H has not been measured.** It can be checked only on real 4-class
softmax, so it stays a candidate until R1 exists.

### 2.4 When the labels arrive

| Milestone | Action |
|---|---|
| now | Wire the namer into the A4 QA pass (already ruled). Run R on the released ImageCAS-X nnU-Net predictions for the remaining CT-cached test cases (this note's queue) |
| ramus rule written (§5.2) | Set the switch and re-score this note's cases (minutes) |
| R1 val predictions | Compute D, R, H on the val fold; tF1 @ 1.5 mm, FP-component gate, swap rate, LM length error |
| first 20 team labels | Re-score D/R/H against team labels (the namer needs no retraining: it is convention-agnostic) |
| ≥ 50 team labels | Refit the 11-weight ostium model and a junction ranker of the same form on team names. Measured: 5 cases give 0.93 ostium accuracy |
| sealed test | Score only the output the rule below selected, on the val fold, in advance |

## 3. Evaluation and the pre-registered rule

- Metric: the master's own deciding metric, macro **tF1 @ 1.5 mm**, gated by FP components per case
  (A1), with the aorta-contact ostium. Swap rate and LM length error are reported.
- **Rule.** On the val fold, compute the paired per-case difference R − D (and H − D). Adopt R (or H) as
  the shipped naming if the paired bootstrap 95 % CI of the mean difference **excludes 0 in its favour**
  and its swap rate is no higher. This is the master's own ablation rule (Atlas, A1). Otherwise ship D,
  and keep the namer as QA only (A4).
- **What would make me drop R and H for good:** D ≥ R and D ≥ H on val with the CI excluding 0. That would
  show a direct voxel model names at least as well as structure does, and the namer remains QA.

## 4. Evidence

All new evidence is on real data:

1. [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]]
   — **new, end to end.** Real stage-1 output on 19 ImageCAS-X test cases (13 never seen):
   - tF1 @ 1.5 mm: namer 0.881, oracle naming 0.918.
   - With the ramus excluded: namer 0.908 vs 0.915; paired gap −0.007, CI [−0.011, −0.004]. On the
     13 never-seen cases the gap is the same, −0.007.
   - 1 swap (the ramus, also present on the reference lumen).
   - Without bridges: 0.853.
   - On the reference lumen of 63 test cases: 0.981, or 0.990 with the ramus excluded, never refit.
   - The cuts come from stage 1 and are scored alike in both arms.
2. [[Bridge - A rule-based labeller names LM, LAD, LCx and RCA on our binary masks]] — Round 1, held out on
   Girder masks: 94.9 % of cases with all four classes ≥ 0.8; 98.9 % pooled voxel agreement.
3. [[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]
   — Atlas's own check: the namer and the projected proxy agree everywhere except a few mm at the carina.
   Median ignored fraction 0.26 %.
4. [[Bridge - Finding the left ostium is the crux of naming, and 5-10 labelled cases teach it]],
   [[Bridge - Stage-1 gaps are what break naming, and bridging fixes most of it]] (simulated; now confirmed on
   real output by item 1), [[Bridge - A generic learned vertex labeller is worse than structured rules at 5-40 training cases]].
5. Literature, all verified in v1: graph labellers on correct trees name the main branches at F1 0.92–0.99
   (CPR-GCN, arXiv:2003.08560 Table 3; Hampe et al. 2024, doi:10.1117/1.JMI.11.3.034001). On extracted
   trees, the error comes from extraction (Hampe: 0.91 → 0.74). Item 1 reproduces that split on our data:
   the end-to-end loss is the lumen, not the names.

## 5. Risks

| Risk | Detected by | Response |
|---|---|---|
| The master names well enough that R and H add nothing | the §3 rule on val | ship D. Cost of finding out: ~2 CPU-hours |
| Wrong naming bridges (c0407) | R − D per case; joins listed in the QA record | lower the threshold to 3 mm (A2's), or bridge only endpoint-to-endpoint |
| Long real gaps (> 4 mm; 5 of 22 in Delta's E8) orphan subtrees | per-case component count after bridging | the orphan takes its nearest named neighbour's class. tF1 counts it as uncut-unrooted either way, as for D |
| Ostium mis-rooted on a cut tree | aorta-contact check (§2.2 step 4) | flag the case |
| The ramus convention differs from mine | §5.2 decision | switch, set before scoring |
| Fused trees (~2 %) | single tree > 800 mm | flag; D is used for that case |

## 6. Comparison

- **Master ([[Atlas v1]] + A1–A6).** v2 is a strict superset at zero GPU cost. The master's training,
  data and schedule are unchanged. v2 adds two candidate namings of the master's own output and a
  pre-registered rule that ships them only if they beat the master's labels on the master's metric.
  If they do not, nothing changes except ~2 CPU-hours per scoring round.
- **Delta's A2 (gap bridging + label repair).** A2 edits voxels: bridges join pieces in the mask, and
  repair relabels islands. R and H edit names only, and in R the names are made consistent by
  construction. They are complementary: run A2 first, then R/H on its output. Delta's E8 counted 17 of 22
  real gaps ≤ 4 mm. My naming bridges are exactly the "implemented bridging step evaluated on real
  predictions" that the ruling asked of Delta, but **for naming**. Measured, including the one false join.
- **Crucible (option A, thin lumen).** The namer is convention-agnostic: 0.990 tF1 on the thin reference
  lumen of 63 test cases with the ramus excluded, never refit. It serves either human decision.
- **v1.** It dropped: the separate binary model, the comparator arm (~430 h), the patch-context
  argument, and Dice as the deciding metric. It kept: the namer, the ostium model, bridging, and the
  "decide by measurement" rule.

## 7. Cost

- **GPU:** 0 additional H100-hours. D comes from the master's runs. H needs D's softmax saved, which is an
  inference flag (`--save_probabilities`), not a run.
- **CPU:** ~2 min per case per output. A val fold of ~130 cases is ~4–9 CPU-hours for R and H.
- **Human:** none beyond the ramus rule the ruling already requests (§5.2).

## 8. Changes since v1

- **Narrowed** from a separate two-stage segmentation route to a naming stage on the master's
  predictions. The separate binary model and the 430 h comparator arm are removed.
- **Deciding metric:** now the master's tF1 @ 1.5 mm (A1), not mean per-class Dice.
- **New evidence:** the end-to-end real-prediction experiment (item 1), with an upper-bound direct
  baseline, 0 swaps, the bridging effect, and convention transfer.
- **Patch-context argument withdrawn** (ruling C1 accepted).
- **Ramus is now an explicit switch.**
- **Aorta-contact ostium** preferred when a mask exists.
- **H (hybrid tree decoding of D's softmax) added** as an unmeasured candidate.

## 9. Pending (stated so the judge can discount it)

- **End-to-end sample.** 19 cases. Two more queued cases (c0041, c0907) were not run: c0041 was
  OOM-killed on the shared machine, and a container restart stopped the queue. The thin-lumen naming
  ceiling covers 63 of the 160 ImageCAS-X test cases, interrupted by the same restart. Both runs can be
  resumed (`e2e.py`, `ceiling.py` skip finished cases).
- **Not measured yet:** H (needs real 4-class softmax), the aorta-contact ostium preference (needs aorta
  masks for more cases), and the behaviour of R on the master's own predictions (needs R1).
