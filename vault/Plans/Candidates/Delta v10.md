---
tags: [plans, candidate, round10, fir, four-class, janus, D35, D27, A10, A31, A22, seed-anchoring, tree-f1, ostium]
author: Delta
round: 10
version: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Delta v10: decide on 35 patients that look like the seal, size the seal on the contrast A10 actually tests, and measure the seed's extent before any read, because extent, not width, is what anchored reads would make A10 measure

## 0. Improve or start again?

**Improve.** Round 9 adopted P1 (Dice decides nothing, A28) and tested P2 on CPU (A29). P2 failed by 0.0079 on val and is closed. It refused my 60-patient seal as under-powered. That refusal was right: I had sized a per-class A10 contrast with a macro paired SD. This version keeps Janus 0 and the recipe (settled), sizes everything on Janus 0's own numbers, and uses the right quantity for each question:
- for A10, the per-class contrast d = model-vs-read − inter-read;
- for fine-tune decisions, the macro paired difference with A22's seed term.

New evidence this round (CPU; code in `experiments/Delta/r10/`; no sealed case opened):
- [[Delta - After the seal and its reserve only 61 primary pool patients are free, 43 from one source, so a decision set with the seal's source mix must come from the reserve]]
- [[Delta - On Janus 0's own spread a 150-patient seal passes a human-level model 80 percent of the time, and the reads' correlation matters more than f or k]]
- [[Delta - If reads keep a seed's extent, A10 fails a model that is exactly ImageCAS-X, through precision alone, while a one-voxel width difference costs almost nothing]]
- Three tools for the lead to run on Fir, all self-tested:
  - `seed_vs_icx.py` (Job S): the seed's extent against ImageCAS-X on val 80;
  - `ostium_residual.py`: the P2 residual;
  - `repower_contrast.py`: the seal re-power on the measured contrast.
- An external citation check: `experiments/Delta/r10/citations.md`. Every item was opened at source; four were reworded or dropped.

**Independent agreement.** Crucible v11 and Foxtrot v6 (merged before this PR) reached the same pool counts (235 / 161 / 61) and a similar seal power (0.76–0.80 at 150), each with its own code. I read them only after my numbers were in; §11 lists where we differ.

## 1. The plan in one paragraph

**Keep Janus 0 and its recipe.** Freeze a **35-patient D35 decision set** now. Draw it from the 161 non-sealed primary patients, with each source's share equal to its share of the seal's population, so that decisions are made on patients who look like the acceptance set.

**The seal stays at 150 until wave 1 measures the contrast A10 tests.** Then it grows to the smallest of 175 / 200 / 228 that gives a human-level model at least 0.80 power. The ceiling is 228 because D35 takes 23 reserve patients; changing D27's 250 is the lead's question (§10, Q1).

**Janus 1 is a warm fine-tune of Janus 0** (A17a) with ImageCAS-X replay (#116/#118):
- three runs: LR 1e-2 twice (D28's second seed on the control) and LR 1e-3 once; about 45 Fir GPU-h;
- adopted only if it beats Janus 0 on D35 **and** does not fall below Janus 0 on val 80.

**Before any read:**
- run TotalSegmentator's coronary model on val 80 and measure how far the seed's extent departs from ImageCAS-X's (**Job S**, ≤ 1 GPU-h). If reads keep the seed's extent, that gap is what A10 on the pool will measure (§5).
- re-power the seal on Janus 0's exact per-case file (**Job R**, CPU).

## 2. The D35 decision set

### 2.1 Counts, reconciled (`pool_census.py`)

| Count | Patients | Note |
|---|---|---|
| "About 347" (D35, Atlas on #43) | 517 − 170 | Name-rule keys before D32, not patients |
| Real patients in the pool | 468 | 311 primary, 83 ImageCHD, 74 spacing-suspect |
| Non-sealed, non-ImageCHD | **235** | 161 primary + 74 spacing-suspect. **D35's 15 % of this = 35** |
| The wave-1 note's "198 open" | 198 | 61 primary + 63 ImageCHD + 74 spacing-suspect: correct, but mostly not A10's population |
| Primary: sealed / reserve 1–50 / reserve 51–100 / free | 150 / 50 / 50 / **61** | The free 61 are Taiwan 43, SDN-cy54 8, EpicardialFat 5, VMR 4, Kaggle-CAD 1. 17 of the 22 primary sources have **no** free patient |

### 2.2 The rule (proposed; frozen before any read of these patients is looked at)

| | Value |
|---|---|
| Eligible | The 161 non-sealed primary-stratum real patients (`segtrain.pool_seal.ingest_patient`). ImageCHD is out by D35, ImageALCAPA by D29, and the spacing-suspect sets because a mm tolerance on a wrong grid means nothing |
| Size | **35 patients** (51 volumes) |
| Allocation | Proportional to each source's share of the **primary pool**, which is the seal's own population; largest remainder; capped by availability; ≥ 1 patient for any source with ≥ 5 |
| Draw within source | Ascending `sha256('asclepius-decision-round10-pool:' + patient)` |
| Scored volume | One per patient, the lowest by the same hash. A patient with several volumes counts once |
| File | `experiments/Delta/r10/d35_decision_set_proposal.json`, sha256 `1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1`. The adopted file is copied to `configs/segqueue14/` and pinned by #116/#118 |
| Drawn | Taiwan 11, SDN-cy54 5, EpicardialFat 4, VMR 4, Kaggle-CAD 3, CardiacCT15 2, RIDER 2, TotalSegmentator-cardiac 2, HeartSR 1, SLAWT 1. Of these, 12 are free, 11 are reserve 1–50 and 12 are reserve 51–100 |

**Why from the reserve, and why the seal's mix?**
- A set drawn from the free 61 is 70 % Taiwan, and so is the training data. A fine-tune that overfits Taiwan would win there and lose at acceptance.
- The seal is proportional to the primary pool, so the decision set should be too.
- Crucible (#116) draws 35 with allocation proportional to the eligible 161 instead. The two differ by one or two patients per source, and either serves.

**Interaction with A30's extension order.** The order is kept and **skips D35 patients**, as D32 skipped sealed ones. 78 entries remain, so the seal can grow to **228**. The remaining reserve stays untrained and uninspected until the seal is sized (#114).

**What D35 is used for:**
- Janus 1 against Janus 0 (a fixed baseline);
- fine-tune arm choices;
- the wave-1 measurements of A31 (with the free patients).

Its reads are **never trained on**, and no image or per-case error list of a D35 patient is opened for tuning: decisions read only the pre-registered paired statistics.

### 2.3 What 35 patients buy (`power_r10.py`; macro tF1, 80 % power, two-sided 0.05)

The paired SD is 0.041. That is the real per-case SD of the difference between two retrained models on val 80 (atlas2 B − run 1).

| n | Case term only (fixed predictions, e.g. vs Janus 0) | A22, one seed per arm | Two seeds per arm |
|---|---|---|---|
| 25 | 0.023 | 0.043 | 0.035 |
| **35** | **0.019** | **0.041** | **0.032** |
| 50 | 0.016 | 0.040 | 0.030 |

Going from 35 to 50 buys 0.001–0.003. A second seed buys 0.009. If the pool is 1.5× more varied (f = 1.5), every entry rises by up to 0.010. **D35 is limited by seed noise, not by its size.**

## 3. The acceptance set (D27, A30, A31.1)

### 3.1 Re-powered on Janus 0

Janus 0's per-case val file is on Fir. Here a surrogate stands in for it: run 1's per-case shape, scaled per class to Janus 0's mean and to the SD implied by its CI. That gives SDs of LM 0.121, LAD 0.126, LCx 0.135 and RCA 0.079; run 1's were about 0.08. Bridge's simulation is unchanged, and on run 1's spread the same code gives 0.97 at 150.

**P(all four classes pass A10 | the model is exactly as good as a second reader):**

| Scenario | 150 | 175 | 200 | 228 | 250 |
|---|---|---|---|---|---|
| f = 1, k = 1, ρ = 0 (Bridge's model) | **0.80** | 0.88 | 0.93 | 0.96 | 0.98 |
| f = 1.2, k = 1, ρ = 0 | 0.56 | 0.67 | 0.77 | 0.84 | 0.88 |
| f = 1, k = 1, **ρ = 0.3** | **0.95** | 0.97 | 0.99 | 0.995 | 1.00 |
| f = 1.2, k = 1, ρ = 0.3 | 0.80 | 0.87 | 0.92 | 0.96 | 0.98 |

- LCx binds first (0.905 at 150 in the base case).
- Here ρ is the per-patient correlation between model-vs-read and inter-read tF1. Bridge's model sets it to 0. If the patients that are hard for the model are also hard for two readers (poor contrast, a tiny LM), then ρ > 0.
- At ρ = 0.3, 150 patients are as good as 228 patients at ρ = 0. **The one unmeasured number decides the seal size, and wave 1 measures it directly.**

### 3.2 The rule (proposed amendment to A31.1; the judge's call)

**When wave 1 has scored ≥ 60 primary patients**, score the D35 set and the free patients for Janus 0 against the reads. Then run `repower_contrast.py` on Bridge's `per_volume.jsonl`. It:
- takes, per class and per patient, d = model-vs-read − inter-read (unflagged, volumes averaged);
- **weights patients to the seal's source mix**, so a wave that is 70 % Taiwan does not size the seal alone;
- resamples d (centred at 0 = human level) at n = 150 / 175 / 200 / 228;
- reports ρ and SD(d), with patient-bootstrap CIs.

**The seal size** is the smallest n whose **lower 80 % bootstrap bound** of P(pass) is ≥ 0.80. If none reaches it, the result is reported to the lead.

**Why replace the f/k > 1.2 trigger?**
- It fires by chance 54 % of the time at 50 patients (Bridge's own `trigger_false_alarm.py`).
- It cannot see ρ.
- It is measured on whatever source mix wave 1 happens to have.

Until the judge rules, A31.1 runs as written and both results are reported.

**The extension happens before any sealed read is scored (A31.1).** The released reserve, the entries the seal did not take, becomes training data at that point.

**Not extending now.** Extending to 200 on the ρ = 0 assumption would spend 50 training patients, from sources that have no other training data, against a risk one measurement can remove. Foxtrot v6 extends now; §11 gives the contrast.

## 4. Janus 1: the pool fine-tune recipe

### 4.1 Warm fine-tune, with ImageCAS-X replay

| | Warm fine-tune (A17a, Atlas F3) | From scratch on ImageCAS-X + pool (Crucible P3/P4) |
|---|---|---|
| GPU-h per run | ≈ 15: 250 epochs × 192 s measured on Janus 0 = 13.3 h, + plan/preprocess ≈ 0.3 h, + prediction ≈ 0.5 h | ≈ 60: Janus 0's 54 h of training + preprocessing + prediction |
| A22 runs for one decision | 3 (below) | ≥ 4 (two seeds per arm for an effect < 0.02) |
| Total | **≈ 45** (range 40–55; ceiling 3 × 23.6) | ≈ 240 |
| What D35 can tell apart | ≥ 0.032 with two seeds | the same, so it cannot see the gap between the two either |

**Why warm:**
- The new data are small. There are 49 trainable primary patients now, plus 63 ImageCHD; with the reserve released, up to 127 primary. That is against 560 ImageCAS-X cases.
- From scratch would mostly re-learn Janus 0 at four times the cost.
- From scratch is the right shape for the **final** retrain (§10, Q4), once all reads exist and the recipe is fixed.

**Why replay.** Training on new data alone erases the old task:
- fine-tuning dropped the old structure's Dice from 96.7 to 0.1, while replay or distillation kept 95.9–96.3 (Ozdemir et al., arXiv:1806.00265, Table 1);
- sequential fine-tuning across segmentation domains forgets (González et al., arXiv:2010.11008, Figs. 5–8);
- rehearsal across scanners keeps old domains (Perkonigg et al., Nat Commun 12:5678, doi:10.1038/s41467-021-25858-z, Table 2). Even their naive random memory forgot a little (BWT −0.011).

So the training set is ImageCAS-X train 560 (collapsed by `territory.py`), plus every allowed pool read as its own sample (A11′). Fold-0 val is ImageCAS-X val 80, and no pool read is held out by `segtrain index` (#116 item 3, #118 (c)).

**LR arms (A17a/b).**
- The 1e-3 arm is kept because full fine-tuning can cost out-of-distribution accuracy (Kumar et al., arXiv:2202.10054).
- On brain MRI, a 1e-3 peak beat 1e-2 consistently (Wald et al., arXiv:2410.23132, Table 3).
- nnU-Net fine-tunes need a warm-up (Ulrich et al., MultiTalent, arXiv:2303.14444, Methods). The A17 trainer has one (2500 iterations).

### 4.2 Three runs, because D28's fallback is binding

D28: "A22's fallback stands: the first retrained decision adds a second seed to its control." Janus 1 is that decision. So:

| Run | Arm | Seed | Role |
|---|---|---|---|
| F1 | primary, peak 1e-2 | 1 | Control |
| F2 | primary, peak 1e-2 | 2 | D28's second seed of the control. It also gives the first measured σ_seed for warm fine-tunes |
| F3 | lr1e3, peak 1e-3 | 1 | A17b arm |

nnU-Net does not fix its seeds, so two runs of one arm in separate runs roots are two seeds.

### 4.3 How Janus 1 is read (pre-registered)

Scoring:
- **D35:** each fine-tune against each read, A1 ostium (TotalSegmentator aortas from Job P0), decisive tF1, paired by patient against Janus 0 on the same reads;
- **val 80:** paired against Janus 0, as in A26;
- **open-36:** confirmation.

The SE includes A22's seed term. σ_seed is the measured F1−F2 SD if it is available, else 0.013.

| Rule | Then |
|---|---|
| (a) The arm beats Janus 0 on D35 (macro, CI excludes 0), **and** (b) val-80 macro Δ ≥ −0.01 at the lower 95 % bound, **and** (c) no class drops > 0.03 on D35 or val 80, **and** (d) FP ≤ 1 per case on val (A15) | The arm is a Janus 1 candidate |
| Both arms pass | The higher D35 point estimate wins. If they are within 0.032 (D35's MDE with two seeds), lr1e3 wins: it moves less from Janus 0 (Kumar; Wald) |
| (a) passes but **D35 recall falls while precision rises**, or val-80 recall falls | It may have learned the seed's extent (§5). Not adopted until A31.2 and Job S have been read. To the lead (L5) |
| No arm passes (a) | Janus 0 stays the model. Wave 2 reads are added, and the comparison is re-run with the same rules |
| (b) fails | The fine-tune forgot ImageCAS-X. Re-run with replay doubled (ImageCAS-X sampled 2:1) before any other change |

The winner is read as **Janus 1** (D34).

### 4.4 When wave-1 reads are sufficient to start (pre-registered)

1. #114, #116 and #118 are merged, D35 is frozen and guarded, and Job P0 is done.
2. ≥ 30 of the 35 D35 patients have two approved reads. 30 rather than 35 costs about 0.002 of MDE.
3. ≥ 40 trainable primary patients have two approved reads (≥ 80 read samples), not counting ImageCHD. Below this the fine-tune is mostly replay, which is my judgement, not a measurement.
4. The seal size is fixed (§3.2), so the reserve is either sealed or released for training.

If condition 4 is not met when 1–3 are, start anyway: train without the reserve, and fold it in at wave 2.

## 5. What seed-anchored team reads measure (A31.2, L5), and the domain check (A31.3/A31.4)

### 5.1 Width versus extent: a CPU simulation on the 80 val references

[[Delta - If reads keep a seed's extent, A10 fails a model that is exactly ImageCAS-X, through precision alone, while a one-voxel width difference costs almost nothing]] (`anchoring_sim.py`, pinned tF1; ostia from ImageCAS-X start points so a trim never moves an ostium).

**The setup:**
- "Truth" is ImageCAS-X collapsed by D25.
- **Independent reads** each trim every distal tip by their own 0–8 mm.
- **Anchored reads** keep a seed that stops L mm short of every tip, and trim 0–2 mm more.
- Model **M0** is ImageCAS-X exactly. **M1** is ImageCAS-X thinned to Janus 0's measured volume ratio (0.87) with the centreline kept.

**Result** (the full table is in the note; RESULT_PLACEHOLDER):
- A one-voxel width difference, whether the model is thinner (M1, Janus 0's 0.87 volume ratio) or the reads are one voxel wider, moves A10's contrast by **≤ 0.012** in every class. tF1 is centreline-based. **Janus 0 drawing the lumen about one voxel inside ImageCAS-X's does not matter for A10.**
- **Extent does.** Anchored reads agree with each other almost perfectly: inter-read 0.99–1.00 whatever L is. A model that is exactly ImageCAS-X loses **precision** past the reads' distal ends, and its recall stays 1.0.
- With a seed only **5 mm** short of ImageCAS-X's extent, d is already **−0.045 to −0.068** per class (LAD, LCx, RCA). That is at or past D6's −0.05 margin.
- At 10 mm, d is −0.08 to −0.13; at 20 mm, −0.15 to −0.29. The LCx, a third side branch, is worst.
- A10 on anchored reads would then **fail a perfect model**, and reward a model that learned the seed's extent.

**What reads redrawn from a seed would follow.**
- **Width:** whatever the reader leaves. D12 allows redrawing to the contrast-filled lumen, but tF1 does not see width.
- **Extent:** the seed's, unless the reader extends it.
- Starting from a machine contour is known to reduce inter-observer variation: by 54.5 % (Lin et al., Radiology 2019, doi:10.1148/radiol.2019182012, abstract), and seminal vesicles 0.83 vs 0.73 (Palazzo et al., phiRO 2023, doi:10.1016/j.phro.2023.100501, abstract). That is exactly the inter-read inflation above.
- I found no study showing that edited contours end up nearer the machine's than the truth's. **Anchoring is a hypothesis this plan measures, not a fact.**

### 5.2 Job S: the seed's extent on ImageCAS-X, before any read (≤ 1 GPU-h)

- Run TotalSegmentator 2.18.0 `coronary_arteries` (the D23 seed model; `tools/ccta/totalseg_cpu.py`) on the 80 val CTs on Fir.
- Then run `seed_vs_icx.py`. It names the seed with ImageCAS-X's classes (nearest voxel), drops components more than 2 mm from ImageCAS-X (a reader deletes them whole), and scores per class, with ImageCAS-X as reference and the A1 ostium:
  - **recall:** how much of ImageCAS-X's extent the seed reaches;
  - **precision:** how much seed lies beyond it;
  - **Janus 0 against the named seed:** what a fully anchored read would cost Janus 0 on in-domain cases.

**It gives three things:**
1. **The size of L5's risk before any read exists.** A seed recall of 0.95 or more in a class means anchoring cannot cost more than about 0.03 there (the 5 mm row above). Below 0.90, A10 on that class is at risk.
2. **A reading for A31.2's seed flag.** The simulation shows the flag (seed-vs-read ≥ inter-read − 0.02) fires **without any anchoring** when the seed is within about 5 mm of the truth's extent. Seed-vs-independent-read was 0.96–0.99 there, against an inter-read of 0.95–0.98. The flag means anchoring only if Job S shows the seed is clearly short (Bridge's own caveat, wave-1 note §4.2).
3. **The in-domain baseline for the A31.4 domain check.** Per source, Janus 0 against the seed is only readable as domain shift relative to its value on ImageCAS-X's own val. Like Atlas's Dice-row check, it reports 1-voxel-tolerant Dice and the volume ratio beside plain Dice (`r10_dice_check.measure()`), so a uniform width difference is not read as shift.

### 5.3 What this asks of A10 on the pool (pre-registered; L5 stays the lead's)

| Job S + A31.2 | Then |
|---|---|
| Seed recall ≥ 0.95 in every class, or A31.2 shows reads extend the seed (median read voxels outside the seed ≥ 10 %) | A10 as written. The anchoring cost is below 0.03 |
| Seed recall < 0.95 in a class **and** A31.2 flags it | Report A10's contrast in that class split into its recall and precision halves. If the deficit is precision past the reads' distal ends, it is the seed's extent, not a model error. **L5 recommendation:** in such a class, acceptance also needs Janus N to be non-inferior to Janus 0 against ImageCAS-X on the sealed 80 (its one blind look, A26), within 0.05 per class |

### 5.4 Per-source shift (A31.3)

- Model-vs-read per source is reported with patient-bootstrap CIs and decides nothing (A31.3).
- Multi-institution coronary models lose accuracy across sites. Kim et al. (JMI 12(1):016002, found in Round 9) and Zhang et al. (JIIM 2025, ASOCA + GeoCAD) both show this.
- The 17 primary sources with no free patient have no training data. Their per-source rows are the out-of-distribution check.

## 6. The left-ostium residual behind P2's 0.0079 (report only)

**What is known (#43):**
- The gap is entirely in the left tree: LM +0.010, LAD +0.011, LCx +0.011; RCA identical.
- 4.3 % of val ostia are more than 2 mm from the expert start, and the CI's lower bound is 0. On open-36 the gap is exactly 0.

**Why it is worth one look:**
- It inflates Janus 0's per-case left-tree spread (macro SD 0.117 under A1 against 0.093 under the expert ostia).
- That spread feeds §3's power.
- If A1 roots a few left trees past the bifurcation, the same happens on pool reads, to both reads and the model.

**`ostium_residual.py`:**
- **Stage 1** reads the A29 run's own `delta_p2/per_case.jsonl` on Fir. It opens no image and lists the val cases carrying the gap and their share.
- **Stage 2** opens only those cases. For each one it reports:
  - the reference class at A1's left ostium (LM, or LAD/LCx past the bifurcation);
  - the geodesic distance from the expert start and the LM's length;
  - how many contact components the aorta has;
  - whether Janus 0's prediction covers the ostium of record.

Nothing is decided on it. If most carriers have an A1 ostium on the LAD/LCx, it goes to the judge as an A1b flag rule, "flag a left tree whose ostium of record lies past the first bifurcation", to be validated on open-36 (A26).

## 7. What results would change the plan

| Result | Where | Then |
|---|---|---|
| `power_r10.py --real` gives P(150, f = k = 1, ρ = 0) ≥ 0.90 | Job R | The seal is very probably 150. The wave-1 rule still decides |
| ... < 0.70 | Job R | Ask the lead now whether to seal 200 before wave 1 |
| Measured ρ ≥ 0.3 in every class | wave 1 | The seal stays at 150 (§3.1). 78 reserve patients are released for training |
| The contrast rule picks 228 and the power is still < 0.80 | wave 1 | Report to the lead: A10 cannot reach 0.80 on this pool. Accept with the shortfall stated, or change D6's reading (lead) |
| Job S seed recall < 0.90 in any class | Job S | L5 is live before wave 1. Put §5.3 to the lead now |
| Janus 1 fails rule (b) (forgetting) | Fir F1–F3 | Double the replay; nothing else changes |
| F1 − F2 shows σ_seed (fine-tune) ≥ 0.013 | Fir | Every later fine-tune decision runs two seeds per arm |
| No arm beats Janus 0 on D35 | Fir | Janus 0 stays; wave 2. From scratch is not tried before the final retrain |
| Ostium residual: carriers have A1 ostia past the bifurcation | Job R | An A1b flag-rule proposal to the judge; validated on open-36 |

## 8. The Fir jobs (for the lead; account `def-aso22`)

All GPU jobs: 1 × H100 SXM5 80 GB (`--gpus-per-node=h100:1`), 12 cores, partition by walltime, charged to `def-aso22_gpu`. Nothing here reads, writes or fetches a sealed case or a reserved volume.

### Job R: now, CPU on the login node (minutes, 0 GPU-h)

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo && git pull --ff-only      # after this PR is merged
# 1. the seal re-powered on Janus 0's exact per-case val tF1 (A31.1)
python experiments/Delta/r10/power_r10.py --real $SCRATCH/icx4/r9_tf1_val.json --out $SCRATCH/icx4/r10_power_real.json
# 2. the left-ostium residual (report only); stage 2 opens only the cases that carry the gap, val only
python experiments/Delta/r10/ostium_residual.py --rows $SCRATCH/icx4/delta_p2/per_case.jsonl \
  --icx $SCRATCH/icx4/icx --aorta $SCRATCH/icx4/aorta --pred $SCRATCH/icx4/predictions \
  --out $SCRATCH/icx4/r10_ostium_residual.json
```

If `delta_p2/` sits elsewhere, it is the `--out` folder of the A29 step in `r10_read_icx4.py` (the folder holding `SUMMARY.md` and `per_case.jsonl`).

**Send back** on #113: the printed tables of both runs. The JSONs carry case ids and numbers only, no image.

### Job S: the seed's extent on val 80 (before wave 1; ≤ 1 GPU-h)

TotalSegmentator's `coronary_arteries` needs the project's licence. It is the same licence the D23 seeds were made with, and it lives with the lead and never in the repository. The model weights download once on the login node.

```sh
# login node
module load StdEnv/2023 python/3.11.5
source $HOME/icx4-tseg-venv/bin/activate              # icx4's TotalSegmentator 2.18.0 venv
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg && mkdir -p $TOTALSEG_HOME_DIR $SCRATCH/seedcal/seeds
totalseg_set_license -l "<the project's TotalSegmentator licence key>"   # typed by the lead; never committed
C=$(python -c "import json;print(json.load(open('$SCRATCH/icx4/splits.json'))['val'][0])")
CT=$(python -c "import json;print(json.load(open('$SCRATCH/icx4/layout.json'))['cases']['$C']['ct'])")
TotalSegmentator -i $CT -o $SCRATCH/seedcal/seeds/$C.nii.gz -ta coronary_arteries --ml -d cpu   # one case: downloads the weights (a few minutes)
cat > $SCRATCH/seedcal/job.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=seedcal --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=02:00:00
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
python - <<'PY'
import json, os, subprocess
W = os.environ['SCRATCH'] + '/icx4'; out = os.environ['SCRATCH'] + '/seedcal/seeds'
val = json.load(open(f'{W}/splits.json'))['val']; ct = json.load(open(f'{W}/layout.json'))['cases']
for c in val:                                         # ImageCAS-X val 80 only (A26); no sealed case is in val
    o = f'{out}/{c}.nii.gz'
    if not os.path.exists(o):
        subprocess.run(['TotalSegmentator', '-i', ct[c]['ct'], '-o', o, '-ta', 'coronary_arteries', '--ml', '-d', 'gpu', '-q'])
print('seeds:', len(os.listdir(out)), 'of', len(val))
PY
EOF
sbatch $SCRATCH/seedcal/job.sh                        # about 30-60 min on one H100
# when it has finished: score on the login node (CPU, about 10 min)
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/Delta/r10/seed_vs_icx.py --seeds $SCRATCH/seedcal/seeds --icx $SCRATCH/icx4/icx \
  --aorta $SCRATCH/icx4/aorta --splits $SCRATCH/icx4/splits.json --pred $SCRATCH/icx4/predictions \
  --out $SCRATCH/seedcal/seed_vs_icx.json --np 10
```

**Check:** `seeds: 80 of 80`. **Send back:** the printed summary (per class: recall, precision, tF1, and Janus 0 against the seed against Janus 0 against ImageCAS-X), and `slurm-*.out` if it fails. Cost: ≤ 1 GPU-h (0 if the loop runs with `-d cpu` in a CPU job instead).

### Job P0: Janus 0 on the D35 and trainable pool volumes (after #116; about 2–3 GPU-h)

As specified in #116 items 4–5 (Crucible v11 §7 gives the same commands):
- fetch the non-sealed, non-reserved pool CTs;
- predict with Janus 0's `checkpoint_final.pth`;
- make TotalSegmentator aortas.

It is needed for the D35 baseline, the A31 measurements and the domain check. The commands are those of the #116 PR, which must print `refused: sealed N, reserved R` before any request.

### Jobs F1–F3: Janus 1 (when §4.4 holds; about 45 GPU-h)

These use task 716 v2 (ImageCAS-X replay, fold-0 val = val 80, D35 and reserve refused), as built by #116/#118. The commands follow `docs/TRAINING-WAVE1.md`; flag names are as on `dev` today.

```sh
# Girder host (the lead): export the approved reads; sealed reads are left out, D35 and reserved reads are refused later by the guard
segqueue14-export --out /srv/segqueue14/export-janus1 --replicas all
# Fir login node, after copying the export to $SCRATCH/janus1
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo && git pull --ff-only
segtrain index   --root $SCRATCH/janus1 --layout nested
segtrain convert --task 716 --zenodo-root $SCRATCH/janus1          # refuses any sealed, D35 or reserved read (#114/#116)
segtrain plan    --task 716 --zenodo-root $SCRATCH/janus1 \
  --plans-from $SCRATCH/icx4/nnunet_preprocessed/Dataset715_ICX4/nnUNetResEncUNetPlans_60G_iso05.json
segtrain preprocess --task 716
ICX4=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
segtrain scinet submit --task 716 --fold 0 --finetune-from $ICX4 --dry-run          # read: h100:1, 12 cores, def-aso22 (#118 (d))
segtrain scinet submit --task 716 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-f1           # F1: 1e-2, seed 1
segtrain scinet submit --task 716 --fold 0 --finetune-from $ICX4 --runs-root $SCRATCH/runs-f2           # F2: 1e-2, seed 2 (D28)
segtrain scinet submit --task 716 --fold 0 --arm lr1e3 --finetune-from $ICX4 --runs-root $SCRATCH/runs-f3   # F3: 1e-3
segtrain status --runs-root $SCRATCH/runs-f1                                         # expect about 190-200 s/epoch
```

**Cost:** 3 × about 15 GPU-h = **about 45** (range 40–55; ceiling 3 × 23.6 = 71). The three can run at once.

**When done:**
- predict val 80 and the D35 volumes with each model (#116 item 5);
- score D35 with `experiments/Bridge/wave1/score_wave1.py` (reading each fine-tune as `--pred`), and val 80 with `experiments/Atlas/r9_score_icx4.py --pair` against Janus 0;
- apply §4.3's table.

If #118's task id becomes 717, every `--task 716` above becomes `--task 717` and nothing else changes.

### Total

| Job | GPU-h | When |
|---|---|---|
| R | 0 | now |
| S | ≤ 1 | now (before wave 1) |
| P0 | 2–3 | after #116 |
| F1–F3 | ≈ 45 | after §4.4 |
| **All** | **≈ 48–50** | |

## 9. External evidence (all opened at source; `experiments/Delta/r10/citations.md`)

| Claim | Source | Fits our case? |
|---|---|---|
| Fine-tuning on a new task alone erases the old one; replay or distillation keeps it | Ozdemir et al., MICCAI 2018, arXiv:1806.00265, Table 1 (Dice 0.1 vs 95.9–96.3); Kirkpatrick et al., PNAS 2017, doi:10.1073/pnas.1611835114, Fig. 2 | Shoulder MR / MNIST, not CCTA. The direction is general |
| Sequential fine-tuning of segmentation across domains forgets | González, Lemke, Sakas, Mukhopadhyay, arXiv:2010.11008, Figs. 5–8 | Same task, new domains: our case |
| Rehearsal keeps old scanners; a random memory still forgets a little | Perkonigg et al., Nat Commun 12:5678, 2021, Table 2 discussion | Scanner shift ≈ our 26 sources |
| Full fine-tuning can lose out-of-distribution accuracy relative to linear probing | Kumar et al., ICLR 2022, arXiv:2202.10054, abstract | Classification. It supports keeping the 1e-3 arm, not a number |
| A 1e-3 peak beats 1e-2 for nnU-Net ResEnc fine-tuning; warm-up is essential | Wald et al., CVPR 2025, arXiv:2410.23132, Table 3 | Brain MRI, nnU-Net ResEnc: the same trainer family |
| nnU-Net fine-tuning with head then whole-network warm-up | Ulrich et al., MultiTalent, MICCAI 2023, arXiv:2303.14444, Methods | Our A17 trainer's design |
| Seed and data-order variance is the size of claimed improvements | Bouthillier et al., MLSys 2021, arXiv:2103.03098, Fig. 3 | A22 / D28: why F2 exists |
| A median CI width of 0.03, three times the median gap between first and second | Christodoulou et al., MICCAI 2024, arXiv:2409.17763, abstract | Why D35's 0.03–0.04 MDE is normal, not a defect |
| Rankings are unstable under test-set resampling | Maier-Hein et al., Nat Commun 9:5217, 2018, doi:10.1038/s41467-018-07619-7, Fig. 4 | Bootstrap CIs on every decision |
| Machine-generated labels are a named noise source | Karimi et al., MedIA 65:101759, 2020, Fig. 1 | The seed |
| Starting from a machine contour lowers inter-observer variation | Lin et al., Radiology 2019 (abstract); Palazzo et al., phiRO 2023 (abstract) | Radiotherapy contours. It predicts the inter-read inflation of §5.1, not its size |
| TotalSegmentator zero-shot DSC 70.5 ± 6.2 on ImageCAS-X; nnU-Net 89.8 ± 3.2; inter-observer LCx 84.8 | Bransby et al., ImageCAS-X, arXiv:2608.30404, Tables 1–2 | Same cases. The seed is far from the expert lumen, so anchoring is not benign |
| `coronary_arteries` is its own licensed TotalSegmentator subtask, not one of the 2023 paper's 104 classes | TotalSegmentator README (github.com/wasserth/TotalSegmentator) | Job S needs the licence; the 2023 paper is not cited for this model |

**Dropped after checking:**
- Tversky & Kahneman 1974: the quote was unverifiable.
- An "anchoring in contouring" study: none was found.
- A test-set-size claim attributed to Christodoulou et al.: it is not in the paper.

## 10. Decisions for the lead (through the PM)

1. **Q1 (D27): the seal's ceiling 228 instead of 250.** This is what drawing D35 with the seal's source mix costs. The power difference at f = k = 1 is 0.96 vs 0.98 (ρ = 0). **Recommended: yes.** The alternative keeps 250 and draws D35 from the free 61 only: about 12 patients, 70 % one source.
2. **Q2 (L5): if Job S and A31.2 show anchored extent in a class**, does acceptance in that class also require the sealed-80 ImageCAS-X look (non-inferior to Janus 0 within 0.05)? **Recommended: yes** (§5.3). No answer is needed until Job S is back.
3. **Q3: Job S** (≤ 1 GPU-h, the licence on Fir) and **Job R** (CPU). **Recommended: now.** They are the only items that can change the plan before a read exists.
4. **Q4 (final retrain on train + val + open):** **recommended later, from scratch, once.** Only after the D35-decided recipe is final and the pool reads are complete. It spends val 80, so nothing may be decided after it except the sealed looks.
5. **L6 (ASOCA): not now.** The pool's 17 untrained sources are the out-of-distribution check.

## 11. Where this differs from the other merged candidates (for the judge)

| Item | Delta v10 | Crucible v11 | Foxtrot v6 |
|---|---|---|---|
| D35 size and frame | 35 of the 161 | 35 of the 161 | 50 = extension ranks 51–100 |
| D35 allocation | the primary pool's (the seal's) mix | the eligible 161's mix | the extension order's |
| Seal | 150 until the measured contrast, weighted to the seal's mix; cap 228 | rule D on D35's contrast; default 200; cap 227 | 200 now |
| Janus 1 runs | 3 (D28's second seed on the control) | 2 ("not now: a second seed") | 2 |
| Before any read | Job S (seed extent on val 80), Job R | P0 | Job 1 (similar seed measure + domain check) |

**On the second seed.** D28 is binding: "the first retrained decision adds a second seed to its control". Janus 1 is that decision, so a two-run plan conflicts with D28 unless the lead says otherwise.

## 12. Code that must ship (`role:swe`, linked from #113)

No new issue. Delta v10 needs exactly what #114, #116 and #118 already specify:
- D35 freeze and guard;
- reserve refusal by patient, skipping D35;
- task 716 v2 with ImageCAS-X replay and val 80 as fold-0 val;
- pool fetch and inference;
- the Fir `h100:1` string.

The only Delta-specific inputs are the D35 file (this PR) and a reserve definition: the first N entries of the extension order **after skipping D35**, where N = the seal size minus 150 and is at most 78.

## 13. Changes since v9

- P2 is closed (A29), and so is my seal sizing (Round 9). The seal is now sized on Janus 0's spread and on the per-class contrast, with ρ.
- New: D35's size and draw; the seal rule on the measured contrast; Janus 1's three runs; Job S and the anchoring simulation; the ostium-residual tool.
- Dropped: my Fir aorta job (Round 9 found it redundant) and every Dice-based line (A28).
