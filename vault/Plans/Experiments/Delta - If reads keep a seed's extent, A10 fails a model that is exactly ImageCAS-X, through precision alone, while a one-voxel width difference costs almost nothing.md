---
tags: [plans/experiment, round10, A10, D6, A31, L5, seed-anchoring, D26, tree-f1, lumen-width]
author: Delta
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# If reads keep a seed's extent, A10 fails a model that is exactly ImageCAS-X, through precision alone, while a one-voxel width difference costs almost nothing

**Question.** D26 starts every class as a copy of the TotalSegmentator seed. Janus 0 draws the lumen about one voxel inside ImageCAS-X's ([[icx4 - Results]]). What would A10 (D6: model-vs-read tF1 non-inferior to inter-read within 0.05 per class) measure:
- (a) if the reads' **width** differs from the model's?
- (b) if the reads keep the seed's **extent** (anchoring, A31.2, L5)?

**Method.** `experiments/Delta/r10/anchoring_sim.py`, CPU. Summary by `summarise_anchoring.py`; rows in `anchoring_val80.jsonl`.

**References.** ImageCAS-X's 80 val references (fetched from Zenodo, CC BY 4.0; no sealed case), collapsed by `territory.to_four` (D25). The pinned `segtrain.tf1` (A1c `24441cf8…5254`, 1.5 mm).
- Ostia are ImageCAS-X's released start points used as the pseudo-aorta (Delta v9's P2 mechanics), so that no perturbation moves an ostium.
- Trims never come within 10 mm of an ostium along the vessel, so the **LM is never trimmed** and scores 1.0 by construction.

**Distal tips.** Skeleton end points more than 8 mm from an ostium. The geodesic distance from them inside the mask (`MCP_Geometric`) defines a per-tip trim. A side branch shorter than the trim disappears, as a seed's short branches do.

| Object | Definition |
|---|---|
| M0 | ImageCAS-X exactly: a model with no error at all |
| M1 | M0 thinned to a volume ratio of 0.87 without touching its centreline (Janus 0 on val: 0.867, with tolerant Dice 0.97) |
| Independent reads (a, b) | Each tip trimmed by its own U[0, 8] mm |
| `indep_wide` | Independent reads dilated by one voxel (a reader or seed convention one voxel outside ImageCAS-X) |
| Anchored reads at L (a, b) | A seed that stops L mm short of every tip, with each tip trimmed a further U[0, 2] mm (the reader cuts the seed down and adds nothing). L = 0, 5, 10, 20 |

- **Inter-read:** the mean of tF1(a → b) and tF1(b → a).
- **Model-vs-read:** the mean over both reads, with the read as the reference.
- **The contrast:** d = model − inter, per class, mean over cases with a case-bootstrap 95 % CI.
- A (case, class) is dropped from a condition when the trimmed reads lost that tree (inter-read exactly 0). That happens when a trimmed RCA falls under tF1's 1000-voxel tree minimum, so it has no ostium. 1 pair at L = 10 and L = 20, counted in the JSON.

## Result

Interim, n = 9 of 80 cases. The tables are regenerated from `anchoring_summary.json` when the run completes. RESULTS_TABLE

## Reading

1. **Width is not what A10 measures.**
   - Thinning the model to Janus 0's volume ratio (M1 − M0), or widening the reads by a voxel, moves tF1 by ≤ 0.012 in every class and condition.
   - tF1 is a centreline metric with a 1.5 mm tolerance. Atlas's finding that Janus 0 sits one voxel inside ImageCAS-X's boundary does not touch A10, whatever width convention the reads follow.
2. **Extent is what A10 measures, and anchoring makes it the seed's extent.**
   - With independent reads, the perfect model sits where a reader sits (d ≈ 0, with CIs that include 0 except a small negative LAD). This is the simulation's calibration: a perfect model is human-level.
   - With anchored reads, the reads agree almost perfectly (inter-read 0.97–1.00, because they share the seed's ends). A model that traces ImageCAS-X's extent loses **precision** beyond those ends, and its recall stays 1.0.
   - From L = 5 mm, d is at or past D6's −0.05 margin in LAD, LCx and RCA. **A10 would fail a model with no error at all**, and pass a model that had learned to stop where the seed stops.
3. **A31.2's seed flag cannot tell a good seed from anchoring by itself.**
   - A seed only 5 mm short of ImageCAS-X scores 0.96–0.99 against an *independent* read. That is above the independent inter-read in LCx and RCA, so the flag (seed-vs-read ≥ inter-read − 0.02) fires with no anchoring at all.
   - This is Bridge's own caveat (wave-1 note §4.2), now with a size. The flag needs to know how short the real seed is. That is Job S (Delta v10 §5.2): TotalSegmentator on the val 80, scored against ImageCAS-X.
4. **The signature of anchoring is in the A10 decomposition:** recall ≈ 1 with precision falling, and an inter-read near 1.0. Reporting A10's recall and precision halves beside it costs nothing and separates "the model errs" from "the reads stop short".

## What it changes

- L5 is not hypothetical if the real seed stops ≥ 5 mm short of the expert extent in a class. TotalSegmentator's 70.5 zero-shot DSC on ImageCAS-X (arXiv:2608.30404, Table 2) says the seed is far from the expert lumen, but not in which direction its extent errs. Job S measures that before any read exists.
- Delta v10 §5.3 pre-registers what follows: A10 as written if the seed's recall is ≥ 0.95 or the reads extend it; otherwise A10 is reported split into recall and precision, and the L5 recommendation applies.
- The val-80 guard on Janus 1 (Delta v10 §4.3 b) is what stops a fine-tune from buying D35 by learning to stop short.

## Limits

- Synthetic reads: reader behaviour is modelled as distal trims only. Real readers also extend, redraw and miss side branches mid-vessel, and real seeds also overshoot and include veins (components dropped whole, as Bridge's comparison does).
- The direction of the bias reverses if the seed overshoots ImageCAS-X: the deficit would then sit in recall.
- The 10 mm ostium guard makes the LM immune by construction.
