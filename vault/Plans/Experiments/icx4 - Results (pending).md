---
aliases: [icx4 results]
tags: [plans, experiment, fir, icx4, four-class, round10]
status: {{status}}
updated: {{date}}
issue: christianGRogers/Asclepius#43
---

# icx4 results: the first 4-class model on ImageCAS-X, read as pre-registered

<!-- if:template -->
> **Template.** Every `{{…}}` is filled by `experiments/Atlas/r10_read_icx4.py read … --note-template <this file>
> --note-out <new note>`. Only the "what it changes" blocks of the A27/A29 rows that actually fire are kept. Nothing
> in this note is written after the numbers are seen except the numbers themselves (#86). When filled, save it as
> `icx4 - Results.md` and keep this template.
<!-- endif:template -->

**Question.** How good is icx4 (nnU-Net v2 ResEnc, 0.5 mm, 256³, 1000 epochs, ImageCAS-X 560/80 collapsed by D25) on
the decisive metric, and what does Round 9's pre-registered reading (A26, A27, A29, A15) say to do next?

**Setup.**
- The model: `trillium/icx4` on Fir (A25).
- Decisive set: val 80 (A26), scored by `experiments/Atlas/r9_score_icx4.py`. That scorer runs icx4's own in-job scoring code, with the in-job aortas and CT.
- Metric: tF1 @ 1.5 mm at A1c `24441cf8…5254`. Provisional cases and flagged trees are left out (A1a/A1b).
- Open-36 confirms; dev-44 is reported apart.
- No sealed case is read.

**Headline.**

| | Value |
|---|---|
| A26 identity (r9 scorer = in-job, open-36) | **{{a26}}** |
| Decisive macro tF1, val 80 (95 % CI) | **{{macro}}** ({{macro_ci}}) |
| LM / LAD / LCx / RCA decisive tF1 | {{tf1_lm}} / {{tf1_lad}} / {{tf1_lcx}} / {{tf1_rca}} |
| Flagged-tree share, LM / LAD / LCx / RCA | {{flag_lm}} / {{flag_lad}} / {{flag_lcx}} / {{flag_rca}} |
| FP components per case, val (A15 gate ≤ 1) | {{fp_val}} |
| Whole-tree Dice, open 80 (report only, A28) | {{dice_open80}} |
| A27 rows that fire | {{fired}} |
| P2 (A29) | {{p2}} |

## The reading (generated)

{{reading}}

## What it changes

<!-- if:a26_stop -->
**A26 failed.** The val-80 scorer does not reproduce the in-job tF1 on open-36. Its val numbers decide nothing, and
no A27 row is read. First find the difference: the predictions directory, the aortas, the CT paths in
`layout.json`, or the metric copy. Then re-run both scorers on the same inputs and read again. No GPU is spent until
the two agree (A9: one metric).
<!-- endif:a26_stop -->
<!-- if:stop -->
**A27: Stop.** Something is wrong with the job, the collapse, the resume or the scorer, not the recipe.
- Check 5 val cases end to end before any more GPU is spent: CT → prediction → collapse → reference → tF1.
- Then check the training log for a restart ("training from scratch") and `label_census.json`.
- No recipe question is asked until this is resolved.
<!-- endif:stop -->
<!-- if:reopen -->
**A27: the recipe reopens** (0.80 ≤ macro < 0.85). In this order:
1. the flagged and provisional share;
2. the per-class split;
3. a cut census on ImageCAS-X (Atlas R2).

The candidate levers (Atlas v11 §8: Skeleton Recall, a weighted FP term, patch/context) are each two-seed
comparisons (A22). Round 10 chooses among them on this evidence.
<!-- endif:reopen -->
<!-- if:stands -->
**The recipe stands** (macro ≥ 0.85, A26 passed). icx4 is the base model for the pool reads: fine-tunes enter through
A17a/b as reads arrive, and every retrained decision follows A22. Before wave-1 fine-tuning, the `coronary_icx4`
segtrain task config is due (A32).
<!-- endif:stands -->
<!-- if:class -->
**A27: a class is below 0.80.** Review that class's 10 worst val cases (listed above) before any fine-tune: the
calcified and side-branch-heavy LCx cases first. The LCx class is 35 % side branch on ImageCAS-X, and the human LCx
DSC is 84.8 ± 19.8.
<!-- endif:class -->
<!-- if:flagged -->
**A27: flagged trees > 30 % in a class.** The A1b review of those trees comes first, and decisions on that class
wait for it.
<!-- endif:flagged -->
<!-- if:dice -->
**A27: whole-tree Dice on the open 80 < 88.3** (report only). Check preprocessing, the collapse and the window
before the predictions are used (for example as pool seeds or for the A31 domain check). This is indicative, not
paired: ImageCAS-X's Table 2 includes our sealed 80.
<!-- endif:dice -->
<!-- if:fp_ok -->
**A27/A15: FP per case ≤ 1.** A15 is met on val, and A24's FP-loss line is closed. The FP gate stays an acceptance
criterion on the final model (A15).
<!-- endif:fp_ok -->
<!-- if:fp_high -->
**A27/A15: FP per case > 1.** atlas2's census runs on icx4's val (`r10_read_icx4.py census`). The Round 8 §6.1 human
question on the gate's achievability (L7) is asked again with this census.
<!-- endif:fp_high -->
<!-- if:fp_confident -->
**Confident components dominate** (atlas2's majority rule: `confident_other` > 50 % by count). A properly weighted FP
term (5–20 % of the loss) becomes a two-seed candidate (A22), not a single run.
<!-- endif:fp_confident -->
<!-- if:p2_adopted -->
**A29: P2 adopted.** ImageCAS-X start points are the ostium of record for **ImageCAS-X references only**, together
with Delta's flag rule (passed on val 80 and on open-36). Team reads keep A1 as written (TotalSegmentator aorta).
<!-- endif:p2_adopted -->
<!-- if:p2_withdrawn -->
**A29: P2 withdrawn.** TotalSegmentator aortas stay required for every decisive score (A1 as written).
<!-- endif:p2_withdrawn -->
<!-- if:p2_reported -->
**A29: P2 reported, not adopted.** It passed on val 80 but not on open-36, where a rule is validated (A26). A1 as
written stays the rule of record.
<!-- endif:p2_reported -->
<!-- if:p2_missing -->
**A29 not read yet.** Run Delta's `score_tf1.py --aorta-dir $SCRATCH/icx4/aorta` and read again with `--delta`.
<!-- endif:p2_missing -->

## Inputs

```json
{{inputs}}
```
