---
tags: [plans/experiment, A31, A10, D26, D8, L5, seed-anchoring, tF1, round10]
author: Bridge
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Seed-anchored reads move A10 through where vessels stop, not through lumen width

**Question (A31.2, L5 groundwork, issue #113).** D26 starts every class of a pool read as a full copy of the
TotalSegmentator seed. Janus 0 draws the lumen about one voxel inside ImageCAS-X's (#43). What convention do reads
redrawn from such a seed follow, and what does that do to A10 on the pool?

**Answer.**
- **Width does not matter to A10; extent does.** tF1 is a centreline score with a 1.5 mm gap tolerance, so a
  one-voxel boundary convention barely moves it (#43: tolerant Dice 0.97, tF1 0.91 against plain Dice 0.88). What
  tF1 sees is **where each vessel stops** and which thin branches exist.
- **If both reads keep a seed that stops early, A10 fails a perfect model.** On the 80 ImageCAS-X val trees, a model
  that traces ImageCAS-X's full extent scores below inter-read in LAD, LCx and RCA when both reads stop where the
  seed stops: by 0.02–0.04 if the seed keeps 96 % of the centreline, **0.08–0.10 at 88 %** (beyond D6's 0.05
  margin) and 0.24–0.75 at 56–20 %. Inter-read stays near 1, because the reads share the seed's stopping points. LM is
  untouched (it is short and wide, and every seed keeps it).
- **If only one read is anchored, the bias reverses:** inter-read falls and A10 passes too easily (+0.03 at 88 %,
  +0.21 to +0.32 at 34 %).
- **A31.2's flag separates the cases once the seed misses about a tenth of the tree** (LAD, LCx, RCA): seed-vs-read
  equals inter-read exactly when both reads are anchored, and sits 0.06–0.80 below it when readers trace
  independently. With a near-complete seed (96 %) it fires without anchoring, but then the bias is inside the margin.
  In LM it fires either way and says nothing.
- **The tell-tale on real reads is precision without recall.** An extent mismatch costs the model precision against
  the read (its centreline runs past the read's end) and costs no recall. A model that fails A10 by precision alone,
  with recall near 1, is being scored against a shorter convention, not failing.

## Method

CPU only, on the 80 ImageCAS-X val references (fold 0; inspected since Round 5; fetched by
`experiments/Bridge/r10/fetch_val_refs.py`, which checks the list against `trillium/sealed_test.json` first).
No CT, prediction or pool data: every mask is a deterministic edit of the reference.
Code: `experiments/Bridge/r10/anchoring.py` → `anchoring.json` (seeds at 0.6 / 0.8 / 1.0 mm) and
`anchoring_mild.json` (0.45 / 0.5 mm).

- **Truth T:** ImageCAS-X collapsed to four classes (`territory.py`, D25).
- **Truncation trunc(T, r):** keep voxels whose nearest skeleton point has radius ≥ r mm, then only the components
  touching an ostium of T. Thin distal vessels and thin side branches go first, as they would for a seed that
  cannot resolve small vessels.
- **Seed S = trunc(T, r_s).** Its retained share of T's centreline is reported.
- **Readers:** reader i = trunc(T, u_i), u_i ~ U(0.20, 0.45) mm per reader and case: two readers who stop at
  slightly different calibres. An anchored reader stops at the seed instead: trunc(T, max(u_i, r_s)).
- **Model M = T:** a model with ImageCAS-X's extent. Janus 0 is trained on it, and its val centreline recall
  against T is 0.94 (#43).
- **Scores:** tF1 @ 1.5 mm (`segtrain.tf1`, thick-rule ostia; aorta-free and so provisional, which is fine for a
  paired contrast on identical references). Inter = mean of both directions; model = mean over the two reads;
  contrast = model − inter (A10's quantity); seed = mean(tF1(R1 → S), tF1(S → R1)).

## Results (80 cases; class means)

**Both readers independent (α = 0):** inter-read LAD 0.985, LCx 0.983, RCA 0.993, LM 1.000. The model is at or
above inter-read in every class (contrast +0.000 to +0.006; per-patient SD of the contrast 0.017–0.039). A10 would
pass a model with ImageCAS-X's extent comfortably.

**Both readers anchored (α = 1)**, by how much of T's centreline the seed keeps:

| Seed r_s (share of centreline kept) | Class | Inter-read | Model-vs-read | **Contrast** | Seed-vs-read |
|---|---|---|---|---|---|
| 0.6 mm (56 %) | LAD | 1.000 | 0.657 | **−0.343** | 1.000 |
| | LCx | 1.000 | 0.617 | **−0.383** | 1.000 |
| | RCA | 0.975 | 0.734 | **−0.241** | 0.975 |
| | LM | 1.000 | 0.998 | −0.002 | 1.000 |
| 0.8 mm (34 %) | LAD / LCx / RCA | 0.987 / 0.987 / 0.924 | 0.403 / 0.343 / 0.584 | **−0.58 / −0.64 / −0.34** | = inter |
| 1.0 mm (20 %) | LAD / LCx / RCA | 0.947 / 0.934 / 0.842 | 0.218 / 0.182 / 0.407 | **−0.73 / −0.75 / −0.43** | = inter |

**Milder seeds** (`anchoring_mild.json`; the 0.5 mm row also runs one anchored reader).

| Seed r_s (centreline kept) | Both anchored: contrast LAD / LCx / RCA | Seed-vs-read, independent readers (inter-read ≈ 0.98–0.99) | One anchored: contrast |
|---|---|---|---|
| 0.45 mm (96 %) | −0.039 / −0.033 / −0.016 | 0.97 / 0.98 / 0.99: **the flag fires without anchoring** | — |
| 0.5 mm (88 %) | **−0.087 / −0.101 / −0.079** | 0.92 / 0.91 / 0.92 (flag silent) | +0.032 / +0.028 / +0.031 |

So the bias crosses D6's 0.05 margin once the seed misses about a tenth of the tree and both reads keep it. A seed
that misses only a few percent cannot be told apart from careful independent readers by the flag; there, the flag
fires without meaning anything, but the bias it would warn of is also within the margin. That is why the flag is
read with the seed-edit sizes (wave-1 note §4): anchoring shows as reads that add nothing beyond the seed.


**One reader anchored, one not (α = 0.5, r_s = 0.8):** inter-read falls to LAD 0.40, LCx 0.34, RCA 0.58, while the
model matches the independent read, so the contrast is **+0.30 / +0.32 / +0.21**.

**Seed-vs-read with independent readers** (the flag's "no" side): r_s 0.6 → LAD 0.67, LCx 0.63, RCA 0.74; 0.8 →
0.41 / 0.34 / 0.58; 1.0 → 0.21 / 0.17 / 0.39, all well below inter-read (≥ 0.98). In LM it is 0.93–1.00 throughout.

## Reading

1. **The size of the effect.** A10's margin is 0.05 (D6). A seed that misses about a tenth of the distal tree, if
   both readers keep its stopping points, already moves the contrast past the margin (−0.08 to −0.10); a seed that
   misses half moves it by several times the margin. If anchoring happens at that scale, it decides A10.
2. **The direction depends on how many reads are anchored.** Both anchored: biased against a model with the expert's
   extent. One anchored: biased for any model. Mixed habits across annotators would add a large, patient-level
   variance to the contrast, which rule C would read as a need for a bigger seal.
3. **A fine-tune on anchored reads would learn the seed's extent.** Janus 1 would then pass A10 on the pool by
   stopping where TotalSegmentator stops, and lose tree against ImageCAS-X. That is a silent change of convention
   away from D8 (ImageCAS-X's lumen as drawn), not a better model. The val-80 guard in the Janus-1 rule (lower bound
   > −0.02) is what would catch it.
4. **What the convention of seed-anchored reads is:** in lumen width, whatever the annotator redraws (D12 allows
   it; tF1 does not care); in extent, the seed's, unless annotators extend vessels the seed missed. The protocol
   says to stop "where the lumen is no longer confidently distinguishable", which is ImageCAS-X's rule, not
   TotalSegmentator's.

## What it changes (proposed)

- **A31.2 is read per class, LM excluded,** together with the seed-edit sizes (share of each read's centreline
  outside the seed). Both reads of a patient anchored = the bias case; one anchored = the opposite bias.
- **A10's report splits each class's tF1 into recall and precision**, for model-vs-read and for inter-read. A
  precision-only deficit with recall near 1 is an extent mismatch, reported as such.
- **L5 recommendation to the lead**, if wave 1 shows anchoring in LAD, LCx or RCA (seed-vs-read ≥ inter-read − 0.02
  and most reads adding under 5 % of centreline beyond the seed):
  1. first, an annotator instruction (no D-number change): trace each vessel to where its lumen is no longer
     distinguishable, beyond the seed's end; measure again on the next 30 reads;
  2. if anchoring persists, A10 on the pool is not the test D6 intends. The lead chooses between accepting the
     seed's extent as the pool convention (a change to D8's meaning for the pool, which also changes what Janus 1
     learns) and requiring the sealed-80 model-vs-ImageCAS-X look (A26) to pass a pre-set line as well.
- Nothing here needs GPU or changes the seal size directly; rule C uses the measured s_d, which already contains
  whatever anchoring does to the spread.

## Limits

- The seed is modelled as a calibre cut-off. TotalSegmentator's real errors also include breaks, veins and missed
  side branches. The measured seed-vs-read and seed-edit sizes on wave 1 replace this model.
- Readers are modelled as stopping at a calibre. Real readers also miss or add branches; that adds variance, not
  bias, in the independent case.
- The model is ImageCAS-X itself (a perfect extent model). Janus 0's own extent is slightly shorter (centreline
  recall 0.94), which shrinks the both-anchored deficit by a few hundredths.
- Provisional ostia (no aorta) are used on both sides of every contrast, so they cancel.
