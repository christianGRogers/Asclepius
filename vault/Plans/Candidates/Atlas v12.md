---
tags: [plans, candidate, master, four-class, fir, round10, janus, D35, wave-1]
author: Atlas
round: 10
version: 12
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Atlas v12: Janus 1 as a warm fine-tune with ImageCAS-X replay, decided on a 35-patient D35 set drawn outside the seal and its reserve, with the seal sized on the measured contrast and an anchoring test that works

## 0. The plan in one paragraph

**Janus 0** (icx4, D34) stands as the base model: val-80 decisive tF1 0.909 [0.880, 0.932], A15 met, P2 withdrawn
(#43). What follows it is decided on pool reads, in this order.

1. **Freeze the D35 decision set now.**
   - 35 primary-stratum patients (42 volumes), drawn by salted hash within source, outside the D27 seal **and** its
     100-patient extension reserve.
   - A pre-registered second tranche takes it to 50 if the seal ends below 250.
   - The "about 50 of about 347" on #43 was Atlas's miscount. On real patients, 15 % of the non-sealed,
     non-ImageCHD pool is 35.
2. **Run Janus 0 on the non-sealed, non-reserved pool volumes** (one Fir job, about 3 GPU-h, once #116 merges). This
   gives the baseline for every wave-1 measurement.
3. **Size the seal on the measured contrast (A31.1′).** When about 50 primary patients have two reads (around queue
   position 300 of 675), size the seal from the measured per-patient model-vs-read minus inter-read contrast. On
   Janus 0's own spread, 150 patients give only 0.79 power if reads vary independently of the model.
4. **Train Janus 1 once the trigger in §7 is met.** It is a **warm fine-tune from Janus 0** (A17a, 250 epochs) on
   ImageCAS-X train 560 as replay plus the trainable pool reads (each read a sample, A11′).
   - Three runs on Fir: primary LR twice (two seeds, which also measures σ_g on the master as D28 requires) and the
     1e-3 arm once. About 45 GPU-h.
   - The decision is made on D35 against the reads, guarded on val 80 against ImageCAS-X.
   - From-scratch ImageCAS-X + pool (Crucible P3/P4) costs about 5× as much per decision. It belongs to the lead's
     final-retrain question, not to wave 1.
5. **Detect seed anchoring with a test that works.** It can fail a human-level model under D6, and A31.2's seed flag
   does not see it on phantoms. The working test is the model-vs-read **precision–recall gap**.

## 1. What Janus 0 settled, and what it did not

| Settled (not relitigated) | Source |
|---|---|
| The recipe stands; Janus 0 is the base model | A27 macro 0.909 ≥ 0.85; A26 identity passed (#43) |
| A15 met (FP 0.36/case on val); L7 moot; no softmax census | #43 |
| P2 withdrawn; TotalSegmentator aortas required (A1) | A29, val Δ 0.0079 > 0.005 |
| The Dice row is lumen width (tolerant Dice 0.97, volume ratio 0.87), not lost tree | [[icx4 - Results]] |
| The sealed ImageCAS-X 80 are not looked at until the final model | A26 |
| D35 option A | the lead, 2026-10-25 |

**New this round, from Janus 0's numbers:**

- **Janus 0's per-case val spread is 1.2–1.6× run 1's** in LM, LAD and LCx. Macro SD is 0.117 against 0.065. The
  ImageCAS-X reference traces further distally, so a few cut trees weigh more. This moves two Round 9 numbers: the
  seal's power (§3) and the decision set's resolution (§2.4).
- **The pool is not where Round 9 counted it** (§2.1).

## 2. The D35 decision set

Evidence: [[Atlas - On real patients 61 primary pool patients sit outside the seal and its reserve, so the D35 decision set is 35 of them, in two tranches]].
Draw: `experiments/Atlas/r10_decision_set.py` → `experiments/Atlas/r10/decision_set_proposal.json` (sha256
`bc47690cc1b0acb50037f19ea05ae0619444c1ed1396be592082371b022b6042`).

### 2.1 The counts, reconciled (real patients, `segtrain.pool_seal.ingest_patient`)

| Bucket | Patients | Volumes |
|---|---|---|
| Sealed primary (D27/D32) + sealed ImageCHD report-only | 150 + 20 | 305 + 20 |
| Reserve: the first 100 of the extension order (the 200/250 steps) | 100 | 144 |
| Open primary (incl. extension entry 101) | **61** | 69 |
| ImageCHD, not sealed (D29 stratum) | 63 | 63 |
| Spacing-suspect (ImageALCAPA, HOCMvalvesSeg, CCA200-HF; D29) | 74 | 74 |
| **Total** | 468 | 675 |

- **#43's "about 347"** is 517 − 170 on the pre-D32 name heuristic, and it includes the 63 open ImageCHD patients.
  It is wrong; the error is Atlas's.
- **On real patients:** non-sealed 298; non-sealed and non-ImageCHD **235**; 15 % of that is **35**.
- **The wave-1 note's 198** = 61 + 63 + 74: the patients wave-1 analysis may open today. It is correct, and it is a
  different quantity.

### 2.2 What it is drawn from, and why not the reserve

- **From the 61 open primary patients only.**
  - **Primary**, because the decision set decides what is best for the population A10 scores.
  - **Not spacing-suspect:** tF1's tolerance is in mm.
  - **Not ImageCHD:** D35 says so.
- **Not from the reserve.**
  - A reserve patient whose reads had decided a recipe could never be sealed afterwards. Every reserve patient
    drawn into D35 removes one from the seal's growth room.
  - The order holds 101 patients, so drawing even two from it makes D27's 250 unreachable.
  - Crucible's draw (#116: 35 from all 161 non-sealed primary, extension order recomputed skipping them) would take
    about 22 from the reserve and cap the seal near 229.
  - That changes what D27 allows, so it is the lead's decision, not the round's. This plan keeps D27 whole.
- **The cost of that choice is composition.** The seal and its round-robin extension order exhausted every small
  source. Of the 61 eligible, 43 are Taiwan AI CUP (70 %), against 32 % of the primary stratum and 29 % of the seal.

### 2.3 The draw

| | Value |
|---|---|
| Size | **35 patients, 42 volumes** (tranche 1) |
| Salt | `asclepius-decision-round10-pool:`; rank sha256(salt + patient) within source |
| Allocation | each source at its share of the **whole primary stratum**, capped at its eligible patients (water-filling, then largest remainder): Taiwan 18/43, Mendeley-SDN-cy54ttk3fj 7/8, EpicardialFat 5/5, VMR-Coronary 4/4, Kaggle-CAD 1/1. Taiwan share 51 % (71 % if proportional to the eligible) |
| Unit | the patient: every volume of a drawn patient is in the set; a patient's score is the mean over its volumes and its two reads |
| Tranche 2 (pre-registered) | if A31.1′ ends the seal below 250, released reserve patients join until the set holds **50**, each step taking the source furthest below its primary share, then the lowest salted rank. The lists for "seal ends at 150" and "at 200" are in the JSON (Kaggle-CAD, TotalSegmentator, Figshare-CardiacCT15, IDC-RIDER, Kaggle-HeartSR, SLAWT, VMR, EpicardialFat). At 250, none |
| Trainable meanwhile | the other 26 eligible primary patients (25 Taiwan), the 63 ImageCHD; spacing-suspect once re-gridded; released reserve after A31.1′ |
| Freeze | the JSON as committed in this PR, before any read of a listed patient is looked at. #116/#118 copy it byte for byte to `configs/segqueue14/decision-set-2026-10.json`, sha256-pinned, refused in `convert` and the trainer by real patient; the reserve is refused too until A31.1′ |

**The other open patients are read and measured, not trained on, until A31.1′.** D35 and the 26 trainable patients
are also the patients A31.1 measures f, k and the contrast on. Reading them is the decision set's purpose; D35
forbids only training.

### 2.4 The power it buys

Evidence: [[Atlas - Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]].

- **Two measured pairs.** A warm fine-tune replicate (run 3 F0/F1) and a from-scratch pair (run 1/B), each on val 80.
  - The per-case SD of the paired difference is **0.038 / 0.041**.
  - The mean differences are fully explained by case noise: a model-level term of **0.001 / 0** (1 df each).
- **Paired MDE on Janus 0's spread** (macro tF1, 80 % power):

  | n | Pool like val (f = 1) | f = 1.5 | With A22's 0.013 added as a model-level term |
  |---|---|---|---|
  | 26 | 0.021–0.041 | 0.055–0.062 | 0.063–0.066 |
  | **35** | **0.018–0.036** | 0.048–0.053 | 0.060–0.063 |
  | 50 | 0.015–0.030 | 0.040–0.045 | 0.058–0.059 |
  | val 80 (forgetting guard) | 0.012–0.024 | — | 0.056–0.057 |

  The low end uses the measured SD(Δ); the high end scales it by the ratio to Janus 0's per-case SD.
- **What this buys.** 35 patients resolve the wave-1 question that matters: does a pool fine-tune beat Janus 0 on pool
  reads? They do not resolve second-order recipe questions (< 0.02). Those take pre-registered defaults (§4.3), not
  tests.

### 2.5 How it interacts with A30's extension order

- It does not touch it: the seal, its 101-patient order and the 200/250 steps are unchanged.
- The reserve's back half is released by A31.1′ and feeds tranche 2 and training.

## 3. The acceptance set: 150 or 200–250?

Evidence: [[Atlas - On Janus 0's own spread the 150-patient seal passes a human-level model 0.79 of the time if reads vary independently of the model, and more if hard cases are shared]].

| P(all four pass), human-level model (δ = 0), k = 1 | 150 | 200 | 250 |
|---|---|---|---|
| Round 9 (run 1's spread, independent draws) | 0.97 | — | — |
| **Janus 0's spread, independent draws (f = 1)** | **0.79** | 0.93 | 0.97 |
| Janus 0's spread, f = 1.25 | 0.48 | 0.71 | 0.84 |
| Janus 0's spread, model and inter-read correlated per case, ρ = 0.3 | 0.96 | 0.99 | 1.00 |
| δ = −0.02 (e.g. partial anchoring), independent | 0.15 | 0.31 | 0.44 |

**Recommendation: the seal stays at 150 today, and its size is set on wave 1 by A31.1′.**

- The deciding unknown is the per-patient contrast SD, which depends on ρ, and wave 1 measures it directly.
- The f/k > 1.2 trigger fires by chance 54 % of the time at 50 patients, and ignores ρ.

**A31.1′ (replaces "f or k > 1.2 → extend").**
- Once ≥ 50 primary non-sealed patients have two approved reads, compute per patient and class:
  model-vs-read minus inter-read (Janus 0, decisive tF1).
- Re-run `r10_seal_power.py` with that contrast resampled directly.
- The seal takes the smallest of 150/200/250 whose power at δ = 0 is ≥ 0.8, both at the measured SD and at its
  patient-bootstrap 80th percentile.
- 250 still under 0.8 → report to the lead; the seal stops (as A31.1).
- f and k stay as a report.
- The measured mean δ̂ is read beside this, not into it: an offset is a §5 question.

## 4. Janus 1: the pool fine-tune recipe

### 4.1 Warm (A17a, Atlas F3) against from scratch (Crucible P3/P4), costed on real numbers

Janus 0 measured 192 s/epoch on Fir (#43). An nnU-Net epoch is 250 iterations whatever the dataset size.

| | Warm fine-tune from Janus 0 | From scratch, ImageCAS-X + pool |
|---|---|---|
| Epochs | 250 (A17a trainer, 2500-iteration warm-up then poly) | 1000 (the recipe; A25 forbids fewer) |
| GPU-h per run | ≈ 13.3 train + ≈ 1 prep/predict = **≈ 14–15** (one 23:50 job) | ≈ 53 + 2 = **≈ 55** (3 chained jobs) |
| A decision with two runs of the primary arm (D28 fallback) + one alternative arm | **≈ 45** | ≈ 165 |
| Crucible's 2 mix arms × 2 seeds | — | ≈ 220 |
| Evidence | Fine-tuned CNNs "outperformed or, in the worst case, performed as well as" scratch training, and were "more robust to the size of training sets" (Tajbakhsh et al., IEEE TMI 35:1299, 2016, doi:10.1109/TMI.2016.2535302, abstract). Wave 1 brings about 25–100 pool patients against 560 ImageCAS-X cases: the small-data case | Uses the pool from the start; no inherited bias. But the pool is about 10–15 % of the data at wave 1, and each decision costs about 4× |

**Choice: warm.** It answers the wave-1 question at a quarter of the GPU, and A22's two-run rule is affordable for it.
From scratch is the right tool only once most reads exist: the lead's **final retrain** question (§9).

### 4.2 Data: replay, not pool-only

- Fine-tuning on a new domain alone forgets the old one: "fine-tuning the network for the new domains causes
  catastrophic forgetting" (Karani et al., MICCAI 2018, LNCS 11070:476, doi:10.1007/978-3-030-00928-1_54).
- In nnU-Net specifically, "sequential training mostly depict[s] a rapid fall after task boundaries. Both Rehearsal
  and EWC considerably reduce the amount of forgetting" (González et al., *Lifelong nnU-Net*, Sci Rep 13:9381, 2023,
  doi:10.1038/s41598-023-34484-2, Fig. 4). Rehearsal was best. Also Perkonigg et al., Nat Commun 12:5678, 2021,
  doi:10.1038/s41467-021-25858-z, Fig. 1b.
- So the Janus 1 training set is **ImageCAS-X train 560 (dataset 715's collapsed labels) plus every trainable pool
  read**, each read a sample (A11′).
- **The mix is 50 % pool reads per batch**, by oversampling. The prior is the 50–50 mix of new and replayed data that
  "substantially reduce[s] catastrophic forgetting" in Rolnick et al., NeurIPS 2019, arXiv:1811.11682 (RL, so a prior,
  not evidence for CT).
- **nnU-Net's fold-0 val is ImageCAS-X val 80**, as Janus 0's, and it is never trained on.
- **No pool read is held out by `segtrain index`.** D35 is the only pool hold-out.
- This is exactly #116 §3 and #118 (c).

### 4.3 Does Dataset716 / task 716 fit?

**Partly.** It has the right trainer (A17a, both LR arms), adopts Janus 0's plans field by field, and refuses the D27
seal by patient. Four gaps, all filed:

| Gap | Consequence if run as is | Fix |
|---|---|---|
| Pool reads only, no replay | forgetting on ImageCAS-X; the val-80 guard would catch it only after the GPU is spent | #116 §3a, #118 (c) |
| `segtrain index` holds out its own 15 % val + 15 % test of pool reads, by an unsalted hash | a second, unfrozen hold-out beside D35, and 30 % of the reads lost from training | #116 §3b, #118 (c) |
| Refuses the seal, not D35 or the reserve | it would train on decision-set patients and on reserve patients the seal may still need | #116 §2, #118 (b) |
| `segtrain scinet` cannot request `h100:1` on Fir | a MIG slice, or a refused job | #118 (d) |

**Pre-registered defaults** (not tested, because their effects are under the decision set's MDE):
- 250 epochs;
- warm-up 2500 iterations;
- the 50 % pool share;
- both reads as samples (A11′).

### 4.4 The Janus 1 decision, pre-registered

**Runs**, read in this order and so named Janus 1, 2, 3 (D34):

| Run | Arm | Seed |
|---|---|---|
| a1 | primary (peak LR 1e-2) | 1 |
| a2 | primary | 2 |
| b | `lr1e3` (A17b) | 1 |

The same data, epochs and export for all three. **Scored**, each against Janus 0:
- **on D35:** patient-level macro tF1 against the reads, A1 aortas, flagged trees apart;
- **on val 80:** decisive tF1 against ImageCAS-X (A26);
- **open-36:** confirms the sign.

| # | Question | Rule |
|---|---|---|
| J1 | Does a fine-tune replace Janus 0? | Yes if **both** a1 and a2 have the D35 paired Δ (run − Janus 0) with lower 95 % patient-bootstrap bound > 0, **and** each passes the guards J3–J5. Ship **a1** (pre-registered; a2 is the replicate). If not, Janus 0 stays, and the question is asked again at the next export with more reads, under the same rules |
| J2 | LR arm | b replaces a1 only if D35 Δ(b − a1) has lower bound > 0 and b passes J3–J5. Ties go to the primary arm |
| J3 | Forgetting guard (val 80, against ImageCAS-X) | paired Δ lower bound > −0.02 (MDE 0.012–0.024 at n = 80) |
| J4 | Not learning the anchor | val-80 centreline **recall** against ImageCAS-X does not fall by more than 0.02. A gain on D35 bought by stopping where seeds stop would show here (§5) |
| J5 | FP gate (A15) | ≤ 1 component/case on val 80 and on D35 |
| J6 | σ_g on the master (A22′) | from a1 vs a2: σ̂_g = √(max(Δ̄² − SE², 0) / 2), on D35 and val 80, pooled with the two measured pairs. ≤ 0.005 → later warm decisions use the paired case CI with one run per arm. > 0.005 → σ̂_g is the model-level term, and effects under 0.02 need two runs per arm |
| J7 | Per source (A31.3) | Taiwan and non-Taiwan reported beside each D35 number; decides nothing |

**A22′ in one line.** Both measured pairs put run-to-run variation inside the per-case term. A22's 0.013, added on
top of a paired case CI, would double every MDE (§2.4). The a1/a2 replicate tests this on the master before it is
relied on.

## 5. What seed-anchored team reads measure

Evidence: [[Atlas - Seed-anchored reads can fail a human-level model under D6, and the A31.2 seed flag does not see it]].
Phantoms from Bridge's wave-1 code, scored with the pinned tF1.

- **Width (convention).**
  - Reads redrawn from a TotalSegmentator seed follow the seed's outline unless the reader redraws it. Janus 0 draws
    about one voxel inside ImageCAS-X's.
  - **tF1 cannot see either.** A one-voxel erosion keeps tF1 at 1.000 while Dice falls to 0.69, the phantom form of
    Janus 0's tolerant Dice 0.97 against plain 0.88.
  - So width differences between conventions do not touch A10, only Dice. The **A31 domain check** (Janus 0 against
    each pool volume's TotalSegmentator seed, per source) reports plain Dice, the 1-voxel-tolerant Dice, the volume
    ratio and centreline recall and precision (`r10_dice_check.measure`). A source is flagged, report only, if its
    median tolerant Dice is below 0.75 × the pool median.
- **Extent (anchoring).**
  - If readers keep the seed's distal ends, inter-read tF1 is inflated by the shared anchor, while a model that
    follows the vessel is charged for every millimetre past the read.
  - Seed at half the distal segment, readers not extending: a human-level model is **0.07–0.085 below inter-read and
    fails D6 in every class**.
  - Half-extension: 0.02–0.03 below, which at 150–250 patients cuts P(pass) to 0.15–0.6.
  - Readers who follow the vessel remove it.
- **A31.2's seed flag does not detect it.** On the phantoms it fired in one class of the worst cell, and in cells where
  nothing was wrong. The seed's own jitter and width keep seed-vs-read at 0.70–0.97 either way.
- **The precision–recall gap does.**
  - Anchored: model-vs-read recall 0.96–0.97 and precision 0.81–0.83.
  - Unanchored: the two are equal within 0.02.
- **Proposed A31.2′.**
  - Per class on primary non-sealed patients, report model-vs-read precision − recall with a patient-bootstrap CI.
  - **Anchoring is declared** when the gap is below −0.03 with its CI excluding 0, and inter-read precision is not
    also low.
  - Then L5 goes to the lead with δ̂.
  - The seed flag and Bridge's edit sizes stay as reports.
- **What it does to A10 on the pool.** Under anchoring, A10 measures agreement with the seed's extent. Extending the
  seal cannot fix an offset (§3). Recommendation on L5: §9.
- **Per-source domain shift (A31.3).** Report only, as Round 9 ruled. D35 makes it starker: tranche 1 covers 5 of the
  22 primary sources, so per-source effects are reported, never decided. Multi-centre segmentation results are
  sensitive to which cases are sampled (Maier-Hein et al., Nat Commun 9:5217, 2018, doi:10.1038/s41467-018-07619-7:
  under bootstrapping, the winner stays the winner in only 21 % of tasks on Dice). That is one more reason not to
  decide per source at n ≈ 5–18.

## 6. The left-tree ostium residual behind P2's 0.0079 (report only; P2 is closed)

- **What is known (#43).**
  - The gap is all left tree (LM +0.010, LAD +0.011, LCx +0.011, RCA 0).
  - 4.3 % of val ostia are more than 2 mm from the expert start.
  - The CI's lower bound is 0, and open-36 is exactly 0. So a few val cases carry it.
- **What is not known:** which cases, and whether the cause is the TotalSegmentator aorta mask or the ostium rule.
- `experiments/Atlas/r10_ostium_residual.py` (self-tested) lists them from Delta's existing per-case output, in CPU
  seconds:

  ```sh
  cd $SCRATCH/asclepius/repo && git pull --ff-only && module load StdEnv/2023 python/3.11.5
  python experiments/Atlas/r10_ostium_residual.py $SCRATCH/icx4/delta_p2/per_case.jsonl --split val > $SCRATCH/icx4/r10_ostium_residual.json
  ```

  Send back the JSON on #43. It lists the cases carrying the Δ, each one's share of the mean, and its ostium distance.
- It changes no decision. If one or two cases carry it through a short or misplaced aorta mask, that goes to the A1
  aorta QC note. A1 stays as written.

## 7. The exact next Fir jobs, and when reads are sufficient

All jobs run on `fir.alliancecan.ca` with account `def-aso22`: 1 × H100 SXM5 80 GB (full, `h100:1`), 12 cores, 280 GB.
Always send back the `slurm-*.out` of any failed job. No sealed case is ever fetched or scored. The tools refuse.

### Job P0: Janus 0 on the open pool volumes (now; after #116 merges)

- **What:** the D35, trainable and report volumes (non-sealed, non-reserved: 42 + 27 + 63 + 74 = **206** volumes).
- **Why:** these predictions and aortas are the baseline for every wave-1 measurement (A31.1′, A31.2′, A31.3,
  D35's Janus 0 arm) and the A31 domain check.
- **Cost:** about 0.3–0.5 h of prediction and about 1.5–2 h of aortas. **≈ 3 GPU-h; one 11:50 job.** The script names
  are those #116 specifies.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only          # dev with #116 merged
test -f trillium/pool/fetch_pool.py || echo "#116 NOT merged: stop"
python3 trillium/pool/fetch_pool.py --purpose d35    $SCRATCH/pool/cases   # refuses sealed and reserved names before any request
python3 trillium/pool/fetch_pool.py --purpose train  $SCRATCH/pool/cases
python3 trillium/pool/fetch_pool.py --purpose report $SCRATCH/pool/cases
JANUS0=$(ls ~/projects/def-aso22/$USER/icx4/checkpoint_final.pth $HOME/icx4-keep/checkpoint_final.pth 2>/dev/null | head -1)
POOL_CLUSTER=fir trillium/pool/predict_pool.sh --checkpoint $JANUS0 --cases $SCRATCH/pool/cases --out $SCRATCH/pool/janus0
#   check the printout: 206 volumes (d35 42, train 27, report 137), sealed 0, reserved 0; header h100:1, 12 cores, 280G, 11:50, def-aso22
```

The command surface (`--checkpoint/--cases/--out`, `POOL_CLUSTER=fir`, and the per-source domain report
`$SCRATCH/pool/janus0/domain.json` from `r10_dice_check.measure`: plain Dice, tolerant Dice, volume ratio,
centreline recall and precision, Janus 0 against each volume's TotalSegmentator seed) is what Atlas asked #116 for
in a comment. If #116's PR names them differently, its README is the copy-paste of record.

**Send back:** the job's printout and `$SCRATCH/pool/janus0/` file counts.

### When wave-1 reads are sufficient: the trigger for Janus 1

All four must hold. Pre-registered, so it is not chosen after seeing reads.

1. #116/#118 merged, and A21's dry run passes on the first real four-class double-read export.
2. **A31.1′ has fixed the seal size.** That needs ≥ 50 primary non-sealed patients with two approved reads. In the
   fixed serve order these are all served by about queue position 300 of 675.
3. **≥ 27 D35 patients have both reads approved.** 27 of the 35 are first served by position 277. The last 8 are
   QC-"limited" volumes near the end of the queue. J1 is confirmed, not re-decided, on all 35 (a sign reversal is
   reported, not adopted, as A26).
4. ≥ 20 trainable primary patients with two reads, plus the released reserve after (2).

### Job J1: Janus 1, three concurrent runs (when the trigger holds)

**Cost:** ≈ 14–15 GPU-h per run, **≈ 45 GPU-h** in all, plus about 1 h of shared preprocessing. Each run is one 23:50
job on the 24 h partition. Command surface as #118 specifies (`segtrain` with the Fir profile, the ImageCAS-X + pool
task, D35 and reserve refusal). On the Girder host:

```sh
segqueue14-export --out /srv/segqueue14/export-wave1 --replicas all      # leaves out sealed reads and says how many
```

On Fir, after moving the export to `$SCRATCH/wave1/export`:

```sh
cd $SCRATCH/asclepius/repo && git pull --ff-only && source $HOME/icx14-venv/bin/activate
segtrain index   --root $SCRATCH/wave1/export --layout nested
segtrain convert --task 717 --zenodo-root $SCRATCH/wave1/export --icx-root $SCRATCH/icx4   # refuses sealed, D35 and reserved reads
segtrain plan    --task 717 --zenodo-root $SCRATCH/wave1/export \
                 --plans-from $SCRATCH/icx4/nnunet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json
segtrain preprocess --task 717
ICX4=$(ls ~/projects/def-aso22/$USER/icx4/checkpoint_final.pth $HOME/icx4-keep/checkpoint_final.pth 2>/dev/null | head -1)
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --profile fir --dry-run       # read the header: h100:1, 12 cores, 280G, def-aso22
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --profile fir --runs-root $SCRATCH/runs-a1
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --profile fir --runs-root $SCRATCH/runs-a2
segtrain scinet submit --task 717 --fold 0 --finetune-from $ICX4 --profile fir --arm lr1e3 --runs-root $SCRATCH/runs-b
```

nnU-Net draws a fresh seed per run, so a1 and a2 are seed replicates.

**Scoring** (CPU on the login node, after each run predicts D35 + val 80 + open-36): Bridge's `score_wave1.py` for
D35 against the reads, and `r9_score_icx4.py --pair` for val 80. Each run against Janus 0 gives J1–J7. **Send
back** the three `results/` folders and both scorers' JSON.

If #118 settles different flag names (`--profile`, `--icx-root`, task 717 vs 716 v2), its PR's
`docs/TRAINING-WAVE1.md` is the copy-paste of record, and these lines are its intent.

### Budget

| Job | GPU-h | When |
|---|---|---|
| P0 | ≈ 3 | now, after #116 |
| J1 (3 runs) | ≈ 45 | at the §7 trigger |
| P1: predict released reserve volumes (if any) | ≈ 1–2 | after A31.1′ |
| **To the first Janus 1 decision** | **≈ 50** | |

The from-scratch alternative would be ≈ 165–220 for the same decision.

## 8. What would change the plan

| Result | Change |
|---|---|
| A31.1′ needs 250 | No tranche 2; D35 stays at 35; the trainable pool is 26 primary + ImageCHD + spacing-suspect when re-gridded; J1 is re-costed (same runs, fewer reads) |
| A31.2′ declares anchoring | L5 goes to the lead with δ̂. J4 becomes binding for every fine-tune. Training on anchored reads would teach the anchor |
| J1 passes | Janus 1 (a1) is the base for wave 2. Same rules on the 50-patient D35 if tranche 2 exists |
| J1 fails (no D35 gain) | Janus 0 stays. Re-ask at the next export. If it fails twice with ≥ 100 trainable patients, the warm recipe reopens (the replay share, then from scratch at the final retrain) |
| J3 fails (forgetting) | Raise the ImageCAS-X share to 75 %. One rerun of a1, a2 only |
| J6: σ̂_g > 0.005 | A22's model-level term returns at σ̂_g. Two runs per arm for effects under 0.02. Wave decisions are re-costed |
| P0's domain report flags a source | That source is its own stratum in every report; nothing is excluded without the lead |
| The lead takes Crucible's reserve-inclusive D35 | Use that draw; the extension caps near 229; this plan's rules apply unchanged |

## 9. Decisions for the lead

1. **D35's number.** D35 said "about 50 of about 347". On real patients, 15 % is **35** (of 235), drawn outside the
   seal and its reserve. A pre-registered second tranche reaches 50 if the seal ends below 250.
   - **Recommended: confirm 35 + tranche 2.** It keeps D35's rule and D27's 200–250 room.
   - The alternative, drawing 50 now, needs about 15–22 reserve patients and caps the seal below 250. That changes
     what D27 allows.
2. **L5, if A31.2′ declares anchoring.**
   - **Recommended:** acceptance then requires A10 on the pool seal **and** the sealed ImageCAS-X 80 milestone
     (model vs expert, A26's red flag), with the precision–recall gap reported beside A10.
   - **Optionally, now and cheaply:** a line in the SegQueue14 protocol notes telling readers to follow each vessel
     past the seed's end as far as the contrast allows. D12 already allows it; this is an internal instruction (D31
     does not apply). It removes the effect at its source.
3. **L6, ASOCA. Recommended: not now.** It is one centre and one scanner ("all data has been collected from one
   medical centre", Gharleghi et al., CMIG 97:102049, 2022, doi:10.1016/j.compmedimag.2022.102049), with binary labels
   and 40 + 20 cases. The pool's 26 sources already test multi-source shift. No request is drafted (D31).
4. **The final retrain on train + val + open. Recommended: not yet, and not with D35.**
   - A retrain that includes val 80 and D35 leaves no decision set: the final model could then be judged only by the
     seal's single look (A19) and the sealed 80.
   - Revisit after wave 2, as a from-scratch run on everything except the seals, with the warm Janus line as its
     paired control on the seal.

## 10. Evidence index (new this round; citations checked 2026-10-25)

| Claim | Evidence |
|---|---|
| Pool accounting on real patients; the draw; serve positions | [[Atlas - On real patients 61 primary pool patients sit outside the seal and its reserve, so the D35 decision set is 35 of them, in two tranches]] |
| Paired noise is per case; MDE table; A22′ | [[Atlas - Run-to-run noise in both measured pairs is per case, so a 35-patient decision set resolves about 0.02-0.035 tF1 and A22's 0.013 overstates it]] |
| Seal power on Janus 0's spread; A31.1′ | [[Atlas - On Janus 0's own spread the 150-patient seal passes a human-level model 0.79 of the time if reads vary independently of the model, and more if hard cases are shared]] |
| Anchoring fails D6; the seed flag misses it; precision–recall detects it; width is invisible to tF1 | [[Atlas - Seed-anchored reads can fail a human-level model under D6, and the A31.2 seed flag does not see it]] |
| Fine-tune ≥ scratch, robust to small data | Tajbakhsh et al. 2016, IEEE TMI 35(5):1299–1312, doi:10.1109/TMI.2016.2535302 (abstract) |
| Fine-tuning on a new domain forgets; rehearsal fixes it | Karani et al. 2018, MICCAI, LNCS 11070:476–484, doi:10.1007/978-3-030-00928-1_54; González et al. 2023, Sci Rep 13:9381, doi:10.1038/s41598-023-34484-2, Fig. 4, Tables 1–2; Perkonigg et al. 2021, Nat Commun 12:5678, doi:10.1038/s41467-021-25858-z, Fig. 1b; Kirkpatrick et al. 2017, "Overcoming catastrophic forgetting in neural networks", PNAS 114:3521, doi:10.1073/pnas.1611835114 |
| 50–50 replay | Rolnick et al. 2019, NeurIPS, arXiv:1811.11682 (RL setting) |
| Nondeterminism ≈ seed variation; data sampling dominates | Summers & Dinneen 2021, ICML, arXiv:2103.04514 (abstract); Bouthillier et al. 2021, MLSys, arXiv:2103.03098, §2; Dodge et al. 2020, arXiv:2002.06305, Table 3 |
| Paired sample size | Julious 2004, Stat Med 23:1921, doi:10.1002/sim.1783, §2.2.2, eq. 2.10 |
| Rankings depend on the case sample | Maier-Hein et al. 2018, Nat Commun 9:5217, doi:10.1038/s41467-018-07619-7, Fig. 4 |
| Label noise sources include inter-observer variability and computer-generated labels | Karimi et al. 2020, Med Image Anal 65:101759, arXiv:1912.02911, Fig. 1 (medical image annotation in general) |
| Anchoring and pre-annotation bias | Tversky & Kahneman 1974, Science 185:1124, doi:10.1126/science.185.4157.1124; Fort & Sagot 2010, LAW IV, ACL W10-1807, §4.3; Constantinou et al. 2025, Clin Oncol 37:103660, doi:10.1016/j.clon.2024.10.032 (abstract) |
| TotalSegmentator coronary seed: a separate licensed subtask; DSC 70.5 ± 6.2 against ImageCAS-X | Wasserthal et al. 2023, Radiol AI 5:e230024, doi:10.1148/ryai.230024 and its README (`-ta coronary_arteries`, model changed at v2.12.0); arXiv:2608.30404, Table 2 (version not stated) |
| ASOCA is one centre | Gharleghi et al. 2022, CMIG 97:102049, doi:10.1016/j.compmedimag.2022.102049 |

Not cited, and why: nnU-Net Revisited (arXiv:2404.09556) reports fold-to-fold SD (Fig. 1), not seed variance, so it
is not used for A22′.

## 11. Changes since v11

- Janus 0 read (#43). The recipe, A15 and P2 are closed as pre-registered.
- **D35 drawn**, outside the seal and its reserve, with two pre-registered tranches. #43's count corrected.
- **Seal re-powered** on Janus 0's spread. A31.1′ sizes it on the measured contrast.
- **Janus 1 recipe:** warm fine-tune with ImageCAS-X replay, three runs, pre-registered J1–J7. From scratch is costed
  and deferred.
- **A22′:** the measured pairs put run-to-run noise inside the case CI. The a1/a2 replicate tests this on the master.
- **Anchoring:** quantified on phantoms with the pinned metric. A31.2's flag is shown not to detect it; A31.2′ adds
  the precision–recall test.
- The Job B, ensemble and 500-epoch items of v11 are gone (D28, A25).
