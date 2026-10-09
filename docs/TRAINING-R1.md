# R1 on Trillium: the four-class coronary model

The runbook for the model the plan tournament settled on: one four-class nnU-Net
(`712_CoronaryBranches`: left main, LAD, LCx, RCA) at 0.5 mm, trained first on proxy
labels and then on the team's double reads. The reasoning is in the vault:
[`vault/Plans/Master plan.md`](../vault/Plans/Master%20plan.md), the decisions the
project lead made are in [`vault/Plans/Human decisions.md`](../vault/Plans/Human%20decisions.md),
and the sealed test is [`vault/Plans/Sealed test.md`](../vault/Plans/Sealed%20test.md).
This document is the sequence of commands and does not repeat any of that.

It replaces [`TRAINING-PHASE1.md`](TRAINING-PHASE1.md), which describes the retired
binary-lumen plan.

> **Status.** Every command below exists and the library code behind it is tested
> (`pytest`), but this sequence has not yet been run end to end on Trillium. The
> four tournament experiments in `trillium/` are the first real runs; read their
> results before trusting the numbers in step 8.

---

## 0. What is fixed before you start

| | Value | Where it is enforced |
|---|---|---|
| Target, seed and reference | The original ImageCAS mask, split into four classes | `segtrain proxy`, the convention monitor in `segtrain reads-report` |
| Side branches | Territory rule; ramus → LCx | `segtrain.namer` (`--ramus LCx`) |
| Spacing, patch | 0.5 mm isotropic, 256³, batch 2, ResEnc at a 60 GB budget | `segtrain plan` |
| CT window | Fixed [−300, 1300] HU | the coronary trainer refuses any other |
| Mirroring | Off | the coronary trainer |
| Sealed test | 80 ImageCAS-X test + 20 quality-0 cases, never trained on | `segtrain proxy`, `convert`, `splits` all refuse them |
| Deciding metric | Tree-F1 at 1.5 mm, gated on false-positive components of the raw prediction | `segtrain tf1` |

## 1. Before anything else

```sh
segtrain scinet check        # paths under $SCRATCH, account, venv in $HOME
```

The SLURM account is `def-aso22`. Build the venv once, on a login node:
`segtrain scinet setup`.

## 2. Get the data onto `$SCRATCH`

The one-command route used by the tournament experiments downloads the cases from
Girder in the layout every tool here accepts:

```sh
python3 trillium/fetch_cases.py $SCRATCH/asclepius/cases     # ~91 GB, resumable
```

Then the ImageCAS-X labels (~14 MB, login node only — compute nodes have no internet):

```sh
python3 trillium/atlas/lib/fetch_icx.py $SCRATCH/asclepius/icx
```

## 3. Proxy labels (until team reads exist)

```sh
segtrain proxy --cases $SCRATCH/asclepius/cases --icx $SCRATCH/asclepius/icx \
               --root $SCRATCH/asclepius/proxy --workers 8
```

ImageCAS-X's per-branch names are projected onto the ImageCAS mask under the
territory rule, then checked against the rule namer (amendment A4): voxels the two
name differently near the carina become `ignore`; cases with a wholesale disagreement
are dropped and listed in `proxy_report.json` for human review (about 12 % of cases).
Sealed cases are refused.

## 4. Index and convert

```sh
segtrain index --root $SCRATCH/asclepius/proxy --layout nested
segtrain convert --task 712
```

Expect a line saying how many sealed cases were excluded, and a `dataset.json`
with `"ignore": 5`.

## 5. Plan, split, preprocess

```sh
segtrain plan --task 712
segtrain splits --task 712 --explicit-icx $SCRATCH/asclepius/icx
segtrain preprocess --task 712
```

Check the plan printout: 0.5 mm, 256³, batch 2, window [−300, 1300]. There is no
patch-fraction gate any more, and `3d_lowres` is never trained. Preprocessing at
0.5 mm needs about 10 GB of RAM per worker; keep to about 10 workers.

## 6. Benchmark first (R0)

Before the long run, measure peak GPU memory, seconds per epoch and loader wait:
the `trillium/atlas` experiment does exactly this. Acceptance: ≤ 306 s/epoch and
≤ 75 GB peak. If either fails, apply the levers in `vault/Plans/Candidates/Atlas v4.md`
in order before submitting.

## 7. Train

```sh
segtrain scinet submit --task 712 --fold 0
```

The job chain resumes across 24-hour blocks. Validation softmax is always saved, so
naming and post-processing alternatives can be scored later without retraining.

## 8. Evaluate

```sh
segtrain tf1 <reference.nii.gz> <prediction.nii.gz> --ct <ct.nii.gz>
```

Tree-F1 at 1.5 mm decides; Dice and clDice are reported, not decisive. Read the
false-positive component count on the **raw** prediction, before any bridging or
repair. Pass `--aorta` for the A1 ostium; without it the ostium is provisional and
says so. Sealed cases are scored only at milestones, against team reads.

## 9. When the team's reads arrive

Every case is read twice. Put the reads in `<reads>/<case>/<annotator>.nii.gz` and run:

```sh
segtrain reads-report <reads> --masks $SCRATCH/asclepius/cases --icx $SCRATCH/asclepius/icx --out report/
```

The report checks each wave for reads drawn in the wrong convention (more than 10 %
halts the wave), inter-read tree-F1 per class (the acceptance ceiling), the carina
anchor and per-annotator habits, and lists cases that need a third read. The first
50 double-read cases get this report before team labels replace proxies in training.
Its tree-F1 uses the provisional ostium rules (no per-case aorta masks yet).
