---
tags: [plans, candidate, round-9, fir, four-class, evaluation, sealed-test, A10]
author: Crucible
round: 9
version: 10
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Crucible v10: train icx4 on Fir now, and move A10 to a sealed share of the pool, because no sealed case will ever have two reads

## 0. Improve or start again?

**Start again on the frame, keep the evidence.** D25 (four classes), D22/D23 (no ImageCAS case is ever annotated;
SegQueue14 serves only the 675 pooled volumes) and the move to Fir change what the plan is about. v9 was a set of
amendments to Atlas v9's proxy-label plan. Its parts that still hold carry over unchanged: A11′ (each read is its own
sample), A22 (the seed rule), and A17c (a teacher is admitted only if it would pass as a model).

This round's work:

1. [[Crucible - No sealed case will ever have two reads, so A10 needs a sealed share of the pool]]: the sealed
   test has no inter-read and never will; power of A10 on pool volumes; a hash-drawn sealed pool set.
2. [[Crucible - The territory collapse is clean, and a third of the LCx class is side branch]]: what D25's collapse
   does to the 720 non-sealed ImageCAS-X label maps.
3. A citation check of every external number used below (§9).

## 1. Thesis

1. **The model is right; train it now.** icx4 (nnU-Net v2 ResEnc, 0.5 mm, 256³, ImageCAS-X collapsed by territory)
   is the best-evidenced recipe the project has, and it runs on Fir with no change but the job header (already in
   `dev`). No CPU or literature evidence argues for a different architecture for this data (§2). The first Fir job
   is icx4 as written, plus the two scoring fixes already filed (#55 seal, #54 tF1).
2. **The acceptance test has lost its cases.** A10 (D6) needs two team reads per sealed case. D22/D23 put no
   ImageCAS case in the queue, and ImageCAS-X released one read per case. So none of the 100 sealed cases will ever
   have an inter-read. A10 can only be run on **pool** volumes. They have to be sealed **now**, before any pool read
   exists, or every pool case will have been seen by the time the model is judged.
3. **150 sealed pool patients**, drawn by a pre-registered hash rule by patient and source, give a human-level
   model a 79 % chance of passing A10 (44 % if pooled sources are 30 % noisier). The rule never passes a model 0.05
   worse than a second reader. At 100 patients a human-level model passes about half the time.
4. **The labels need no change** (§3). The one place to watch is the LCx: it is a third side branch and the weakest
   class in every source.

## 2. Model and architecture

**Unchanged from icx4** (`trillium/icx4`, D25):

- nnU-Net v2.8.1, ResEnc with the 60 GB plan `nnUNetResEncUNetPlans_60G_iso05`;
- 0.5 mm isotropic, patch 256³ (128 mm), batch 2;
- mirroring off;
- stock DiceCE;
- 1000 epochs, poly LR over the full run;
- chained 23:50 jobs.

Why not change it:

| Question | Evidence | Verdict |
|---|---|---|
| Is ResEnc a sound backbone? | nnU-Net Revisited (Isensee et al., MICCAI 2024, arXiv:2404.09556, **Table 1**): ResEnc L ≥ default nnU-Net on 5 of 6 datasets (KiTS 88.17 vs 86.04, AMOS 89.41 vs 88.64), and above every transformer tested (SwinUNETR KiTS 81.27, nnFormer 75.85, CoTr 84.59). Measured VRAM: M 9.1 GB, L 22.7 GB, XL 36.6 GB. Our 60 GB plan is above XL in memory because of the 256³ patch, not the network | Keep |
| Does a coronary-specific network beat nnU-Net on this exact data? | ImageCAS-X (arXiv:2608.30404, **Table 2**, merged lumen, 160 test): CAS-Net 91.2 ± 2.8, nnU-Net 89.8 ± 3.2, nnU-Net + clDice 90.0, Swin-UNETR 87.9; inter-observer 92.8. The best method is +1.4 Dice over nnU-Net, binary only, and no per-branch result is published for any method | Not worth a re-implementation before the first model. CAS-Net's margin is within the inter-observer gap, and nothing shows it for four classes |
| Is the 128 mm patch needed? | [[Atlas - A 128 mm patch at 0.5 mm holds the whole tree and the LM in almost every training patch]]; run 1 decisive macro tF1 0.896 with this recipe on the earlier proxy target (Round 8) | Keep |
| Can one network name territories? | icx14 (same recipe, 14 classes) learned the four main classes by epoch ~200 (val pseudo-Dice LM 0.91, LAD 0.91, LCx 0.85, RCA 0.93) and labelled every side branch as its parent ([[icx14 - interim check after job 1 (446 epochs), side branches not yet learned]]). The territory target is what it learned unprompted | Keep 4 classes in one network; no rule namer in the loop (A7 retired) |
| Is there a published per-branch voxel model to match? | None found. All per-branch CCTA work labels **centrelines**: CPR-GCN (CVPR 2020, arXiv:2003.08560, **Table 3**) F1 LM 0.989, LAD 0.988, **LCx 0.976**, RCA 0.990; TreeLab-Net re-run there LCx 0.924; LWT-ARTERY-LABEL (arXiv:2508.06874, **Table 2**) LCx F1 91.85 (lowest of four); Ren et al. 2023 (DOI 10.1186/s12911-023-02332-y, **Table 2**) LCx recall 96.2 %. Kim et al. 2025 (DOI 10.1117/1.JMI.12.1.016002) segment binary with nnU-Net and name afterwards | There is no like-for-like external number for our tF1 per class. §9 says what can be compared |

## 3. Labels

ImageCAS-X as drawn (D8), collapsed by `trillium/icx4/lib/territory.py` (D25, D1, D1b): LM ← LM; LAD ← LAD, D1, D2;
LCx ← LCx, OM1, OM2, IM, L-PDA, L-PLA; RCA ← RCA, R-PDA, R-PLA; Other → the nearest LAD/LCx voxel in mm.

Measured on the 720 non-sealed cases
([[Crucible - The territory collapse is clean, and a third of the LCx class is side branch]]):

- **Other → nearest LAD/LCx is right.** 82 of 90 Other pieces, 99.6 % of Other voxels, get the class of the vessel
  they touch. The 7 exceptions are 1–2-voxel fragments grazing the RCA (8 voxels in all). Other is in 85 cases and is
  0.44 % of vessel voxels. Echo's #56 (segtrain's voxel-index distance) is a consistency fix; it cannot move a
  training label measurably.
- **Territories are whole.** No LM touches the RCA. Only 8 cases have a territory in two pieces (gaps in ImageCAS-X's
  lumen). 708 of 720 trees are exactly two components. LM is absent in 11 cases (separate ostia; D13 makes LM
  optional).
- **Side branches** are 24.5 % of the LAD class, 35 % of the LCx class (90th percentile 57 %) and 25 % of the RCA
  class (medians). So ImageCAS-X's per-trunk inter-observer Dice (Table 1) is not a ceiling for our classes.
- **Balance:** RCA 42.5 %, LAD 29.3 %, LCx 22.9 %, LM 5.2 % of vessel voxels. Class-weighted CE stays off; icx14
  learned an LM of the same size without it.

No label change. No case excluded.

## 4. Data and splits

| Set | Cases | Use |
|---|---|---|
| ImageCAS-X train | 560 | Training (icx4) |
| ImageCAS-X val (fold 0) | 80 | nnU-Net validation, and **decisive tF1 for recipe decisions** (aortas exist: run 1 used the same 80, `$SCRATCH/atlas2/aorta` on Trillium) |
| ImageCAS-X test, open 36 + development 44 | 80 | Decisive tF1 with #54; the 36 clean ones for any claim an advocate did not tune on |
| **ImageCAS-X test, sealed 80** (A14) | 80 | **Stays sealed.** It is no longer an acceptance set (no inter-read). It becomes a one-look, single-read, in-domain milestone (§7) |
| Quality-0, sealed 20 (A14) | 20 | **Retired from scoring.** No reference will ever exist (not in ImageCAS-X, not in the D23 queue). Kept out of everything, for hygiene |
| **Pool, sealed (A14-pool, new)** | 150 patients / 198 volumes | Two team reads each (D23). Never trained on or inspected; **A10 is scored here** on one volume per patient |
| Pool, open | 403 volumes (315 patients) + 74 suspect-spacing volumes | Team reads for fine-tuning (§5, P3) and the wave reports (A12) |

**A14-pool rule** (pre-registered; `experiments/Crucible/r9_seal_pool.py`, list in
`experiments/Crucible/r9_sealed_pool_150.json`):

- candidates are the "QC annotatable" and "QC limited" sections of `configs/segqueue14/pool-2026-10.txt` (601 volumes);
- one patient group per `<Source>__<Case>`, with phase, timepoint and frame suffixes joined: 465 groups;
- groups are ranked per source by `sha256('asclepius-sealed-round9-pool:' + group)`, and the first
  round(150/465 × groups) are sealed (sources with one group are never sealed);
- every volume of a sealed patient leaves training. A10 scores the first volume in serve order.

The ranking is fixed, so a larger set (if wave 1 shows more spread, §8) extends the same list per source rather than
redrawing it. **Annotators do nothing differently.** These volumes are in the queue already and get their two reads
like any other.

## 5. Recipe and schedule

| Phase | When | What | Fir GPU-hours |
|---|---|---|---|
| **P1: base model** | Now | icx4 unchanged on ImageCAS-X 560/80, plus #55 (refuse sealed) and #54 (aortas + A1c tF1) before submission. The tF1 stage also scores **val 80**, using the Trillium aortas copied over (or computed on Fir, about 15 min). Val softmax is **not** saved today (`nnUNetv2_train` runs without `--npz`); adding `--npz` is one line in `job_body.sh` and serves A7 (later inference-only questions) | **50–70** (3–4 chained 23:50 jobs; ~181–187 s/epoch measured on Trillium for this recipe; 10 rather than 22 augmentation workers on Fir's 12-core share, so up to +40 %: compute inventory) + ~0.5 aortas |
| P2: wave-1 report | First ~50 open pool patients double-read | A12 report on **open** pool reads only: inter-read tF1 per class; model-vs-read tF1 (P1 predicting those volumes); **seed-vs-read tF1** (how much of each read is the TotalSegmentator seed, D23/D26); per-source strata; A23 extent diagnostic. Measures the A10 contrast's real SD, which resizes A14-pool if needed (§8) | ~1 (inference on ≤ 100 volumes) |
| P3: pool fine-tune | ≥ 300 open pool reads (D15's refresh point) | A17 fine-tune trainer from P1, on ImageCAS-X 640 + open pool reads, **each read a separate sample (A11′)**. Arms: ImageCAS-X + pool vs pool-weighted 2:1, equal epochs, one seed, then A22 (a second seed if \|Δ\| < 0.02 on the open-pool validation fold) | 2 arms × ~10 = 20, +20 if A22 triggers |
| P4: final | When the pool reads are complete | From scratch on ImageCAS-X 640 + all open pool reads, the P3 winner's mix, 1000 epochs. One decisive look at **A14-pool (A10)** and at the **sealed ImageCAS-X 80** (milestone) | 50–70 + ~2 inference |

**Total ≈ 120–180 H100-hours** over the project, of which **50–70 now**. The final model never trains on a sealed
case of either set. No proxy labels anywhere: ImageCAS-X is the target, not a proxy (D8).

Why one seed for P1: it is not a comparison. A22 binds when two retrained networks are compared (P3), not when the
first model is trained.

## 6. The first Fir job (for the lead)

Preconditions: #55 and #54 merged into `dev` (both are open `role:swe` issues with sessions started). If they are not
merged when the lead is ready, run P1 anyway, but delete `per_case_test.json`, `results.json` and `SUMMARY.md` from
`$SCRATCH/icx4/results/` unread. `score.py` writes scores that include the sealed 80 there.

**1. Stage the data (Trillium → Fir), Globus web app:** source collection `alliancecan#trillium`, path
`<root>/cases/` (the folder icx4 used on Trillium); destination `alliancecan#fir-globus`,
`/scratch/croger/asclepius/cases/`. Second transfer: `$SCRATCH/atlas2/aorta/` on Trillium →
`/scratch/croger/asclepius/aorta_val80/` (run 1's TotalSegmentator aortas for the same 80 val cases). Or, from the
Fir login node:

```sh
mkdir -p $SCRATCH/asclepius && cd $SCRATCH/asclepius
rsync -a --info=progress2 <you>@trillium.scinet.utoronto.ca:<root>/cases/ cases/        # MFA prompt; or use Globus
rsync -a <you>@trillium.scinet.utoronto.ca:'$SCRATCH/atlas2/aorta/' aorta_val80/
```

**2. Code and a dry run** (Fir login node `fir.alliancecan.ca`; `CC_CLUSTER=fir` selects the Fir profile itself):

```sh
cd $SCRATCH/asclepius
git clone -b dev https://github.com/christianGRogers/Asclepius.git repo      # or git -C repo pull if present
mkdir -p experiments && rm -rf experiments/icx4 && cp -r repo/trillium/icx4 experiments/icx4
cd experiments/icx4
ICX4_DRYRUN=1 ./icx4 | tail -n 15
# expect: cluster: fir; --gpus-per-node=h100:1, --cpus-per-task=12, --mem=280G, --account=def-aso22, --time=23:50:00
```

**3. Submit:**

```sh
./icx4            # builds $HOME/icx14-venv once (torch from the wheelhouse, nnunetv2==2.8.1 from PyPI), fetches the
                  # ImageCAS-X labels (Zenodo), submits a 4-job afterany chain to def-aso22 (gpubase_bygpu_b3, 24 h)
./icx4 status     # after ~2 h: s/epoch. Above ~250 s/epoch, all 4 jobs are needed (the chain already has 4)
```

Resources: 1 × H100 80 GB, 12 cores, 280 GB per job; **expected 50–70 GPU-hours** (3–4 jobs), charged to
`def-aso22_gpu`. Queue: the 24 h by-core GPU partition had 309 jobs queued at ~06:00 UTC today, and the account has
top fairshare (no usage), so expect a start within hours, not days *(estimate)*.

**4. Send back:** `./icx4 collect`, then the `results/` folder (SUMMARY.md, results.json, val summary, training
log, timings; under 1 MB). Never the sealed per-case file if #55 was not merged.

## 7. Deciding metric

| Decision | Metric | Set | Rule |
|---|---|---|---|
| Recipe choices (P3, any ablation) | Decisive macro and per-class tF1 @ 1.5 mm (A1, D3), `segtrain.tf1` sha256 `24441cf8…5254` (A1c), flagged trees apart (A1b) | ImageCAS-X val 80 (+ open pool validation fold for P3) | A22: seed term in the CI; < 0.02 needs 2 seeds |
| **Acceptance (D6)** | **A10:** per class, model-vs-reads tF1 − inter-read tF1, paired bootstrap lower bound > −0.05 (`segtrain.reads.acceptance`) | **A14-pool, 150 patients** | All four classes pass. LM may be reported rather than gated if its CI is too wide (Round 3; D13 makes LM optional) |
| In-domain milestone (report) | Decisive tF1 vs collapsed ImageCAS-X (single read); whole-tree Dice beside ImageCAS-X Table 2 | Sealed ImageCAS-X 80, one look at P4 | Reported. Pre-registered red flag: macro tF1 more than 0.03 below the open-test value → overfitting to the open set; investigate before release |
| FP gate (A15) | Raw FP components per case | val 80 / A14-pool | ≤ 1 per case. Still unmet by any model (run 1: 1.49); the human question from Round 8 §6 stands |

Dice stays secondary everywhere. It is never compared with ImageCAS-X Table 1 (trunk classes).

## 8. What results would change the plan

| Result | Where | Then |
|---|---|---|
| P1 val decisive macro tF1 ≥ 0.85 and every class ≥ 0.80 | P1 | Proceed to P2 |
| LCx decisive tF1 < 0.83 (Atlas's guard) | P1 | Review calcified and side-branch-heavy LCx cases (side share > 0.57) before P3; consider the class-weight file for the LCx only, under A22 |
| Any class < 0.75 or macro < 0.80 | P1 | Stop. Check the collapse and the scorer on 5 val cases before spending more GPU |
| P1 whole-tree Dice on the open test more than 3 points below ImageCAS-X's nnU-Net (89.8) | P1 | Our pipeline (0.5 mm resampling, plan) is losing lumen. Check before P3 |
| Wave-1 A10 contrast SD > 1.3 × assumed (Bridge's 0.15–0.19) | P2 | Extend A14-pool to 200 patients along the same hash ranking, before reads of the extra patients exist |
| Model-vs-read tF1 more than 0.10 below inter-read in a class, on open pool | P2 | Domain or convention gap. P3 is mandatory before any acceptance attempt; report per source |
| Seed-vs-read tF1 ≥ inter-read tF1 − 0.02 in a class | P2 | The reads mostly keep the TotalSegmentator seed's extent (D26), and inter-read agreement is shared-anchor agreement. A10 then compares the model with a seed-anchored pair; the A23 extent diagnostic becomes the first thing reported beside A10, and the question goes to the lead (§11, Q3) |
| Inter-read tF1 < 0.80 in a class | P2 | A12 re-instruction trigger (habits), as before |
| P3 arms differ by < 0.02 with two seeds | P3 | "No difference detected"; take the simpler mix (ImageCAS-X + pool, unweighted) |

## 9. External evidence: what is comparable and what is not

All checked on 2026-10-18 (DOIs resolved; tables read). Not verified: the ASOCA top Dice (publisher text blocked),
TreeLab-Net's own per-branch table (paywalled), and Cao 2017's per-branch table.

| Source | Number | Comparable to ours? |
|---|---|---|
| ImageCAS-X, arXiv:2608.30404, Table 2 | Merged-lumen DSC: inter-observer 92.8 ± 3.1; nnU-Net 89.8 ± 3.2; CAS-Net 91.2 ± 2.8; TotalSegmentator 70.5; original ImageCAS labels 41.8 | **Yes, for whole-tree Dice:** same images, lumen convention and split (use the non-sealed half) |
| ImageCAS-X, Table 1 | Inter-observer DSC per **trunk**: LM 91.9 ± 13.7, LAD 92.3 ± 6.7, LCx 84.8 ± 19.8, RCA 95.3 ± 5.0; side branches 70.9–83.6 | **No:** our classes are territories (24–35 % side branch). Direction only: LCx is the hardest |
| Run 1 (Round 8) | Decisive macro tF1 0.896 (LM 0.966, LAD 0.901, LCx 0.846, RCA 0.883) | **No:** proxy labels on the original ImageCAS masks (D0 era), now superseded by D8. Same recipe, different target and lumen; a sanity range only |
| icx14 interim (446 epochs) | Val pseudo-Dice LM 0.91, LAD 0.91, LCx 0.85, RCA 0.93 | **No:** trunk targets, with side branches predicted as their parent (so penalised); a lower bound on what the territory model should reach |
| CPR-GCN, CVPR 2020, arXiv:2003.08560, Table 3 | Segment F1: LM 0.989, LAD 0.988, LCx 0.976, RCA 0.990 (511 CCTA, 5-fold) | **No:** naming given centreline segments, not segmenting voxels. Agrees that LCx is the weakest |
| LWT-ARTERY-LABEL, arXiv:2508.06874, Table 2 | F1 % LM 96.92, LAD 94.81, LCx 91.85, RCA 97.56 (n = 70) | Same caveat |
| Ren et al. 2023, BMC Med Inform Decis Mak, DOI 10.1186/s12911-023-02332-y, Table 2 | Segment-presence recall: LM 100 %, LCx 96.2 % (right-dominant only) | Closest to our class detection rate; not to tF1 |
| CAT08, Schaap et al. 2009, MedIA, DOI 10.1016/j.media.2009.06.003, §4.4.2 | OF = overlap until first error | The published analogue of tF1's break rule; centreline-only, 4 vessels, 32 cases |
| ASOCA, Gharleghi et al., CMIG 2022, DOI 10.1016/j.compmedimag.2022.102049; data descriptor arXiv:2211.01859 | 40 + 20 cases, binary; inter-annotator Dice 85.6 ± 7.7 | Binary; a different population. Not used for decisions |
| ImageCAS, Zeng et al., CMIG 2023, DOI 10.1016/j.compmedimag.2023.102287, Table IV | Binary baseline Dice 82.96 | **No:** the original labels, which ImageCAS-X shows agree with expert re-annotation at 41.8 |
| TotalSegmentator, Wasserthal et al., Radiol AI 2023, DOI 10.1148/ryai.230024 | No coronary class in the paper; the licensed `coronary_arteries` subtask is binary. ImageCAS-X Table 2 gives it 70.5 | It is our pool seed (D23), so the reads start 20 points of Dice below ImageCAS-X's lumen. This is why P2 measures seed-vs-read |
| Jungo et al., MICCAI 2018, arXiv:1806.02562, Table 1 | Training on a randomly sampled rater per iteration keeps Dice (0.99 vs majority vote 0.99) with better-calibrated uncertainty | Supports A11′ from outside; synthetic and brain data |
| STAPLE, Warfield et al., IEEE TMI 2004, DOI 10.1109/TMI.2004.828354 | EM fusion of raters | Not adopted. Fusion did not beat each-read-as-sample in our two-seed experiment (Round 8) |
| TopCoW, arXiv:2312.17670 | 13-class per-vessel segmentation scored by class Dice, clDice, Betti-0 and detection F1 | Precedent for per-vessel class evaluation with topology terms; supports tF1 over Dice |

**Gap.** No published work reports voxel-wise per-territory segmentation of LM/LAD/LCx/RCA on CCTA. The project's
4-class tF1 has no external comparator. This is why the internal acceptance test (A10) must be sound.

## 10. Risks

| Risk | Detection | Response |
|---|---|---|
| A14-pool takes about a third of pool patients out of training | Training set: 640 ImageCAS-X + ~315 pool patients | Acceptable: ImageCAS-X is the backbone. The alternative is an acceptance test with no cases |
| Patient grouping by name misses a hidden duplicate | QC knows each source | QC checks the 150 sealed groups against source metadata before wave 1; any leak is moved, and logged |
| The pool is noisier than assumed; A10 is underpowered at 150 | P2 measures the contrast SD | Extend along the same ranking (§8) |
| Reads anchored on the TotalSegmentator seed make inter-read optimistic | P2 seed-vs-read | §8 row; lead question Q3 |
| Fir throughput (12 cores) | `./icx4 status` s/epoch | The 4th chained job absorbs up to ~70 h; nothing else changes |
| icx4 runs before #55 lands | — | §6 precondition: delete the sealed per-case file unread |
| Congenital and anomalous anatomy in the pool (ImageCHD 83, ImageALCAPA 30 volumes) | Per-source strata in P2 and A10 | Reported per source. A10 is not re-scoped without the lead |

## 11. Questions for the lead (not assumed in the plan)

1. **A14-pool.** Seal 150 pool patients (198 volumes) for A10, withheld from training. D6 says "against the team's
   reads" without naming the cases. This is the only set that will have them. Approve, or set a different size
   (100 patients gives about half the power at human level).
2. **In-domain acceptance, optional.** Should about 30 of the sealed ImageCAS-X cases go into SegQueue14 for two team
   reads, so A10 can also be run in-domain? That changes D23 ("no ImageCAS case"). It costs about 60 reads and gives
   a three-way check (team, team, ImageCAS-X) on the convention.
3. **If wave 1 shows reads keep the seed's extent** (§8): is A10 against seed-anchored reads still the acceptance test
   you want, or should acceptance add a model-vs-ImageCAS-X condition on the sealed 80?
4. **The 20 sealed quality-0 cases** can never be scored. Confirm they are retired.

## 12. Cost

- CPU here: about 1 h (label fetch, 35 min audit, power simulation, seal draw).
- Fir: 50–70 H100-h now; 120–180 H100-h in all.
- Annotators: none beyond D23 (Q2 would add about 60 reads, only if approved).

## 13. Changes since v9

- New frame: D25, D22/D23 and Fir. The model and recipe are icx4, unchanged.
- **A10 cannot run on the sealed test.** New A14-pool, with a pre-registered draw and a power table.
- The sealed ImageCAS-X 80 become a single-read milestone; the quality-0 20 are retired.
- Territory-collapse audit: no label change; trunk inter-observer numbers are ruled out as a ceiling.
- Literature cross-check, with every number located.
- Kept from v9: A11′ (now with Jungo et al. as outside support), A22, A17c.
