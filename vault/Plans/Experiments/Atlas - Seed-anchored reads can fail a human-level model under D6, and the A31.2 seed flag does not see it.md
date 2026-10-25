---
tags: [plans/experiment, round10, A31, A10, D6, D26, L5, seed, anchoring, convention]
author: Atlas
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
code: experiments/Atlas/r10_anchoring.py, experiments/Atlas/r10_anchoring_pr.py
---

# Seed-anchored reads can fail a human-level model under D6, and the A31.2 seed flag does not see it

**Question.** Pool reads start from a full copy of the binary TotalSegmentator seed in every class (D26), and annotators
may redraw freely (D12). Janus 0 draws the lumen about one voxel inside ImageCAS-X's, and traces ImageCAS-X's distal
extent (#43). Two things follow:

1. What convention do seed-started reads follow?
2. What does that do to A10 (D6: per class, model-vs-read tF1 non-inferior to inter-read tF1 within 0.05) on the
   pool?

Round 9 named this its most important new risk (A31.2, L5).

**Method.**
- Phantoms and scoring are Bridge's wave-1 code: `synth.tree` (LM, LAD, LCx and RCA tubes beside an aorta, on a
  0.5 mm grid) and `score_wave1.pair`, which calls `segtrain.tf1` at the A1c pin with the aorta ostium.
- **Width.** A model equal to the truth but eroded or dilated by one voxel.
- **Extent.** In `r10_anchoring.py`, each case has:
  - **truth**: the full tree, i.e. the ImageCAS-X convention (as far as the vessel goes);
  - **seed**: its own jitter and width, with each vessel's last segment cut to s ~ U(s0 ± 0.1);
  - **two reads**: each starts at the seed's ends and extends each vessel by a fraction e_k ~ U(e ± 0.15) of what the
    seed misses, with its own jitter and a redrawn outline;
  - **model**: human-level by construction, a third reader who follows each vessel to 85–100 % of its end,
    independent of the seed.
  - Cells cross the seed extent s0 ∈ {0.5, 0.8} with reader extension e ∈ {0, 0.5, 1}, plus an unanchored baseline
    (s0 = 1, e = 1). 24 cases per cell.
- **The split.** `r10_anchoring_pr.py` splits model-vs-read into recall and precision (12 cases per cell, the same
  draws).

## Results

**Width does not move tF1.** A one-voxel erosion keeps tF1 at **1.000** while Dice falls to 0.69 and volume to 53 %.
A one-voxel dilation gives tF1 0.972 and Dice 0.77. This is the phantom form of Janus 0's real reading: tolerant Dice
0.97 against plain Dice 0.88, with tF1 0.909 (#43).

**Extent does.** Means per class (LAD / LCx / RCA):

| Seed extent s0 | Reader extension e | Inter-read | Model-vs-read | δ = model − inter | D6 point verdict | A31.2 seed flag fires |
|---|---|---|---|---|---|---|
| 1.0 (no anchor) | 1.0 | 0.983 / 0.987 / 0.995 | 0.966 / 0.975 / 0.991 | −0.017 / −0.012 / −0.003 | pass | — |
| 0.8 | 1.0 | 0.944 / 0.975 / 0.990 | 0.966 / 0.976 / 0.994 | +0.022 / 0.001 / 0.004 | pass | LAD |
| 0.8 | 0.5 | 0.969 / 0.985 / 0.990 | 0.967 / 0.973 / 0.989 | −0.002 / −0.012 / −0.001 | pass | LAD |
| 0.8 | 0 (anchored) | 0.976 / 0.981 / 0.992 | 0.959 / 0.965 / 0.990 | −0.017 / −0.016 / −0.002 | pass | LCx |
| 0.5 | 1.0 | 0.958 / 0.979 / 0.998 | 0.955 / 0.973 / 0.993 | −0.003 / −0.006 / −0.005 | pass | — |
| 0.5 | 0.5 | 0.973 / 0.983 / 0.999 | 0.942 / 0.961 / 0.980 | **−0.031 / −0.022 / −0.019** | pass at the point; power collapses | — |
| 0.5 | 0 (anchored) | 0.953 / 0.964 / 0.889 | 0.882 / 0.879 / 0.810 | **−0.071 / −0.085 / −0.079** | **fail, all three** | LCx only |

**Model-vs-read recall and precision**, LAD / LCx / RCA:

| Cell | Model recall | Model precision | Inter-read recall = precision |
|---|---|---|---|
| s0 1.0, e 1.0 (no anchor) | 0.96 / 0.98 / 0.98 | 0.98 / 0.98 / 0.99 | 0.99 / 0.98 / 0.99 |
| s0 0.8, e 0 | 0.98 / 0.99 / 1.00 | 0.96 / 0.95 / 0.98 | 0.98 / 0.98 / 0.99 |
| s0 0.5, e 0.5 | 0.96 / 0.98 / 1.00 | 0.94 / 0.95 / 0.97 | 0.98 / 0.99 / 1.00 |
| s0 0.5, e 0 | 0.96 / 0.97 / 0.96 | **0.82 / 0.81 / 0.83** | 0.95 / 0.96 / 0.94–0.98 |

## Reading

1. **What convention seed-started reads follow.**
   - **Width:** the seed's outline unless redrawn. tF1 cannot see it: centrelines move by less than the 1.5 mm
     tolerance. Width shows up only in Dice and volume. That is why the A31 domain check must report tolerant Dice and
     the volume ratio beside plain Dice (#43): TotalSegmentator's outline and ImageCAS-X's are different conventions.
   - **Extent:** wherever the reader stops. A reader who keeps the seed's distal ends draws a shorter tree than
     ImageCAS-X's convention, and two such readers agree with each other because they share the anchor.
2. **What it does to A10.** A model that follows the vessel (as Janus 0 does, and as D8 asks) is charged for every
   millimetre it traces past the reads.
   - With a seed that reaches half of each distal segment and readers who do not extend it, a human-level model is
     0.07–0.085 below inter-read, and **fails D6 in every class**.
   - With half-extension it is 0.02–0.03 below. Under the seal power table, that collapses P(pass) to 0.15–0.6 at
     150–250 patients ([[Atlas - On Janus 0's own spread the 150-patient seal passes a human-level model 0.79 of the time if reads vary independently of the model, and more if hard cases are shared]]).
   - A reader who follows the vessel (e = 1) removes the effect whatever the seed.
3. **A31.2's flag (seed-vs-read ≥ inter-read − 0.02) does not detect this.**
   - It fired in only one class of the worst cell.
   - It fired in cells where nothing is wrong (s0 0.8, e 1: δ ≥ 0).
   - The reason: the seed carries its own jitter and width, so seed-vs-read stays at 0.70–0.97 whether or not the
     extent is anchored.
   - Bridge foresaw part of this (the flag "needs the seed to be clearly worse than a reader") and added edit sizes.
4. **The signature that does detect it is the precision–recall gap of model-vs-read.**
   - Anchoring leaves recall alone (the model covers the reads, 0.96–0.97) and lowers precision (0.81–0.83).
   - Without anchoring the two are equal within 0.02.
   - It needs no seed naming and no seed file, and it is computed from the same `tree_f1` call A10 already makes
     (`TreeF1.recall`, `.precision`).

## What it changes

- **Proposed A31.2′:**
  - Report, per class on the primary non-sealed patients, model-vs-read precision minus recall (patient bootstrap
    CI), beside Bridge's seed-vs-read and edit sizes.
  - **Anchoring is declared in a class** when the gap is below −0.03 with its CI excluding 0, and inter-read
    precision is not lower too (so it is the model running past the reads, not the reads disagreeing).
  - Then L5 goes to the lead with the measured δ̂.
  - A31.2's flag stays as a report.
- **L5 (the lead's).** If anchoring is declared, A10 against the reads measures agreement with the seed's extent,
  not D6's intent. Atlas recommends that acceptance then also requires the sealed ImageCAS-X 80 milestone (A26:
  model vs expert, red flag at 0.03 below open-36). The lead may further choose to have readers told, in the
  SegQueue14 protocol notes, to follow each vessel past the seed's end as far as the contrast lets them. D12 already
  allows this. It is an instruction inside the project, not an outside request (D31).
- **Fine-tuning on anchored reads teaches the anchor.** Janus 1 would learn to stop where the seed stops, and its
  model-vs-read tF1 would rise for that reason. So D35 decisions also report the val-80 tF1 against ImageCAS-X
  (the forgetting guard), and a Janus 1 that gains on D35 while losing recall on val 80 is read as learning the
  anchor, not as better.
- **Limits.**
  - Phantoms have three distal ends and no side branches. Real seeds miss whole side branches too, which is the same
    effect in a larger form.
  - A one-voxel-thinner phantom tube drawn with its own jitter lost contact where `synth.tree` carves the aorta. That
    cost tF1 here, but it is a phantom artefact (Janus 0's real thinner lumen roots fine, #43), so the extent runs use
    one width. Width is tested apart, by pure erosion.
  - The size of the real effect depends on how far TotalSegmentator's coronary seed reaches. Its only published
    lumen DSC against an expert is 70.5 ± 6.2 on ImageCAS-X's test set (arXiv:2608.30404, Table 2; the version is
    not stated). Its coronary model is a separately licensed subtask (`-ta coronary_arteries`; the model changed at
    v2.12.0), so wave 1's seed version must be recorded. Wave 1 measures the real effect.
- **Prior evidence that anchoring is real.**
  - Adjustment from an anchor is typically insufficient: Tversky & Kahneman 1974, Science 185:1124,
    doi:10.1126/science.185.4157.1124, "Adjustment and anchoring".
  - Machine pre-annotation biases annotators toward the tool's systematic errors: Fort & Sagot 2010, LAW IV,
    pp. 56–63, ACL Anthology W10-1807, §4.3.
  - "Anchoring bias is present when clinicians edit AI-generated contours": Constantinou et al., Clin Oncol 2025,
    37:103660, doi:10.1016/j.clon.2024.10.032 (abstract).
