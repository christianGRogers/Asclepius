---
tags: [plans/experiment, trillium, gpu, pending, A7, naming]
author: Bridge
round: 3
status: PENDING — prepared and CPU dry-run tested (READY), awaiting the project lead's Trillium run
updated: 2026-10-08
---

# PENDING (Trillium): does rule naming or grammar decoding beat a direct 4-class model's own names?

## Question

A7 binds the master to a comparison on R1's validation fold:

- **D**: the direct model's names;
- **R**: Bridge's rule renaming of D's foreground;
- **H**: grammar decoding of D's softmax.

Every CPU-side result so far bounds naming with an oracle (ruling R2, Bridge scorecard). **No direct
4-class model exists yet.** This experiment trains one with the master's recipe on one H100 inside 24 h
and runs exactly that comparison, before R1.

## Method (as prepared; code in `trillium/bridge/`)

- **Labels.** The master's territory proxy (Atlas v3 §2.1) on the **original ImageCAS mask** (D0):
  - each mask voxel takes the ImageCAS-X class of the nearest ImageCAS-X voxel within 2 mm, with
    geodesic inheritance for the rest;
  - D1 territory; ramus → LCx (D1b).
  - Train = ImageCAS-X train list (560). Val = ImageCAS-X val list (80, the master's own val split).
- **Model.** nnU-Net 2.8.1 `3d_fullres`, `ResEncUNetPlanner`, 60 GB target, 0.5 mm iso, fixed window
  [−300, 1300] HU, no mirroring. Same as Atlas v3 §2.2–2.4 except:
  - **no A4 `ignore`**;
  - **training is deadline-bounded at ~19.5 h** (the master forecasts ~45 h for 1000 epochs, so expect
    roughly 400 epochs). The run reports its epoch count.
  - If the 60 GB plan runs out of memory, the job falls back to a 40 GB plan and says so.
- **Prediction.** nnU-Net's own validation of the 80 val cases with softmax (`--npz`), tile step 0.5,
  no TTA.
- **Arms**, all on the same predicted lumen (D's argmax, components < 100 voxels dropped):

  | Arm | Naming |
  |---|---|
  | D | the model's own names |
  | R | frozen rule namer (`label.py` md5 06f53291…, ramus → LCx, 4 mm naming bridges) |
  | H | unary = log of D's mean softmax over the voxels each skeleton vertex owns; exact tree MAP in which the LM is a connected region containing the root (0.5-nat LM prior), every subtree below it is wholly LAD or wholly LCx, and the tree with the highest P(RCA) is the RCA; root chosen jointly among the 8 best learned-ostium candidates |
  | O | reference names on D's foreground: the naming headroom |
- **Metric.** tF1 @ 1.5 mm (D3) against the proxy reference, plus:
  - per-class tF1, tF1 @ 0 mm, case-level swaps, centreline naming accuracy, macro Dice, FP components.
  - Ostium: reference-derived (left = LM endpoint farthest from LAD/LCx; right = thickest RCA endpoint).
    It is the same for every arm, so paired differences are valid. **It is not the A1 aorta-contact
    ostium, so under A9 the numbers are provisional.**
- **Decision rule, pre-registered here = A7.** R (H) wins if the paired bootstrap 95 % CI of
  tF1(R) − tF1(D) (resp. H − D) is above 0 **and** its swap rate is no higher than D's.
- **Budget.** One job, 1 × H100, ≤ 24 h, `--account=def-aso22`. Prep and preprocessing run on the job's
  24 cores (~1 h).
- **CPU dry run here.** The whole `job.sh` runs end to end on a 13-case fake `cases/` tree with nnU-Net's
  default planner at 2 mm on the CPU (result in §Dry run). `shellcheck` is clean. Layout detection was
  tested on both layouts.

## What each result would change

| Result | Reading | Decision it moves |
|---|---|---|
| R − D CI > 0, swaps no higher | rules out-name a real direct model on its own lumen | A7 ships R after R1 unless R1 overturns it; Bridge v3's naming claim becomes measured, not bounded |
| H − D CI > 0, R not | the network's evidence is good but inconsistent; grammar fixes it | ship H; R stays QA |
| O − D small (< 0.01) and R − D, H − D ≈ 0 | the direct model already names at the ceiling | R and H stay QA only; Bridge's naming thesis is closed for the master recipe |
| R − D CI < 0 | rules name worse than the network | R dropped from A7; the namer remains A4 QA only |
| D has swaps along long vessels | Round-1 concern revived despite the 128 mm patch (ruling C1) | H/R priority up; swap rate becomes a gate |

## Result

PENDING (Trillium). `trillium/bridge/results/SUMMARY.md` will be returned by the lead.

## Dry run (CPU, here): plumbing only, no result is read from it

| Test | What ran | Outcome |
|---|---|---|
| Girder layout, full `./bridge` (`BRIDGE_DRYRUN=1`) | 13-case fake `cases/<case>/{ct,coronary_arteries}.nii.gz` tree; layout detection; ImageCAS-X fetch (skips present files); proxy for 10 train + 3 val; fingerprint + fixed window; nnU-Net default planner at 2 mm; preprocessing; `nnUNetTrainer_bridge` 1 epoch × 2 iterations on CPU; nnU-Net validation with `--npz` | all steps ran. Validation exported 2 of 3 cases; the third export worker was killed by memory pressure on this shared 15 GB box (other agents' runs), and nnU-Net's pool then waits forever. Not expected on a 188 GB Trillium quarter-node, but noted as a risk |
| ImageCAS release layout | 8 cases as `<n>.img.nii.gz` + `<n>.label.nii.gz`, `BRIDGE_STOP_AFTER=prep` | layout detected, ids mapped c(n−1), proxy built, split 6/2 |
| No `cases/` | `./bridge` in a tree without one | fails loudly, listing every directory it checked |
| Scoring | `evaluate_val.py` on a fake nnU-Net validation folder: proxy with a direct-model-like naming error (first ~10 % of LCx named LAD at the carina, three LAD islands inside LCx); softmax saved as nnU-Net/NibabelIO does | all four arms, A7 verdict, SUMMARY.md, results.json written. **Two fixes made from this test:** (1) H's unary is log of mean probability, plus a 0.5-nat LM prior (it had let the LM swallow an ambiguous LCx stretch); (2) a degenerate prediction (> 10× the reference volume) skips R, H and O instead of stalling skeletonisation. R and H corrected the injected LAD/LCx error (LAD/LCx tF1 0.996–0.999 vs D 0.94–0.98). Both lost on the LM, whose few skeleton voxels make LM tF1 fragile |
| `./bridge status`, `./bridge collect` | dry mode | ran; collect copies < 20 MB files only |
| `shellcheck bridge job.sh` | | clean |

Not testable here: `sbatch`/`squeue`, Trillium modules, the Alliance wheelhouse, the CUDA run and the 60 GB
plan's real memory. The launcher fails loudly on each. If the 60 GB plan runs out of memory before the
first checkpoint, the job falls back to a 40 GB plan.

## Limits

- **Reference = proxy.** The model is trained and judged on the same convention. Team reads will not exist
  before R1.
- **Shortened training.** A direct model trained to 1000 epochs may name better. The run states its epoch
  count, and the comparison should be repeated on R1 (A7).
- **80 val cases.** The CI is reported, not assumed.
