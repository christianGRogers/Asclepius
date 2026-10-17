---
tags: [plans/experiment, trillium, pending, a1, fp-gate, window, a16]
author: Atlas
round: 6
updated: 2026-10-10
status: pending
---

# Atlas - Pending Trillium run 2, A1 re-score, FP census and the window ablation

`trillium/atlas2/` (`./atlas2`) is the run approved by [[Round 5]] as **A16**. It is one 1×H100 job of at most
23:50 that follows the contract in `trillium/README.md` (account `def-aso22`, no arguments, never writes to Girder,
never needs a token).

It reuses run 1 ([[Atlas - Trillium R0 and short R1 results]]) through run 1's A13 manifest on `$SCRATCH/atlas`:
the checkpoint, the 80 val segmentations and softmax, the references, the plans and the fingerprint.

No sealed case is touched:
- the val cases are the ImageCAS-X val split;
- the 36 test cases are A14's `open_icx_test`;
- every list is checked against both sealed lists before use.

## What it answers

| Question | How | Decides |
|---|---|---|
| What is run 1's tF1 under the ostium of record? | A1 re-score with TotalSegmentator aortas and the frozen `segtrain.tf1` | Replaces the 0.846–0.895 bounds; a value "well below 0.87" reopens the recipe (Round 5 §5) |
| What are the FP components? | Census, one row per raw FP component, with categories fixed below | Routes the FP lever (A15) |
| Does nnU-Net's default window beat the fixed one? | Phase B: run 1's recipe with the default window, 412 epochs, paired | The window for R1 (A16) |
| Out-of-sample data for Bridge | Run 1's predictions + softmax + aortas + references for the 36 clean open test cases | Bridge's gated-renaming test (Round 5 §5) |

## Procedure

**Login node.** All steps are idempotent.

1. **Metric check.** `lib/segtrain_tf1.py` (a verbatim copy of `src/segtrain/tf1.py`) must have sha256
   `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253`, the hash frozen in [[Master plan]] (A1c).
   Otherwise the run refuses to start. The job checks the hash again.
2. **Venv.** Torch from the wheelhouse, plus `nnunetv2==2.8.1` and `TotalSegmentator==2.18.0` (the versions tested
   here). The TotalSegmentator `total_fast` weights are downloaded into `$SCRATCH/atlas2/totalseg`, with usage
   statistics off.
3. **Run 1 check.** Checkpoint, model `dataset.json`/`plans.json`, plans, fingerprint, splits, 80 segmentations,
   softmax and references. Any gap is a loud failure.
4. **ImageCAS-X.** The labels are reused from run 1. The centrelines for the 116 cases (start points) are fetched
   for the validation column.

**Job.**

| Stage | Resource | Time | Content |
|---|---|---|---|
| A0 | CPU, background | ~40 min | Phase B dataset 714: run 1's images, labels, plans and split, with `foreground_intensity_properties_per_channel` restored from run 1's fingerprint ([−169, 719] HU), then `nnUNetv2_preprocess` |
| A1 | GPU | ~30 min | TotalSegmentator aortas for 80 val + 36 open cases (fast model, roi aorta, on the case grid) |
| A2 | CPU, 4 workers, overlapping training | ~2 h | Run 1 val: A1 re-score, FP gate, census, threshold sweep, ostium validation |
| A3 | GPU | ~30 min | Open 36: run 1's checkpoint, tile step 0.5, `--disable_tta`, `--save_probabilities`; proxy references; `manifest_open36.json` |
| B | GPU | 412 × 175 s ≈ 20.0 h | `nnUNetTrainerAtlas` on dataset 714, 412 epochs (run 1's length), `--npz`, deadline guard keeps the final validation |
| B score | CPU, 18 workers | ~30 min | Same code as A2 (sweep only if more than 80 min remain) |
| Report | CPU | 1 min | `SUMMARY.md`, `results.json`, per-case and census tables (< 1 MB) |

Total ≈ 22.3 h of the 23:50. If the node is slower than run 1's, the trainer stops at the deadline. The final
validation still runs, and the report flags the pairing as weakened.

## Pre-registered rules (fixed before any result)

**tF1 (A1, A1a, A1b).**
- Ostium of record: the reference centreline voxel nearest the aorta, per tree component and per side.
- A case without an aorta mask is provisional and decides nothing.
- A class is *flagged* when the tree (component and side) holding it carries a flagged ostium, i.e. the rules
  disagree by > 5 mm or the tree does not touch the aorta.
- The **decisive** case score is the macro tF1 @1.5 over the unflagged classes. Flagged trees are reported apart.
- Validation columns only: distance of each ostium to the ImageCAS-X start point of its side; the `thick` and
  `pool_thick` candidates.

**FP census categories (A15).** Raw prediction; components ≥ 100 voxels, 26-connected, touching no reference voxel.
- `icx_vessel`: ≥ 50 % of the component's voxels lie within 1 mm of an ImageCAS-X vessel voxel. This is real vessel
  the ImageCAS mask omits.
- `low_confidence`: otherwise, if the 90th percentile of its vessel probability (1 − p_background) is < 0.90.
- `confident_other`: everything else.

**Routing (A15).** "Mostly" means more than 50 % of FP components by count. The share by volume is reported
alongside.
- Mostly `low_confidence` → one global vessel-probability threshold, chosen on val and frozen. It is adopted only if
  tF1 is not worse (CI) and FP falls. The sweep over t ∈ {0.5, 0.6, 0.7, 0.8, 0.9, 0.95} is reported now; the
  choice is made later.
- Mostly `icx_vessel` → the clinical lead's question (Round 5 §6).
- Mostly `confident_other` → the recipe reopens: FP-aware loss or context.
- No majority → all three are reported, and nothing is adopted on the census alone.

**Window (A16).**
- The paired B − run 1 decisive tF1 decides when its bootstrap 95 % CI excludes 0.
- On a tie, the window with fewer FP components per case wins. On equal FP, the fixed window stays.
- R1 then runs at full length with the winner.

**Expectations, stated before the run (Atlas).** These are expectations only; the rules above decide.
- The A1 re-score lands at 0.88–0.90 macro, with the LCx lowest.
- B ties on tF1.
- The census has no `low_confidence` majority: the model is confident almost everywhere.
- If FPs are mostly `icx_vessel`, the gate question goes to the humans, as A15 foresees.

## Tested on CPU here

- **Dry run.** `ATLAS_DRYRUN=1 ./atlas2` was run in both case layouts (Girder export and ImageCAS release, 116
  symlinked cases each) against a fake run-1 tree. It found the cases, run 1, the ImageCAS-X labels and the
  centrelines, and printed the job script: `--account=def-aso22`, 1 GPU, 23:50, no partition, no memory request.
- **Refusals.**
  - A tampered `segtrain_tf1.py` (hash `ca07c1…`) stops the run.
  - A missing run 1 stops it with a pointer to `./atlas`.
  - Sealed cases are refused by `aorta.py`, `open36.py`, `score_run.py` and `check_run1.py`.
- **Job body.** `ATLAS2_LOCAL_TEST=1` ran `lib/job_body.sh` end to end on 2 real val cases (c0038, c0133), with
  synthetic predictions and softmax, stub aortas and one open case:
  - the hash check passed;
  - the aortas were written;
  - the open-36 proxy label was written, and prediction failed cleanly on the fake checkpoint (the stage is retried
    on resubmission);
  - Phase B plans with the default window were built from the fingerprint;
  - run 1 was scored, and the report was written.
- **Scoring on one real case** (c0038, Delta's TotalSegmentator aorta):
  - the A1 left ostium lies 2.8 mm from the ImageCAS-X start point;
  - a planted 3 mm RCA cut gives RCA tF1 0.53, and the RCA tree is flagged (rules 5.9 mm apart), so it is left out
    of the decisive score;
  - two planted blobs are classed `low_confidence` (p 0.6) and `confident_other` (p 1.0);
  - the threshold sweep removes the weak blob from t = 0.7.
  - Cost: 6 min and 3.9 GB on one CPU thread.
- **Phase B preprocessing.** `prepare_b.py` was run with real `nnUNetv2_preprocess` on two cropped real cases.
  - It caught one bug, now fixed: the preprocessor needs `dataset.json` in the preprocessed folder.
  - The preprocessed intensities equal (clip(HU, −169, 719) − mean) / sd with the restored fingerprint values
    (maximum 2.6265 = (659 − 262.4) / 151), so the default window is really applied.
- **Start-point parser.** `lib/vtkcl.py` (binary and ASCII legacy VTK, no vtk package) matches
  `vtk.vtkPolyDataReader` on all 876 local centreline files.
- **Lint.** `shellcheck` is clean on `atlas2` and `lib/job_body.sh`, and pyflakes is clean.

## Limits

- **TotalSegmentator on the node is untested here.** The GPU was not available, and the CPU run exceeds this
  sandbox's 3 GB per-process limit. Delta ran the same model and roi on CPU for 84 cases. If it fails on the node,
  the affected cases are provisional (A1a), and the aortas can be recomputed on CPU later.
- **The reference is the projected proxy**, as in run 1. A4 QA was not applied, for the same reason as run 1.
- **Phase B is one seed.** A tie is the likely outcome. The tie rule (FP) then decides a choice that matters
  little for tF1.
- **The census categories are geometric and probabilistic, not clinical.** `confident_other` can still contain
  real vessel that neither reference traced. The census routes the lever; it does not label vessels.
