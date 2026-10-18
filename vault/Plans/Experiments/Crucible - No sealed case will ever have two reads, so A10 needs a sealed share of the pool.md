---
tags: [plans, experiment, evaluation, sealed-test, A10, A14, power, round-9]
author: Crucible
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# No sealed case will ever have two reads, so A10 needs a sealed share of the pool

## Question

The Round 4 sealed test (A14: 80 ImageCAS-X test cases + 20 quality-0 cases, [[Sealed test]]) was built to be scored
"only at milestones, against team reads". A10 (D6) accepts the final model if, per class, its tF1 against the team's
reads is non-inferior to inter-read tF1 within 0.05. After D22, D23 and D25:

1. Can A10 still be computed on the sealed test?
2. If not, where can it be computed, how many cases does it need, and can the set be fixed now, before any read exists?
3. Does the icx4 job (the model Round 9 plans for Fir) respect the seal?

## Method

- **Reads on sealed cases.** Read D22 and D23 against the sealed list (`trillium/sealed_test.json`). Listed the
  ImageCAS-X release (Zenodo 10.5281/zenodo.21887809, `ImageCAS-X_dataset.zip`, central directory read by HTTP range
  request with `remotezip`, 2026-10-18): 3210 entries.
- **icx4 scoring.** Read `trillium/icx4/lib/score.py` and `prepare.py` on `dev` (commit `743fe90`).
- **Power.** `experiments/Crucible/r9_pool_power.py` runs the implemented A10 rule
  (`segtrain.reads.acceptance`: per-class paired bootstrap 95 % CI of mean(model − inter-read), pass iff the lower
  bound > −0.05, accepted iff all four classes pass) on simulated per-case contrasts. Contrasts are correlated
  Gaussians (between-class ρ = 0.3, assumed) with Bridge's measured per-class SDs of the A10 contrast (Round 6,
  [[Bridge - At n = 100 the A10 rule rejects a human-level model, and most open-set tests cannot see their effect]]
  §3: 0.14 macro to 0.19 for LCx and RCA; used LM 0.17, LAD 0.15, LCx 0.19, RCA 0.19). Scenarios: true mean
  contrast δ ∈ {−0.05, 0, +0.02}; SD × 1.0 or × 1.3 (pooled sources assumed harder than ImageCAS); 0 % or 20 % of
  cases dropped by the A1b flagged-ostium rule. 400 replicates × 1000 bootstrap draws per cell. Results:
  `experiments/Crucible/r9_pool_power.json`.
- **A sealed pool draw.** `experiments/Crucible/r9_seal_pool.py` applies a hash rule to
  `configs/segqueue14/pool-2026-10.txt` (D23's 675 volumes), by patient and stratified by source. Output:
  `experiments/Crucible/r9_sealed_pool_150.json`. No CT or read was opened; the rule uses names only.

## Result 1: the sealed test has no second read and never will

| Sealed group | Team reads? | Any second expert read? |
|---|---|---|
| 80 ImageCAS-X test | **No.** D22: "the 800 ImageCAS cases that ImageCAS-X already labels are not annotated". D23: SegQueue14 serves "no ImageCAS case, labelled or not" | **Not released.** ImageCAS-X double-read all 160 test cases (preprint arXiv:2608.30404, Table 1), but the zip holds exactly one `segmentations/<id>.coronary.nii.gz` per case (800 files; 1600 centreline files, left + right per case; 800 surfaces). The second analyst's masks are not public |
| 20 quality-0 | **No.** They are among the 200 unlabelled ImageCAS cases, which D23 removes from the queue | No (ImageCAS-X excluded them as non-diagnostic) |

So **A10 as written cannot be run on any sealed case.** The only reference on the 80 is ImageCAS-X's single read; the
20 quality-0 cases have none at all. The [[Sealed test]] page's "scored only at milestones, against team reads" is
now impossible.

## Result 2: icx4 as built scores the 80 sealed cases

`trillium/icx4/lib/score.py` scores `splits['test']`, which `prepare.py` fills with **all 160** ImageCAS-X test cases,
and writes per-case Dice for each (`per_case_test.json`) and a summary into `results/`. The 80 sealed cases are among
them. Nothing refuses them (atlas2/atlas3's `score_run.py` does: "REFUSING: sealed case in the case list").

Running icx4 unchanged would therefore spend the one decisive look at the sealed 80 (A19) on a Dice table, before any
milestone, and put their per-case scores in a file every advocate reads. It also scores Dice, not tF1: by A1/A9 a
Dice table decides nothing. Echo's audit found the same seal problem independently (#49) and opened **#55** (never
score the sealed 80); Bridge's **#54** adds the decisive A1c tF1 on the open test cases. Both are fixes to land before
the first Fir job, not reasons to delay it.

## Result 3: how many sealed pool patients A10 needs

Probability that a model passes A10 (all four classes), by number of independent sealed cases n:

| Spread | A1b drop | δ (model − inter-read) | n = 50 | 75 | 100 | **150** | 200 |
|---|---|---|---|---|---|---|---|
| ×1.0 | 0 % | −0.05 (at the margin) | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| ×1.0 | 0 % | **0 (human-level)** | 0.18 | 0.32 | 0.51 | **0.79** | 0.94 |
| ×1.0 | 0 % | +0.02 | 0.49 | 0.76 | 0.91 | **0.98** | 1.00 |
| ×1.0 | 20 % | 0 | 0.11 | 0.23 | 0.38 | **0.65** | 0.83 |
| ×1.3 | 0 % | 0 | 0.05 | 0.15 | 0.19 | **0.44** | 0.59 |
| ×1.3 | 0 % | +0.02 | 0.21 | 0.43 | 0.60 | **0.84** | 0.95 |
| ×1.3 | 20 % | 0 | 0.03 | 0.10 | 0.12 | **0.31** | 0.47 |

- **Type-I side.** A model exactly 0.05 worse than a second reader passes a single class with probability 0.02–0.05
  and all four with probability 0.00 at every n. The rule is safe; its problem is power.
- **At n = 100** (the size of the old sealed test) a human-level model passes about half the time on ImageCAS-like
  spread and a fifth of the time if the pooled sources are 30 % noisier.
- **At n = 150** it passes 79 % (×1.0) or 44 % (×1.3); a model 0.02 better than a second reader passes 84–98 %.
- The worst class at n = 150, δ = 0, ×1.0 is RCA (0.88 alone) then LCx (0.92).

The ×1.3 row is an assumption, not a measurement: no pool reads exist yet. It is the case to plan against, because
the pool mixes 23 sources, congenital hearts (ImageCHD, 83 volumes) and non-gated or low-dose scans.

## Result 4: a sealed pool set, fixed now by a hash rule

Rule (in the script's docstring, pre-registered here):

- candidates: the "QC annotatable" and "QC limited" sections of the pool list (601 volumes). The 74 "header spacing
  suspect" volumes are left out: they are served last and may be re-gridded;
- one **patient group** per `<Source>__<Case>` (three-field names, D22) or per case with its phase/timepoint/frame
  suffix removed (`_diast`, `_syst`, `_tpN`, `_fNN`, `_phN`). This joins, for example, the 20 frames of
  `Mendeley-SDN-4643nn2z44__s010_f00…f19`, the diastole/systole pairs of `Mendeley-SDN-cy54ttk3fj`, and RIDER's
  phases of one patient. 601 volumes form **465 patient groups**;
- within each source, groups are ranked by `sha256('asclepius-sealed-round9-pool:' + group)` and the first
  round(150/465 × n_groups) are sealed. A source with one group is never sealed;
- every volume of a sealed patient leaves training. A10 scores **one volume per sealed patient** (the first in serve
  order), so n counts hearts, not phases.

Draw at 150 patients: **150 scored volumes, 198 sealed volumes in all**, from 20 of the 23 candidate sources. For
example: Taiwan-AICUP 32 of 100 patients, ImageCHD 27 of 83, Mendeley-SDN-cy54ttk3fj 13 of 40 (26 volumes), RIDER 5
of 14 (28 volumes), VMR-Coronary 10 of 30. That leaves 403 candidate volumes (315 patients) plus the 74 suspect-spacing
volumes for training. The full list is in `r9_sealed_pool_150.json`; at 100 patients the same rule seals 121
volumes.

## What it changes

1. **A10 moves to the pool.** D6 says "tF1 against the team's reads". The only team reads will be on pool volumes
   (D23: two reads each), so the sealed acceptance set has to be pool volumes. The 150-patient draw above, fixed
   before any pool read exists, is proposed as **A14-pool** in [[Crucible v10]]. It costs annotators nothing, since
   these volumes are read anyway under D23. Its cost is about a third of the pool's patients withheld from fine-tuning.
2. **The 80 sealed ImageCAS-X cases stay sealed**, as a single-read, in-domain milestone benchmark: decisive tF1
   against collapsed ImageCAS-X, scored once at the final model. They can no longer be an acceptance test, because
   there is no inter-read to be non-inferior to.
3. **icx4 must stop scoring the sealed 80** and must score tF1 (A1c) on the non-sealed cases instead of Dice on
   160. Both changes are already `role:swe` issues (#55, #54). This note adds one requirement to them: the val 80
   should be scored with tF1 too (run 1's aortas for those 80 exist on Trillium, `$SCRATCH/atlas2`), because the open
   36 alone detect only about 0.034 macro between two trained networks (Bridge, Round 6 §2).
4. **Lead question, not plan fact.** If the lead wants A10 in-domain as well, about 30 sealed ImageCAS-X cases would
   have to be added to SegQueue14 for two team reads each. That changes D23 (no ImageCAS case in the queue), so it is
   asked, not assumed.

## Limits

- Simulated contrasts, with Bridge's simulated-read SDs. No real inter-read data exist, and the between-class ρ is
  assumed.
- The patient grouping is a name heuristic. A source that hides one patient under two unrelated case names would leak
  across the seal. QC knows more about each source than the names show, and could correct the grouping before reads
  begin.
- LM is optional (D13), so LM's n on the pool will be below 150. The Round 3 ruling already lets LM be reported
  rather than gated if its CI is too wide.
