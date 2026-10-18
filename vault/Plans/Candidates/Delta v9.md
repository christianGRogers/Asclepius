---
tags: [plans, candidate, round9, fir, four-class, tree-f1, ostium, sealed-test, acceptance]
author: Delta
round: 9
version: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Delta v9: train icx4 on Fir as built, and judge it with tree-F1 using ImageCAS-X's own ostia; D6 acceptance needs a sealed set that team reads can reach

## 1. The plan in one paragraph

Train **one four-class nnU-Net v2 ResEnc model** (LM, LAD, LCx, RCA; D25) on **ImageCAS-X's lumen collapsed by territory** (D8, D1, D1b), with **`trillium/icx4` exactly as built**, on **one Fir H100**: about **55–75 GPU-hours**. This is the master's recipe, which won Rounds 1–8, applied to the label set the lead has since fixed.

I propose no change to the model. What icx4 lacks is a valid way to judge it, and that is this plan's contribution:

- **P1. tree-F1 decides, never Dice.** icx4's own scorer reports only Dice. On ImageCAS-X references, a 5 mm cut in the proximal LM leaves LAD and LCx Dice at 1.000 while their tF1 falls to 0 (§4, Q3).
- **P2. ImageCAS-X's released centreline start points are the ostium of record.** ImageCAS-X defines them as centreline ends within 5 mm of a TotalSegmentator aorta, which is A1's own rule. Passed to the pinned `tf1.py` as the "aorta", they make every icx4 score decisive without a CT. The CT-free cheap rule they replace misses the right ostium by more than 5 mm in about 1 case in 10 (§4, Q2).
- **P3. The A14 seal stays shut.** icx4's scorer would open the 80 sealed test cases; Echo's #55 fixes that before the first run. Decisions use the 80 val cases. The 80 open test cases are reported. The sealed 80 are scored once, at the milestone.
- **P4. D6 cannot be applied as things stand (a question for the lead).** D6 accepts a model against **inter-read tF1 on team reads**. Under D22/D23 the only cases that will ever carry two team reads are the 675 pool volumes, so the A14 sealed set (ImageCAS-X test + quality-0 cases) never can. I propose sealing **60 pool patients now**, before any read exists (list in `experiments/Delta/r9_sealed_pool_proposal.json`). Alternatively, the lead can ask the ImageCAS-X authors for their blind second-analyst reads of the test cases.

Every Fir command the lead runs is in §2.4. The tools for P1–P2 are written and self-tested (`experiments/Delta/r9_fir/`).

## 2. The plan

### 2.1 Model and recipe: icx4 unchanged

| Element | Choice | Evidence |
|---|---|---|
| Framework, architecture | nnU-Net v2.8.1, ResEnc planner with a 60 GB target (`nnUNetResEncUNetPlans_60G_iso05`) | Isensee et al., *nnU-Net Revisited*, MICCAI 2024, arXiv:2404.09556, Table 1. ResEnc L and XL beat transformer and Mamba entries; measured VRAM is 22.7 GB (L) and 36.6 GB (XL). The 60 GB target is ours (vault: *Patch size is the dominant lever…*). Multi-class vessel challenges are won by nnU-Net (TopCoW, arXiv:2312.17670v5: "All top teams based their architectures on nnUNet"; [[Foxtrot - Nothing published by October 2026 beats a well-configured nnU-Net on per-branch coronary or vessel labelling]]) |
| Spacing, patch | 0.5 mm isotropic, 256³ patch (128 mm), batch 2 | [[Atlas - Resampling to 0.5 mm isotropic loses nothing measurable, 0.7-0.8 mm does]]; [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]. ImageCAS-X's own nnU-Net (default, 48–56 mm field) has the second-best DSC but β-error 5.6 against CAS-Net's 1.9 with a larger field (arXiv:2608.30404, Table 2) |
| Mirroring | Off | Left/right mirroring would teach that an LAD can be an RCA (vault: *Mirroring is ruled out for multiclass…*) |
| CT window | nnU-Net's default | Round 8 tie-break (−0.0027 [−0.012, +0.006]); Atlas's LCx guard applies (§5) |
| Schedule | 1000 epochs, poly LR, 4-job chain of 23:50 jobs, checkpoint every 10 epochs, resume from either checkpoint | icx14 lost 23 GPU-h to a resume bug, now fixed in icx4 (`job_body.sh`) |
| Loss | Stock Dice + CE. Optional class-weight file, unused unless §5 triggers it | The FP-aware loss pilot (A24) never ran. Its motivation, veins inside the thick mask, may not survive the change to ImageCAS-X's lumen. Re-decided on icx4's FP census (§5) |
| Seeds | One. This first model is a forced choice, not a comparison (A22) | — |

### 2.2 Labels

- **Labels:** ImageCAS-X's 14 classes as drawn (D8), collapsed by `trillium/icx4/lib/territory.py` to the four classes:
  - LM;
  - LAD + D1 + D2;
  - LCx + OM1 + OM2 + IM + L-PDA + L-PLA;
  - RCA + R-PDA + R-PLA;
  - "Other" takes the class of the nearest LAD or LCx voxel, in mm.
- **The collapse is verified.** Echo's audit (#49, PR #59) finds this table matches D25 exactly, and all five copies of it agree.
- **The reference is clean (Q1, §4).** On {N_Q1} non-sealed references, every class is one piece. No class lacks a centreline, so A1c's fallback is never needed (5 % of thick references needed it). The LM is absent in {LM_ABSENT} cases (D13 makes LM optional).

### 2.3 Data and splits

| Set | Cases | Use |
|---|---|---|
| ImageCAS-X train | 560 | Training |
| ImageCAS-X val | 80 | nnU-Net validation, fold 0. **All development decisions** (§5) |
| ImageCAS-X test, open | 80 (36 clean + 44 development) | Reported beside val. Never used for a choice |
| ImageCAS-X test, **sealed** (A14) | 80 | Scored **once**, at the milestone (P3) |
| ImageCAS excluded by ImageCAS-X | 200 | Predicted only (icx4's `predictions/`). They have no labels; ImageCAS-X excluded them for image quality |
| SegQueue14 pool (D23) | 675 volumes | Team reads (two per volume). **P4:** 60 patients sealed for D6. The rest feed fine-tuning later (§2.6) |

The case mapping c(id − 1) and the split files are ImageCAS-X's own, as in icx4. The 560/80/160 split is confirmed in arXiv:2608.30404, "Data Subsets".

### 2.4 Schedule on Fir, and the exact commands

**Fir facts,** from [[Compute inventory - Nibi or Fir run icx4 unchanged on def-aso22, the AI clusters need an aip- allocation]] and docs.alliancecan.ca/wiki/Fir, read 2026-10-18:

- 160 nodes × 4 H100 SXM5 80 GB. The bundle per GPU is 12 cores and 280 GB. About half the nodes are MIG, so the job must name `h100:1`.
- Walltime up to 7 days.
- Account `def-aso22`, after a CCDB opt-in.
- SCRATCH 20 TB, **purged after 60 days**; PROJECT 1 TB.
- Compute nodes have internet.
- **The lead's account (PM, from #46 / PR #52):**
  - `def-aso22`, which Slurm maps to `def-aso22_gpu` / `def-aso22_cpu`, with no MaxJobs/MaxTRES/GrpTRES limits;
  - RawUsage 0, so fairshare priority is at its maximum;
  - partitions by walltime (3 h, 12 h, 24 h, 3 d, 7 d, plus 24 h gpubackfill), so icx4's 23:50 jobs land in the 24 h partition;
  - SCRATCH 19 TiB (60-day purge), HOME 48 GiB; PROJECT space unconfirmed.

| Step | Resource | GPU-h | When |
|---|---|---|---|
| 0. Prerequisites: CCDB opt-in for Fir; copy `cases/` (Globus `alliancecan#trillium` → `alliancecan#fir`) and the repo at `dev` **with #55 merged** | lead | 0 | before 1 |
| 1. **icx4**: plan + preprocess, 1000 epochs, predict 1000 cases, Dice score (open 80 only, after #55) | 1 × H100, 12 cores, 280 GB; chain of 4 × 23:50 | **50–70** (Trillium measured 184 s/epoch, 455 epochs in 23.3 h on icx14; Fir has 10 data workers instead of 22, so up to 1.4× slower) | first |
| 2. **delta9 aorta** (optional, recommended): TotalSegmentator aortas for the 160 non-sealed test/val cases | 1 × H100, 2 h limit | ≤ 1.5 | after 1 |
| 3. **delta9 score**: decisive tF1 (P1, P2), A1-as-written paired if step 2 ran, FP gate, Dice | CPU, 32 cores, 192 GB, 3 h limit | 0 | after 2 |
| 4. Copy the checkpoint and `results/` out of SCRATCH (60-day purge): PROJECT if confirmed, else HOME (48 GiB) | lead | 0 | after 3 |
| Total | | **≈ 52–72 GPU-h** | about 3–4 days with queue wait |

**Commands** (copy-paste; paths assume the repo is at `$SCRATCH/asclepius` with `cases/` inside it):

```sh
# on fir.alliancecan.ca, login node (it has internet)
cd $SCRATCH/asclepius && git log --oneline -1          # must include Echo's #55 (icx4 never scores sealed cases)
ls cases | head -3                                     # 1.img.nii.gz 1.label.nii.gz ... (ImageCAS layout)

# 1. icx4 (about 50-70 GPU-h, a chain of 4 jobs)
cd $SCRATCH/asclepius/trillium/icx4
ICX4_DRYRUN=1 ICX4_CLUSTER=fir ./icx4                  # check: --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G
ICX4_CLUSTER=fir ./icx4                                # builds $HOME/icx14-venv once, fetches labels, submits the chain
./icx4 status                                          # after ~2 h: s/epoch; above ~250 s the 4th job is used

# 2.+3. after `./icx4 status` says DONE: aortas (GPU, about 1 h), then the decisive score (CPU, about 1 h)
cd $SCRATCH/asclepius/experiments/Delta/r9_fir
DELTA9_DRYRUN=1 ./delta9 all                           # check both job headers
./delta9 all
./delta9 status
./delta9 collect                                       # -> results/SUMMARY.md, summary.json, per_case.jsonl

# 4. keep the model past the 60-day scratch purge (PROJECT if it exists, else HOME: checkpoint + results < 2 GB)
DEST=~/projects/def-aso22/$USER/icx4; [ -d ~/projects/def-aso22 ] || DEST=$HOME/icx4-keep
mkdir -p $DEST && cp -r $SCRATCH/icx4/results \
  $SCRATCH/icx4/nnunet_results/Dataset715_ICX4/*/fold_0/checkpoint_final.pth $DEST/
```

**What to send back (on #48 or a new issue):**

- `trillium/icx4/results/SUMMARY.md` and `results.json`;
- `experiments/Delta/r9_fir/results/SUMMARY.md`, `summary.json` and `per_case.jsonl`;
- `slurm-*.out` of any job that failed.

`delta9 score` also runs without step 2, and is then decisive under P2 alone. The scorer refuses to run unless `tf1.py` matches the pinned A1c hash, and it refuses every sealed case. It needs no VTK on Fir: the start points are committed as `experiments/Delta/r9_expert_ostia.json` (non-sealed cases only).

### 2.5 The deciding metric and how it is read

| | Rule | Status |
|---|---|---|
| Metric | tF1 at 1.5 mm (D3), `src/segtrain/tf1.py` sha256 `24441cf8…5254` (A1c, Round 8), fallback centreline default | Unchanged |
| **P1** | Dice (icx4's `score.py`) is **reported for comparison with the literature only**. No decision reads it | New. Evidence: §4 Q3, §3 |
| **P2** | Ostium of record on ImageCAS-X references = the released start points, passed to `find_ostia` as the aorta (1 mm balls). Same code, same hash. A tree is A1b-flagged only if its ostium of record is not within 2 mm of a start point. Disagreement with the CT-free "thick" rule no longer flags it, because that rule is the one that fails (Q2) | **New, the judge's call (A1/A1b).** Validated by step 2 on Fir (§5 row 3). Team reads (no start points) keep A1 as written: TotalSegmentator aorta |
| **P3** | Decisions on val 80. Open 80 reported. Sealed 80 once, at the milestone, against ImageCAS-X. icx4 must not score them (#55) | Restates A14/A19 for icx4 |
| **P4** | D6 acceptance on a sealed pool set (60 patients, rule fixed in `experiments/Delta/r9_sealed_pool.py`) | **Lead decision** (§7) |
| A15 | FP gate ≤ 1 component per case, raw prediction | Unchanged; reported by `delta9 score` |
| A22 | σ_seed = 0.013 for retrained comparisons | Unchanged. None is planned in the first job |
| A23 | Contrast-supported tF1, report only | Kept. It needs CT and aorta, so `delta9` adds it in a later round, not the first job |

### 2.6 After the first model (unchanged from the master, mapped to D22–D25)

- icx4's predictions are what later models must beat on the same val 80 (paired, case-only CIs for fixed predictions; A22 for retrained ones).
- When pool reads arrive: each read is one sample (A11′). A third read is triggered by decision-level disagreement. The fine-tune trainer is A17a's. A pool model is scored against its reads with TotalSegmentator ostia (A1).
- The P4 sealed pool patients are read like every other volume but **never trained on, never prelabelled and never inspected** before the milestone.
- These steps need a `configs/tasks/` entry for four-class pool reads, which Echo flagged (#49). That is for the judge or PM once the route is chosen. It is not needed for the first job.

## 3. External evidence: where our numbers sit

Sources were opened and quoted by me or a sub-agent working for me. Full quotes are in `experiments/Delta/r9_citations.md`. Where a source was read as an abstract or preprint only, the table says so.

| Claim | Source (table) | Comparable with ours? |
|---|---|---|
| Dice can be identical for two segmentations with different topology | Shit et al., clDice, CVPR 2021, arXiv:2003.07311, §1 and Fig. 1 | Yes, the same argument. Q3 measures it on our reference |
| On ImageCAS-X's 160 test cases, nnU-Net (default) has DSC 89.8 with β-error 5.6, and nnU-Net + clDice raises DSC to 90.0 while β-error worsens to 8.0. "Topological errors such as vessel breaks are present in all model predictions despite high DSC and clDice" | Bransby et al., ImageCAS-X, arXiv:2608.30404v1 (preprint), Table 2 and Fig. 6 text | Same cases, binary lumen, Dice. icx4's whole-tree Dice on the open 80 (a subset) is comparable as a sanity check only |
| Human ceiling per branch: inter-observer DSC LM 91.9, LAD 92.3, **LCx 84.8**, RCA 95.3 (n = 155–160 test cases) | ImageCAS-X, Table 1 | Same lumen convention, Dice not tF1. It predicts that **the LCx is our weakest class**, as it was in run 1 (0.846) |
| Measuring a vessel only up to its first error is established practice: CAT08's OF is "overlap until first error", ignoring the first 5 mm | Schaap et al., *Med Image Anal* 13:701–714, 2009, doi:10.1016/j.media.2009.06.003, §4.4.2 | Our tF1's "past a break counts missed" is the same idea per class. Differences: a fixed 1.5 mm tolerance rather than the local radius, and a precision side |
| Metric guidance recommends clDice over DSC for tubular structures | Maier-Hein et al., *Metrics Reloaded*, Nat Methods 21:195–212, 2024, doi:10.1038/s41592-023-02151-z, Step 2 and Table 1 (FP2.3, FP3.3) | Supports P1's direction. clDice alone is still blind to a disconnection: after Q3's cut the LAD voxels are untouched, so the LAD's clDice is exactly 1 |
| Per-class topology scoring has precedent: TopCoW scores class-average β0 error and a topology-match rate, while its clDice is on the merged mask | Yang et al., TopCoW, arXiv:2312.17670v5, Table S6/S15 (NEJM AI DOI from the header, not opened) | Methodological precedent for per-class topology. Different anatomy |
| ASOCA: top Dice 0.87, ensemble 0.88, on 20 test cases, binary | Gharleghi et al., CMIG 97:102049, 2022, Table 1 | Not comparable (binary, other data) |
| ImageCAS baseline Dice 82.96 % on its original labels | Zeng et al., CMIG 109:102287, 2023 (read from arXiv:2211.01607v2, Table 4) | Not comparable. ImageCAS-X measures those labels at DSC 41.8 against its own (Table 2) |
| Per-branch labelling of *centrelines* reaches F1 0.976–0.990 per main branch | CPR-GCN, CVPR 2020, arXiv:2003.08560, Table 3 (511 private CCTA). LWT-ARTERY-LABEL, arXiv:2508.06874, Table 2. TopoLab, MICCAI 2023, arXiv:2307.11959, Table 1 | **Not comparable.** They label a given centreline graph and do not segment voxels. Our naming error is already small (run 1: naming and connectivity ≤ 0.03 per class, [[Delta - Phase A confirms the RCA was an ostium artefact, and the remaining loss is mask vessel without contrast]]) |
| TotalSegmentator's coronary output: zero-shot DSC 70.5, β-error 4.6 on ImageCAS-X | ImageCAS-X Table 2. No peer-reviewed Dice exists for its coronary task. The aorta is one of 104 classes, overall Dice 0.943 (Wasserthal et al., Radiol AI 2023, doi:10.1148/ryai.230024) | It is the D23 seed for pool volumes, not a competitor. Its aorta is what defines both A1 and P2 |

**What I did not find:** a published learned model reporting per-branch (LM/LAD/LCx/RCA) **voxel** segmentation on public CCTA. Foxtrot reached the same conclusion in Round 6. ImageCAS-X benchmarks only binary lumen; its per-segment numbers are inter-observer only. So our run-1 numbers (macro tF1 0.896 on the thick reference) and icx4's have no direct published comparator. The nearest are the human per-branch Dice ceiling above and the binary benchmark.

## 4. Experiments this round (CPU)

Note: [[Delta - On ImageCAS-X references tree-F1 needs no CT, because the released start points are the ostia, and Dice cannot see a proximal cut]]. Code: `experiments/Delta/r9_*.py`.

The data was ImageCAS-X labels and centrelines, fetched by range requests from Zenodo (CC BY 4.0). The 80 sealed cases were never downloaded. The pinned `tf1.py` hash was checked at start.

- **Q1, reference audit ({N_Q1} cases).** {Q1_SUMMARY}
- **Q2, ostia ({N_Q1} cases).**
  - The released start points coincide with the free end of the LM line (left) and the RCA line (right) in {START_AGREE} (0 mm). Seven LM-less cases have two left start points.
  - Our skeleton passes through the start points: median {EXP_CL_MED} mm, max {EXP_CL_MAX} mm. ImageCAS-X built its centrelines with the same Lee skeletonisation.
  - The CT-free "thick" rule lands more than 5 mm from the start point for the **right** ostium in **{THICK_R5}** and the left in {THICK_L5}. It picks a distal RCA end 22–47 mm away.
  - On Trillium, atlas2 already measured the TotalSegmentator-aorta ostium against these start points on the 80 val cases. The median is 1.9 mm (left) and 2.1 mm (right), and 89–90 % are within 5 mm, although that was on the thick reference, where A1 flagged most of the outliers.
- **Q3, the cut that Dice cannot see ({N_Q3} val references).** All reference voxels within 2.5 mm of the point 3 mm (left) and 15 mm (right) downstream of each start point were removed, leaving a gap of about 5 mm.
  - {Q3_SUMMARY}
  - With the thick-rule ostia, the cut changes the macro tF1 by more than 0.05 differently in {Q3_DIFF} cases: the proximal RCA cut goes unseen (c0106: RCA tF1 0.96 with thick ostia, 0.10 with start points).

## 5. What results change the plan (pre-registered, read on val 80 at the pinned hash with P2 flags)

| # | Result of step 3 | Then |
|---|---|---|
| 1 | Decisive macro tF1 ≥ 0.87 | The recipe stands. My expectation is ≥ 0.90, with the LCx the lowest class (run 1 on its own reference: 0.896; ImageCAS-X's inter-observer LCx is the lowest) |
| 2 | Decisive macro < 0.87 | Recipe reopens (Round 8's line). First check: the label census, and "Other" voxels for LAD/LCx swaps |
| 3 | P2 vs A1-as-written (step 2): ostia within 2 mm in ≥ 95 % of trees **and** \|Δ macro tF1\| ≤ 0.005 | P2 becomes the rule of record for ImageCAS-X references. Otherwise P2 is withdrawn and TotalSegmentator aortas are required for every decisive score, as now |
| 4 | LCx decisive tF1 < 0.83 | Atlas's Round 8 LCx guard: review calcified LCx cases under the default window |
| 5 | FP components per case ≤ 1 (A15 met) | A24's FP-loss pilot is dropped. The thick-mask veins were the reason for it |
| 6 | FP per case > 1 | FP census on icx4's val (atlas2's census script). If confident components beside the tree dominate again, A24's pilot runs on Fir (≤ 21 GPU-h, two arms, same seed and epochs, A22 rules) |
| 7 | Any (case, class) with Dice ≥ 0.85 and tF1 < 0.5 | Listed in the report as evidence for P1. Never a decision |

## 6. Risks

| Risk | Response |
|---|---|
| Fir's 10 data workers make icx4 CPU-bound (≥ 250 s/epoch, > 70 GPU-h) | The 4th chain job absorbs it (compute inventory). Report s/epoch; Nibi (14 cores per GPU) is the fallback |
| #55 is not merged before the lead runs icx4 | The seal opens. §2.4 step 0 checks for it. The PM should not hand over the commands until #55 is on `dev` |
| P2's start points depend on ImageCAS-X's own TotalSegmentator heart-chambers aorta, not ours | Step 2 measures exactly that (row 3). The two disagree only where the aorta itself does |
| P4's sealed pool set takes 60 of 242 QC-annotatable volumes out of training | 25 % of the best pool volumes; the number is the lead's. With Bridge's paired SD (0.041 macro), 60 cases resolve about 0.015 macro. Per-class power at D6's 0.05 margin depends on the inter-read SD, which only the first reads measure; N can grow before any sealed volume is read |
| Patient grouping in the pool is by `<Source>__<Case>` minus `_tp<k>` | Correct for the D22 naming as written. A source that hides one patient under two case names would leak; the source list is short enough for the SWE to check at implementation |
| 60-day scratch purge on Fir | Step 4 copies the model and results to PROJECT, or to HOME while PROJECT is unconfirmed |

## 7. Decisions for the lead (through the PM)

1. **P4: where D6 acceptance is measured.** The A14 sealed set will never have two team reads under D22/D23. Options:
   - (a) **(recommended)** Seal 60 pool patients now, by the rule in `r9_sealed_pool.py`, before any read exists. They are read twice and never trained on; D6 is scored there.
   - (b) Ask the ImageCAS-X authors for the blind second-analyst reads of the 160 test cases (the paper says each was re-read). D6 would then use the 80 sealed ImageCAS-X cases with two expert reads.
   - (c) Both.

   Without one of these, D6 cannot be evaluated for any model.
2. Running steps 1–4 on Fir (≈ 52–72 GPU-h on `def-aso22`).

P1–P3 need no human decision; they are for the judge.

## 8. Changes since v8

- New schema (D25) and label source (D8). v8's extent rule is gone: D12 now allows redrawing the outline, and ImageCAS-X's lumen is the target.
- From the master's recipe I keep everything and add a launcher on top of it, so the plan runs on Fir.
- New: P2 (start-point ostia, measured), P1 measured on the new reference, and P4 (the acceptance gap), with the sealed-pool rule fixed before any read exists.
- v8's §D held: still no GPU experiment of my own. The one GPU item I add is step 2, a ≤ 1.5 GPU-h check.
