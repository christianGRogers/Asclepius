---
tags: [plans, candidate, branch-labelling, double-reads, round-3]
author: Bridge
round: 3
status: candidate
updated: 2026-10-08
---

# Bridge v3: the master, with naming decided at the level of decisions, not voxels, for training and double reads

## 0. Improve or start again?

**Improve.** Bridge v2's two contributions are already binding on the master:

- **A7:** rule renaming R and the hybrid H as naming competitors.
- **A8:** the ramus switch.

I have no evidenced recipe that could beat the master on tF1, and I will not pretend to. The decisions in
[[Human decisions]] do two things to this plan:

- They confirm its premise. The target is the original ImageCAS mask split into four classes (D0, D4), so
  naming really is "split a given tree".
- They open the one technical question where structure-aware naming has something to offer: **every
  case has two reads (D2).**

v3 therefore does three things:

1. Conforms the namer to D0–D3 and re-quotes every naming number under them. Several numbers get worse,
   and I say so (§4).
2. Finishes the measurements Round 2 asked for (§4, items 2–4).
3. Proposes how to use the two reads, built on one measured fact: under the territory rule (D1), a case's
   names are fixed by a handful of decisions (ostium, end of the LM, which child is the LAD, the ramus).

## 1. Thesis

Under D1 and D1b, two annotators who agree on the lumen and on four decisions per left tree produce the
same names everywhere, except a few millimetres at the carina:

- the ostium;
- where the LM ends;
- which child is the LAD;
- whether a ramus exists.

The namer and the projected proxy, two independent namers, disagree on a median 0.26 % of voxels, all
within 10 mm of the carina ([[Atlas - The rule labeller disagrees with the projected proxy on 0.3 percent of voxels, all at the carina]]).

So the two reads should be compared and fused at two levels, not as two voxel maps:

- **Lumen level:** which voxels are vessel. This is a fuzzy boundary; use a soft or ignore treatment.
- **Decision level:** the four naming decisions. These are discrete; agree, or adjudicate.

Treating name disagreements as voxel noise would teach the network that LAD and LCx are interchangeable
near the carina, and would spend `ignore` on a boundary that is a convention.

## 2. Recipe

### 2.1 Training, data, schedule and metric: unchanged

[[Atlas v3]] / [[Master plan]], with A1–A9, D0–D5. The namer runs with **ramus → LCx** (D1b),
territory mapping (D1) and naming bridges (4 mm, graph only; A7 audit).

### 2.2 Using two reads per case (the D2 question)

Per case, with reads A and B (each a 4-class split of the ImageCAS mask, possibly with lumen edits):

1. **Lumen.**
   - Voxels in both reads' union are vessel.
   - Voxels in exactly one read are **soft (0.5)** in the foreground channel.
   - nnU-Net trains on hard labels, so the practical form is: voxels in exactly one read get `ignore`
     when the disagreement band is ≤ 1 voxel thick (boundary jitter), and stay vessel when it is a whole
     branch present in one read (a recall disagreement; the more complete read wins, as tF1 rewards
     recall of rooted centreline).
   - Under D4 both reads start from the same mask, so lumen disagreement should be small. This is
     measured on wave 1 (§3).
   - The five decisions are: ostium, LM end, LAD/LCx side, tree identity (left vs right) and ramus.
     They are extracted from each read's own labels by `decisions.py`'s rules.
2. **Decisions.** Run the namer's decision extractor on each read's own labels. It reads ostium, LM end,
   LAD/LCx child and ramus off the labelled skeleton (no learning).
   - **All four agree:** names = either read's names, which match outside a ≤ 3 mm carina band. Put that
     band to `ignore`; this is the A4 rule applied to reads.
   - **Any decision disagrees:** a third reader adjudicates that one decision. The namer's choice is shown
     as a suggestion, never as a seed (D4 forbids four-class starting labels). Until adjudicated, the case
     is excluded from training and from the sealed test; it is not voxel-masked.
3. **Inter-rater ceiling (all 1000 cases).** Report the macro tF1 of A against B per case, split into
   *lumen-only* disagreement (score B's names relabelled onto A's lumen) and *decision* disagreement. The
   deciding metric for the model is then read against the half of the ceiling that is achievable.

### 2.3 The naming competitors (A7, unchanged in form)

D, R and H are scored on R1 val. The adoption rule is as binding: the paired CI must exclude 0 and the
swap rate must be no higher. v3 adds only that R and H use ramus → LCx.

## 3. Evaluation

- The master's: tF1 @ 1.5 mm (D3), A1 ostium, A9.
- Two-read procedure: on wave 1 (first ~50 double-read cases), report:
  - lumen-disagreement Dice and band thickness;
  - the decision-disagreement rate per decision;
  - the fraction of disagreeing voxels inside the 3 mm carina band;
  - inter-rater tF1, split as in §2.2.3.
- **Pre-registered expectation, to be falsified:** ≥ 80 % of name-disagreeing voxels lie in cases with a
  decision disagreement, or within the carina band. If not, naming disagreement is diffuse, the
  decision-level fusion has no basis, and v3 reverts to voxel-level fusion (the vault's
  [[Fusing multiple annotations and learning from noisy labels]] default).

## 4. Evidence: re-quoted under D0, D1 and D1b

All figures use territory mapping, **ramus → LCx** (namer switch and reference), and IM scored as LCx.
In Round 1 IM was left unscored, which flattered the namer.

1. **Naming on the binding convention (thick ImageCAS masks), against ImageCAS-X names projected onto
   them.** Frozen namer (Round-1 v3 rules + ramus→LCx + 4 mm naming bridges; `label.py`
   md5 06f53291…). Script `evaluate.py` + `summ_d1b.py`. Note:
   [[Bridge - Under the binding ramus rule the namer gets 88 percent of unseen thick-mask cases fully right]].

   | Set | n | all 4 classes Dice ≥ 0.8 | swap (any class < 0.5) | pooled voxel accuracy |
   |---|---|---|---|---|
   | dev | 96 | 0.917 | 6.2 % | 97.5 % |
   | **held-out** | **76** | **0.882** | **7.9 %** | **97.7 %** |

   The Round-1 quote (0.949 on 59 held-out cases) excluded the ramus and is superseded by this row.
   - Held-out failures: LM end placed at a later junction (c0108, c0861), ostium (c0211, c0519), fused
     trees (c0484), and a ramus not detected (c0786, c0796).
   - A dev-only ramus diagnostic: 14 ImageCAS-X ramus branches leaving the LAD side. Geometry does not
     separate a ramus from an early diagonal well (best rule 9 true / 3 false). A looser detector changed
     held-out results by < 0.001, so the rule was left as frozen.
2. **End to end on real stage-1 output, ramus → LCx, all classes**
   ([[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]], Round 3 section).
   - 21 ImageCAS-X test cases, now including c0041 and c0907.
   - tF1 @ 1.5: namer **0.911** vs oracle naming **0.920**. Paired −0.010, CI [−0.016, −0.005]. On the 15
     never-seen cases: −0.011, CI [−0.019, −0.005].
   - **0 swaps.** No-bridging variant: 0.883.
   - This is a secondary cross-check: the stage-1 model is the released thin-convention one.
3. **Thin-lumen naming ceiling, all 160 ImageCAS-X test cases, ramus → LCx, all classes:** tF1 @ 1.5 mean
   **0.973**, median 0.991; ≥ 0.9 in 94.4 %; 5 swaps; 0 failures. On the 142 never-seen cases: 0.970.
4. **Ostium vs ImageCAS-X start points** (aorta-contact truth, all 800 centreline files fetched):
   - within 5 mm in 90.7 % of 172 cases (89.5 % held-out); within 10 mm in 97.1 %; median 3.3 mm.
   - The aorta-*preferred* ostium (TotalSegmentator mask) is **not implemented**. It needs aorta masks this
     environment cannot produce at scale. The master's A1 runs TotalSegmentator on Trillium anyway, and
     the namer will read it there.
5. Unchanged from v2: ostium learned from 5–10 cases; naming bridges needed on real cut trees.
6. **Two-read stand-in (new):** [[Bridge - Naming disagreements between two namings of the same lumen sit in five discrete decisions]].
   - Two independent namings of the same thick lumen: ImageCAS-X names projected, against the rule namer;
     170 cases.
   - 87 % of disagreeing voxels lie in the carina band or in cases with a disagreeing decision; 99.7 % on
     the 75 held-out cases.
   - 21 % of cases carry a decision disagreement, most of them the ramus.
   - The §3 expectation holds on the stand-in. The first extractor version omitted two of the five
     decisions, and that is disclosed in the note.
7. **GPU experiment, prepared, awaiting the lead's run**
   ([[Bridge - PENDING Trillium run - does the namer or grammar decoding beat a direct model's own names]],
   `trillium/bridge/`).
   - A direct 4-class nnU-Net with the master recipe, trained ≤ 19.5 h on one H100 on the territory proxy
     of the 560 ImageCAS-X train cases.
   - D / R / H / O scored by tF1 on the master's 80 val cases, with the A7 adoption rule applied.
   - This is the first real-direct-model test of the naming claim. The note pre-registers what each
     outcome changes.

## 5. Risks

| Risk | Detected by | Response |
|---|---|---|
| Two reads disagree diffusely, not at decisions | §3 pre-registered check, wave 1 | revert to voxel-level fusion |
| Decision extraction from a read's labels is wrong | compare against the read's own voxel names: disagreement > 1 % outside the band | fix the extractor; adjudication load reported |
| Adjudication load too high | decision-disagreement rate, wave 1 | if > 20 % of cases, adjudicate only ostium and LAD/LCx; the ramus goes by rule |
| The namer misses a ramus (held-out c0786, c0796) | decision comparison against reads | the reads decide; the namer is a suggestion only |

## 6. Comparison

- **Master:** it trains on what the readers produce. v3 decides what that is when two reads exist, at no
  GPU cost and with an adjudication step bounded by measurement.
- **Other candidates:** I will answer their two-read proposals in v3 updates once filed. The specific
  claim to test against them is that voxel-level fusion masks carina voxels that are a convention, not
  noise.

## 7. Cost

- GPU 0.
- CPU: decision extraction ~1 min per read.
- Human: third-reader adjudication on decision-disagreeing cases only (rate measured on wave 1).

## 8. Changes since v2

- Conformed to D0–D5.
- Ramus → LCx.
- All numbers re-quoted with IM scored. The held-out naming figure falls from 0.949 to 0.882, stated in §4.
- New §2.2: two-read fusion at lumen and decision level.
- Round-2 requests done:
  - the 160-case ceiling (0.973);
  - the all-classes with-ramus e2e figure (−0.010, 21 cases);
  - c0041 and c0907;
  - ostium against the aorta-contact truth (90.7 % ≤ 5 mm).
- The aorta-preferred ostium is not implemented.
- Trillium experiment prepared.
