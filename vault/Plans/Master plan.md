---
aliases: [Master plan]
tags: [plans, master, four-class, fir]
status: living
round: 9
updated: 2026-10-18
---

# Master plan

**In force: [[Atlas v11]], as amended by the judge in [[Round 9]] (A25–A32).** Four classes (D25) on ImageCAS-X's lumen (D8), trained on **Fir**. Atlas has held the title since Round 1 ([[Atlas v1]]). In Round 9 all five candidates kept the same model and competed on how it is scored, scheduled and accepted. The amendments below are binding and override the candidate text where they conflict. Full reasoning and scorecards: [[Round 9]].

## In one paragraph

Train **one four-class nnU-Net v2 ResEnc model** (LM 1, LAD 2, LCx 3, RCA 4) with `trillium/icx4` exactly as on `dev`:
- data: **ImageCAS-X as drawn**, collapsed by territory (`trillium/icx4/lib/territory.py`: D25, D1, D1b; "Other" → the nearest LAD/LCx in mm); dataset 715;
- recipe: 0.5 mm isotropic, 256³ patch, batch 2, mirroring off, nnU-Net's default window, DiceCE, **1000 epochs**;
- splits: ImageCAS-X train 560 / val 80 / test 160;
- compute: one H100 on Fir, account `def-aso22`.

The job predicts all 1000 ImageCAS cases and scores **decisive tF1** (A1c hash `24441cf8…5254`) on the open test cases, never on a sealed one (#66). **Decisions are made on val 80** (atlas2 aortas), confirmed on open-36. Team reads come only from the 675 pool volumes (D23), two reads each, starting from TotalSegmentator seeds (D26). They enter later through the A17 fine-tune trainer, with each read a separate sample (A11′). **Acceptance (D6) is measured on the A30 pool seal** (150 pool patients, extendable to 200–250 on wave-1 evidence; [[Human decisions]] D27). No second seed for now (D28); anomalous anatomy is its own stratum (D29); D23's serving order is unchanged (D30).

## The first Fir job (copy-paste; the lead runs it)

**Before you start.**
- Fir access is already enabled: the lead has logged in, `CC_CLUSTER=fir`, `SCRATCH=/scratch/croger`.
- `dev` contains #66: `trillium/icx4/lib/sealed.py` exists.

**1. Data, Trillium → Fir.** Use the Globus web app:
- source `alliancecan#trillium`, path `<root>/cases/` (the folder icx4/icx14 used on Trillium) → destination `alliancecan#fir-globus`, path `/scratch/croger/asclepius/cases/`;
- second transfer: `$SCRATCH/atlas2/aorta/` on Trillium → `/scratch/croger/asclepius/aorta_val80/`. These are 116 TotalSegmentator aortas, for the val 80 + open 36. They are used later on CPU and do not block the job.

Or use rsync from the Fir login node:

```sh
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
rsync -a --info=progress2 <you>@trillium.scinet.utoronto.ca:<root>/cases/ cases/
rsync -a <you>@trillium.scinet.utoronto.ca:'$SCRATCH/atlas2/aorta/' aorta_val80/
```

**2. Code and submit.** On `fir.alliancecan.ca`, inside `tmux`:

```sh
cd $SCRATCH/asclepius
ls cases/*.img.nii.gz | wc -l                 # expect 1000 (each case is <n>.img.nii.gz + <n>.label.nii.gz)
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo || git -C repo pull --ff-only
test -f repo/trillium/icx4/lib/sealed.py && echo "#66 present"      # must print; otherwise stop and tell the PM
mkdir -p experiments && rm -rf experiments/icx4 && cp -r repo/trillium/icx4 experiments/icx4
cd experiments/icx4
ICX4_CLUSTER=fir CHAIN=5 ./icx4               # builds $HOME/icx14-venv and the TotalSegmentator venv once,
                                              # fetches ImageCAS-X labels (Zenodo), checks the seal, submits 5 chained jobs
```

**Check the printout:**
- `[icx4] cluster: fir`;
- the metric hash line (`= frozen hash (A1c)`);
- the sealed filter's counts (open-36 36, dev-44 44);
- five job ids.

Then check the job header:

```sh
grep SBATCH $SCRATCH/icx4/job.sh              # --gpus-per-node=h100:1  --cpus-per-task=12  --mem=280G  --time=23:50:00  --account=def-aso22
squeue -u $USER --name icx4                   # 5 jobs; jobs 2-5 wait on (Dependency)
```

If any header line is wrong, run `scancel $(cat $SCRATCH/icx4/submitted_jobs)` and tell the PM.

You can run `ICX4_DRYRUN=1 ./icx4` first. It may stop at the label fetch if the login node's system Python lacks `remotezip`; that is harmless, and the real run builds the venv first.

**3. After about 3 hours** (job 1 preprocesses for 1–2 h, then trains):

```sh
./icx4 status                                 # s/epoch = the time between epoch lines
```

- **≤ 400 s/epoch:** let the chain run.
- **> 400 s/epoch:** let it run anyway. When the chain has ended without `DONE`, run `ICX4_CLUSTER=fir CHAIN=2 ./icx4` again; it resumes.
- **Never** shorten the 1000 epochs (A25).

**4. When `./icx4 status` says `DONE`** (in about 3–4 days, plus queue wait):

```sh
./icx4 collect                                # → experiments/icx4/results/ (SUMMARY.md, results.json, tf1_per_case.json, logs)
# decisive val-80 score on the login node (CPU, ~1-2 h), and the A26 identity check on open-36 first:
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/Atlas/r9_score_icx4.py --pred $SCRATCH/icx4/predictions --icx $SCRATCH/icx4/icx \
  --aorta $SCRATCH/icx4/aorta --splits $SCRATCH/icx4/splits.json --set open36 --out $SCRATCH/icx4/r9_open36_check.json --np 10
python experiments/Atlas/r9_score_icx4.py --pred $SCRATCH/icx4/predictions --icx $SCRATCH/icx4/icx \
  --aorta $SCRATCH/asclepius/aorta_val80 --splits $SCRATCH/icx4/splits.json --set val --out $SCRATCH/icx4/r9_tf1_val.json --np 10
# keep the model past Fir's 60-day scratch purge (PROJECT if it exists, else HOME; < 2 GB)
DEST=~/projects/def-aso22/$USER/icx4; [ -d ~/projects/def-aso22 ] || DEST=$HOME/icx4-keep; mkdir -p $DEST
cp -r $SCRATCH/icx4/results $DEST/ && cp $SCRATCH/icx4/nnunet_results/Dataset715_ICX4/*/fold_0/checkpoint_final.pth $DEST/
```

**Resources and cost.**
- Per job: 1 × H100 SXM5 80 GB (full, not MIG), 12 cores, 280 GB, 23:50. Account `def-aso22`, charged to `def-aso22_gpu`. Partition `gpubase_bygpu_b3` (24 h).
- Chain: 5 jobs, `afterany`.
- **Expected: 60–75 GPU-hours** over 3–4 jobs:
  - training 53–68 h at the measured 190–245 s/epoch;
  - about 2 h of preprocessing;
  - about 4 h of prediction, aortas and tF1.
- Range 55–85 GPU-h; hard ceiling 118 (5 × 23.6 h). Spare jobs exit within a minute.

**Send back** on #48 (or a new issue):
- the `./icx4 status` s/epoch line after job 1;
- at the end: `results/` (SUMMARY.md, results.json, tf1_per_case.json, logs) and both `r9_*.json` files;
- the `slurm-*.out` of any failed job.

Never send a sealed case's file. The job writes none.

**No Job B.** The lead declined a second concurrent seed (D28); only Job A runs. A22's fallback stands.

## Binding amendments, Round 9 (summary; full wording in [[Round 9]] §1)

- **A25, the job:** icx4 as on `dev`, unchanged, `CHAIN=5`, 1000 epochs always. No 500-epoch fallback and no 24-core request by default. Expected 60–75 GPU-h.
- **A26, decision sets:**
  - val 80 decides recipe questions;
  - open-36 confirms, and is the only set where rules and thresholds are validated;
  - dev-44 is reported apart;
  - the sealed ImageCAS-X 80 get one blind look at the final model against ImageCAS-X (a milestone, not A10);
  - the sealed quality-0 20 are retired from scoring;
  - the val scorer must reproduce the in-job tF1 on open-36 exactly before it decides.
- **A27, reading the first result:**
  - macro < 0.80: stop and debug;
  - 0.80–0.85: the recipe reopens;
  - any class or LCx < 0.80: review that class's worst cases;
  - flagged trees > 30 %: the A1b review first;
  - whole-tree Dice < 88.3: check preprocessing (report);
  - FP ≤ 1 per case: the FP-loss line closes.
- **A28:** Dice decides nothing. Foxtrot's human-floor readings are report-only.
- **A29:** Delta's start-point ostium (P2) is tested on CPU with the existing aortas. It is adopted for ImageCAS-X references only if ostia agree within 2 mm in ≥ 95 % of trees and |Δ macro| ≤ 0.005.
- **A30:** Bridge's pool seal list (`experiments/Bridge/r9/sealed_pool_proposal.json`: 150 primary patients, 216 volumes; ImageCHD report-only) is **frozen as a candidate**. Until the lead decides L1, none of its volumes is trained on, prelabelled or inspected. QC confirms the patient grouping before wave 1.
- **A31, wave 1** (non-sealed pool reads):
  - measure f and k, and re-power the seal (extend it if either is above 1.2);
  - measure seed-vs-read tF1 (seed anchoring);
  - report model-vs-read per source, which decides nothing at n ≈ 30;
  - an optional pre-read per-source domain check (about 3–4 GPU-h).
- **A32, carried over:** A1/A1a/A1b/A1c, A2/A15, A9, A11′, A12, A17a/b, A19, A21, A22, A23 (report only). **Lapsed:** A3, A4, A17c, proxies. **Closed:** A24. The `coronary_icx4` segtrain task config is due before wave-1 fine-tuning.

## Decisions for the lead ([[Round 9]] §5)

- **L1 → D27:** D6 acceptance is measured on the 150-patient pool seal (A30). The lead declined the request to the ImageCAS-X authors; under D31 no such request is ever written in the repository.
- **L2 → D28:** no Job B.
- **L3 → D29:** ALCAPA and ImageCHD are their own stratum, outside the A10 aggregate.
- **L4 → D30:** not adopted; D23's serving order stands.
- **Still open, L5:** acceptance if reads turn out to be seed-anchored.
- **L6:** ASOCA.
- **L7:** the FP gate.

## Next round

The plan is settled for the first job and the recipe. **Round 10 runs after icx4's results are back** ([[Round 9]] §6), to settle:
- the reading of icx4 (and σ_seed);
- the acceptance set;
- the pool fine-tune recipe;
- what seed-anchored team reads measure;
- the FP lever, if needed.

## Human decisions in force

All of [[Human decisions]] binds. For this plan the operative ones are:

| Decision | What it sets |
|---|---|
| D25 (D1, D1b) | Four classes by territory; the ramus → LCx |
| D8, D12 | ImageCAS-X's lumen; free redrawing of the outline |
| D3 | tF1 tolerance 1.5 mm |
| D6 | Acceptance: per class, non-inferior to inter-read tF1 within 0.05 |
| D13 | LAD, LCx and RCA required; LM optional |
| D22, D23, D26 | No ImageCAS case is read; 675 pool volumes, two reads each, from TotalSegmentator seeds |
| D19 | The lead handles access requests |

D0, D2, D4, D7, D9, D10 and D11 are superseded.

---

## Record: the D0-era master plan (Rounds 1–8)

> Kept as the record. It trained on proxy labels projected onto the original ImageCAS mask (D0), which D8 retired. The 14-class restructure that briefly replaced it (D9, `trillium/icx14`) was itself reversed by D25. The amendments still in force are listed in A32 above.

**Was in force (Rounds 1–8): [[Atlas v9]], as amended by the judge in [[Round 8]].** Won round 1
(as [[Atlas v1]]) and held the title in rounds 2–8. All three challengers now keep the master's
model, data, schedule and deciding metric, and compete on additions to it.

The plan text is the candidate file; the amendments below are binding and
override it where they conflict. Full reasoning, scorecards and what would
change the ruling: [[Round 8]] (earlier: [[Round 7]] … [[Round 1]]).

### In one paragraph

One four-class nnU-Net v2 ResEnc model, trained directly at 0.5 mm isotropic
with a 256³ patch (a 128 mm patch holds the whole tree in ~98 % of cases), a
fixed CT window instead of nnU-Net's automatic one, mirroring off. Training
starts now on proxy labels — ImageCAS-X's per-branch names projected onto our
cases — and team labels replace the proxies case by case as they arrive.

### Binding amendments (as of Round 2)

Round 1's A1–A6 as revised in Round 2, plus A7–A9. The full wording is in
[[Round 2]] §1; this is the summary.

- **A1 — ostium:** tree-F1 (tF1 @ 1.5 mm) decides everything. The ostium is
  aorta contact (TotalSegmentator, ≤ 5 mm), cross-checked by Delta's two cheap
  rules; disagreement > 5 mm is flagged for a human.
- **A2 — false positives and bridging:** the FP-component gate is computed on the
  **raw** prediction, before any repair. Delta's bridge audit is binding. 3 mm
  bridging alone stays switchable but is weak (+0.01 tF1; 5 of 12 joins were FP).
  Gap-centred re-inference + support-gated bridging (P1′) is a candidate, unproven.
- **A3 — one convention:** a per-case convention monitor on every labelling wave
  (halt the wave if > 10 % is in the wrong convention), seed tagging, and a
  single-convention sealed test. The lumen convention itself is a human decision.
- **A4 — QA namer:** voxel `ignore` only near the carina where proxy and rule
  namer disagree; cases with wholesale disagreement are excluded until reviewed.
- **A5 — calibre trigger** and **A6 — R0 benchmark first:** unchanged.
- **A7 — rule renaming competes with the model's own names** (ship only if the
  paired tF1 CI excludes 0 and swaps do not rise); save softmax at val/test so
  Bridge's hybrid decoding can be scored later.
- **A8 — the ramus rule is a switch** set from the humans' written rule.
- **A9 — one implementation:** only the ported `src/segtrain` tF1 may decide.

### Round 3 changes (summary; full wording in [[Round 3]] §1)

- **A1:** ostia found per tree component, so cases with no left main are handled.
- **A2:** the support rule is withdrawn. Re-inference (P1′) stays unproven and is
  judged only against tile step 0.5.
- **A3:** the convention monitor now flags reads drawn *thin* (the decided
  convention is the original ImageCAS mask).
- **A4:** no trunk mode; a ramus-only disagreement never excludes a case.
- **A7:** the namer is cited at 88.2 % of 76 held-out cases fully right (swaps 7.9 %)
  under ramus → LCx.
- **A10 (from Crucible):** score by mean tF1 against each read; accept a model if it
  is non-inferior to inter-read tF1 within 0.02.
- **A11 (judge's synthesis, untested):** each read is a training sample; voxels
  where the reads name the vessel differently are `ignore`; extent differences are
  kept; decision-level disagreements go to a third reader.
- **A12:** one report on the first 50 double reads (refits every simulated-read result).
- **A13:** Atlas's Trillium run goes first and saves the val softmax and final
  checkpoint; Bridge's and Delta's questions can then run inference-only on it.
  Delta's decisions may use only the 80 non-sealed test cases.

### Round 4 changes (summary; full wording in [[Round 4]] §1)

- **A14 — the official sealed test:** 80 ImageCAS-X test cases + 20 quality-0
  cases, ranked by `sha256('asclepius-sealed-round4:' + case_id)` after excluding
  every advocate's development cases. Published in [[Sealed test]] before any
  Trillium job runs; supersedes Delta's `icx_test_split.json`.
- **A11's test** runs only if wave 1 shows annotator habits or team bias, judged on
  a carina anchor against ImageCAS-X rather than against the reads.
- **A12** adds Crucible's habit test and carina anchor as diagnostics only, after
  the anchor's noise floor is measured.
- **A1/A2 confirmed** on new evidence (0 silent ostium errors in 130; bridging still
  6/13 false-positive joins on the thick reference).
- Atlas's decision-table row for the short R1 is now numeric (≤ 0.03 / > 0.10).

### Round 5 changes (first GPU results; full wording in [[Round 5]] §1)

Measured on Trillium: R0 passes (175 s/epoch, 55.6 GiB; 1000 epochs ≈ 48.6 h). A
412-epoch R1 on the proxy scores macro tF1 0.846 under the provisional ostium; the
judge accepts only the bounds 0.846–0.895 until the A1 re-score. The FP gate fails
(1.49/case).

- **A1 — ostium of record:** the reference centreline voxel nearest the
  TotalSegmentator aorta, per tree component and side (`segtrain.tf1`). A tF1 without
  an aorta mask decides nothing (A1a); flagged trees are reported separately (A1b).
  **Metric frozen (A1c):** `src/segtrain/tf1.py` sha256 `3c737cbcc0ba24d38f923a52a28d479b34b579d6943f4c55a8cae48f66ad9253`, last changed in commit `e2d9677`.
- **A2:** bridging (P1) removed; P1′ survives only if Delta's stricter pre-registered
  table passes (≤ ~0.004 to gain).
- **A4:** absent-LM cases are never auto-excluded.
- **A7:** rule renaming (R) and grammar decoding (H) retired; the namer stays QA only.
- **A11′:** each read is a separate training sample with no name-conflict `ignore`;
  the third-read trigger stays.
- **A15:** the FP gate (≤ 1/case, raw) stays as an acceptance criterion for the final
  model; no model has met it. The FP census chooses the lever.
- **A16:** Atlas run 2 — Phase A (FP census + re-score with the A1 rule, no training)
  and Phase B (window ablation, 412 epochs, paired against run 1). Full-length R1 waits
  for run 2's winning window.

### Round 6 changes (CPU round while Atlas run 2 is on Trillium; full wording in [[Round 6]] §1)

- **Closed:** P1′, P1 and P2 failed their own pre-registered tests and leave the recipe.
- **A17 — fine-tuning as team reads arrive:** a dedicated fine-tune trainer comes first
  (stock nnU-Net re-initialises the output heads and has no warm-up); LR 1e-2 with a
  1e-3 fallback arm, and Atlas's citation corrected (the source prefers 1e-3); if the
  proxy fails the wave-1 admission test, the proxy-drop test moves to wave 3. The final
  model never trains on proxies.
- **A18 — A10 suspended** until the clinical lead sets the acceptance margin (see below).
- **A19 — evaluation discipline:** one decisive look at the sealed test; every decision
  table states its minimum detectable effect; a stacked-recipe control replaces E6.
- **A20 — heart+aorta ROI filter (Foxtrot F3):** allowed only after a check on all 1000
  masks and an atlas2 census showing ≥ 25 % of FP components lie beyond 25 mm.
- **A21 — implementation (from Echo's audit):** 13 defects found, all fixed with tests
  (one critical: a sealed-case leak via SegQueue case names). Binding: a dry run of one
  real approved SegQueue export through index → convert → reads-report passes before
  wave 1; a batch aorta producer (TotalSegmentator) lives in `src/segtrain` before any
  decisive tF1 is computed outside a Trillium job (A1a); Echo's remaining suspicions go to
  their owners.

### Round 7 changes (full wording in [[Round 7]])

- **A1c change approved — report-only:** `segtrain.tf1` reports any reference class with
  no centreline voxels (7 of 143 references: short wide LM ×6, LCx ×1) instead of skipping
  it silently. No score changes, so atlas2's results under the old hash stay
  decision-grade. **New frozen hash (A1c):** `src/segtrain/tf1.py` sha256 `9bb77e24c5b8959d37752e260c78e4e589101687a7fe45f130b188670af90608`; field `TreeF1.classes_without_centreline`. atlas2 keeps the previous pin (`3c737cbc…`, copy at `experiments/Delta/tf1_3c737cbc.py`); scores are identical between the two. Scoring such
  a class as missed is **rejected** (a perfect prediction has no centreline there
  either). A minimum-centreline fallback is approved in principle, to be validated before
  wave 1 and before any A10 or sealed scoring.
- A17a fine-tune trainer and A17b citation done; A20(i) ROI check passes on 92 cases, the
  remaining 908 to run with the aorta producer after atlas2; A21 aorta producer built and
  the SegQueue export dry run passed on test submissions — it must be repeated on the
  first real four-class double-read export before wave 1.

### Round 8 changes (atlas2 and Crucible seed 2; full wording in [[Round 8]])

Measured: run 1 re-scored under the A1 ostium of record — decisive macro tF1 **0.896**
(LM 0.966 / LAD 0.901 / LCx 0.846 / RCA 0.883), 44 of 316 trees flagged. Recall of
expert-traced centreline 93–97 %. 79 % of FP components are confident and are mostly
cardiac veins beside the tree; no threshold or ROI rule removes them.

- **Window:** nnU-Net's default window, by the pre-registered tie-break; recorded as "not
  shown better" (the FP difference is within noise). Atlas's two R1 guards (no worse than
  run 1; an LCx check) bind.
- **A24 — run 3 before R1:** an FP-aware loss pilot, two warm fine-tunes from B with the
  same seed, data stream and epochs; adopt only if FP/case falls (CI excludes 0) and tF1 is
  non-inferior at 0.01 with the seed term included; per-class recall reported separately
  for expert-traced and low-contrast mask vessel. R1 (48.6 h) follows, plain unless the
  term is adopted.
- **A22 — seed rule:** σ_seed ≈ 0.013; any effect under 0.02 needs two seeds; paired arms
  get equal epochs.
- **A1c:** the fallback centreline becomes the decisive default. **Pinned hash:**
  `src/segtrain/tf1.py` sha256 `24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254` (Round 7 tests 5–7 pass). Paired on run 1's
  116 predictions: val decisive macro unchanged (0.8958); two real LM errors on the open
  set are now counted. Run 3 is scored at this hash.
- **A23:** a report-only extent diagnostic (tF1 on contrast-supported reference) beside
  every decisive tF1; Delta's extent rule is refused under D7.
- **A11′ stands**; the seed-1 claim that A11 is worse is withdrawn; the conditional A11
  test is dropped. **F3/A20 withdrawn** (the FPs sit on the heart); aorta masks remain
  required. **A10** uses D6's 0.05 per class.

### Human decisions taken 2026-10-11

- **D6 — acceptance margin:** 0.05 per class; A10 is reinstated with that margin (A18
  resolved).
- **D7 — mask outline:** keep it; redraw only to correct a major error in the original
  segmentation (rare), recorded in the case note.

### Human decisions

Recorded in [[Human decisions]] (2026-10-05) and binding on every plan:
the original ImageCAS mask (current Girder mask) is the lumen target, seed and
reference; territory side-branch rule, ramus → LCx; every case labelled twice;
no four-class starting labels; tF1 tolerance fixed at 1.5 mm; no relabelling
cost; acceptance margin 0.05 per class (D6); the outline is redrawn only for a major
error, noted (D7). Nothing is open.
