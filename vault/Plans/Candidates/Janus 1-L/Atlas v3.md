---
aliases: [Janus 1-L Atlas v3]
tags: [plans, candidate, janus1-l, D45, D46, D49, trillium, four-class, round3, ensemble, locked100]
author: Atlas
track: 1-L
round: 3
updated: 2026-11-22
issue: christianGRogers/Asclepius#302
---

# Atlas v3 (track 1-L): not converged until Step T and Job 0 have run; everything else is ready for the round that reads their numbers

## In one paragraph

**The plan in force stands:** [[Candidates/Janus 1-L/Delta v2|Delta v2]] with L-A1 to L-A25, D46 and D49. D49 answers
Q-R2-1 to Q-R2-4 yes. So the candidate is E, Rule T runs on D60, D46 Q4 gains the Dice clause, and S runs on its
trigger without another round. I argued for a1 in round 2. That question is closed, and nothing below reopens it.

**Round 3 cannot rule the plan converged.** [[Janus 1-L Round 2]] §5 makes item 1 a precondition: Step T's and Job 0's
outputs must be on #302. They are not, because neither has run. So my answer is **"not converged, for item 1 alone"**.
Every other item is settled here, either outright or as a table that reads Job 0's numbers mechanically. Round 4 can
then be a reading round: it applies the tables to the posted numbers and proposes nothing new.

**What this version adds, in order of weight:**
1. **Eight defects in the plan of record's commands and interfaces** (§2), found by reading the merged scripts and
   nnU-Net 2.8.1's wheel, and checked on CPU here. Three would have stopped or changed the look:
   - the post-Job-0 block crashes before the decomposition at t\*: `'%.2f' % chosen_t` is given a string;
   - **`nnUNetv2_predict -f 0 1` is not E.** It averages logits, while `nnUNetv2_ensemble` averages probabilities.
     L-A14 says the two are equal. At t_C < 0.5 they draw different widths;
   - **L3 with L-A5's bootstrap bound false-alarms twice as often as its stated 3–8 %**: 8.1–13.8 % on the measured
     heavy-tailed differences, at the same power. The gate must use the t bound that rate was measured with.
2. **A tested reference implementation of `collect`'s gate** (`experiments/Atlas/j1l_r3/gate.py`). It covers L-A16's
   five verdict rows with D49 Q-R2-3, L3 with its t bound, the share sentence, G5, the S trigger (L-A18), and the
   looks ledger with a preflight that opens a look before any locked-100 score exists. Its self-tests are L-A21's
   test 9 and more (§6).
3. **§5 item 3, S's form, measured.** A 0.45 mm S keeps Janus 0's network and its 256³ patch, so its view shrinks to
   115.2 mm. On the 620, the LAD-centred patch loses the LM often enough to fail the check, which was pre-registered before its first run (LAD → LM 0.985 → 0.938; whole tree in one patch 0.97 → 0.78). **So S is 0.5 mm, whatever Job 0 shows** (§3).
4. **§5 items 4 and 5 as decision tables** (§4, §5), so Job 0's and Step T's outputs settle them without a round.
5. **#306's command block, final against the merged scripts**, with every interface read and self-tested (§6). The
   one consolidated plan text is Appendix A (§5 item 7).

**Cost:** unchanged at ≈ 33–35 GPU-h. Moving Janus 0's D60 pass into Job 0 (§7) adds nothing, because it moves
≈ 1 GPU-h from the predict job. S stays at +≈ 53 GPU-h, since it is 0.5 mm (§3).

## 0. Convergence: the seven items of Round 2 §5

| § 5 item | Status in Atlas v3 | What settles it |
|---|---|---|
| 1. Step T and Job 0 have run, outputs on #302 | **Not settled.** Neither has run | The lead runs them (D46 Q1, Q2). **This alone keeps round 3 from ruling converged** |
| 2. The lead's answers to Q-R2-1 to Q-R2-4 | **Settled.** D49: yes to all four | — |
| 3. S's form | **Settled** (§3): 0.45 mm needed an L-A23 grid row **and** the 115 mm view check. The check fails on the 620 (LAD → LM 0.938 < 0.95), so **S is 0.5 mm** | — (Job 0 no longer bears on it) |
| 4. Calibration | **Settled as a rule** (§4): a temperature fit is a report. Rule W is re-run on calibrated probabilities only if the real-data family mismatch is ≥ 0.02 | Job 0, and `calib.py fit` if its L-A23 row fires |
| 5. Class-weighted CE in Janus 0's run | **Settled as a rule** (§5): the fine-tune takes the weights that were active in Janus 0's last chunk, from the logs | Step T's `grep` |
| 6. #306's commands | **Settled except one reading** (§6). The commands, interfaces and gate are final. Still open: the decomposition reading (L-A22) on the posted numbers, and #306 itself, which is built after convergence | Job 0's decomposition summaries |
| 7. One consolidated plan text | **Settled** (Appendix A) | — |

**Recommendation to the judge:** rule "not converged (item 1)". Adopt §2's fixes and §3–§6's tables as amendments now.
Then round 4 has one job: read the posted numbers through L-A23 and the tables here, and rule.

## 1. What D49 settles, and what it leaves

| D49 | Effect |
|---|---|
| Q-R2-1 (a2 may be one of E's two members) | C = E at t_C (L-A14). My round-2 case for a1 is withdrawn. L-A19 holds: pool runs are member-wise |
| Q-R2-2 (D60 label-free) | Rule T runs (L-A15). Its reference, Janus 0 on D60, can run before training (§7) |
| Q-R2-3 (Q4 needs "Dice not shown worse") | The Q4 row adopts only if the 95 % upper bound of Δ whole-tree Dice is ≥ 0. Implemented and tested in `gate.py` |
| Q-R2-4 (S without another round) | S's trigger is evaluated by `gate.py --strigger` from the reports (§6.6). If it fires, the lead runs S at the form §3 fixes |

## 2. Defects in the plan of record (all checked here)

Every item was found by reading the merged script, or nnU-Net 2.8.1's wheel (downloaded and read, not installed),
and then checked on CPU. Each comes with a fix.

| # | Where | Defect | Evidence | Fix |
|---|---|---|---|---|
| **F1** | Master plan §5, "After Job 0", line 5 | `'%.2f' % json.load(...)['chosen_t']` raises `TypeError: must be real number, not str`. `decide.py select` writes `chosen_t` as the string `f'{chosen:.2f}'` (l. 77). So the decomposition at t\* never runs | Run here: `'%.2f' % '0.45'` → TypeError | `'%.2f' % float(...)` (Appendix A §5) |
| **F2** | L-A14 | "`nnUNetv2_ensemble` of the two folds' saved probabilities equals `nnUNetv2_predict -f 0 1`" is false. `predict` sums the folds' **logits** and divides (`predict_from_raw_data.py` l. 524–530). `ensemble` averages their **probabilities** (`ensembling/ensemble.py` l. 18–31). E is defined as the mean softmax | For two members and a foreground/background decision, the two agree **exactly at t = 0.5**: σ(a) + σ(b) = 1 iff a + b = 0. They differ at every other t. `calib.py tables`, at t = 0.40, with the mean-softmax E wider than the mean-logit E: by ≤ 0.008 mm for fold rims 0.2 mm apart, 0.013–0.063 mm for rims 0.5 mm apart, and 0.05–0.28 mm for rims 1 mm apart (rim logit slopes 2–8 per mm). That is up to half a voxel, where Rule W and Rule T work in steps of about 0.1 mm | E is made only by `nnUNetv2_ensemble`, for the look **and for every later prediction of the shipped model** (the 1000-case pass included). `-f 0 1` is never used for E. What ships is what was tested |
| **F3** | L-A21 `predict` | `nnUNetv2_ensemble` writes no probabilities unless given `--save_npz` (l. 46, 122). `threshold_export.py` then finds no `.npz` and exits | Code | `nnUNetv2_ensemble … --save_npz` |
| **F4** | Master plan §3 L0, §5 "Post" | L0's third clause (≥ 95 % of cases within 0.01 of Fir) is in neither block the lead is told to post. `paired` gives the mean difference and its CI, not the share of cases | `r9_score_icx4.py` `paired()` | `l0_check.py` reads `rows` and `rows_pair` and prints all three clauses, as counts only. Post its output |
| **F5** | L-A5, L-A17 (L3's upper bound) | L-A5 makes every bound a 10 000-resample bootstrap. L3's stated false-alarm rate (3–8 %) was measured with a t bound. On the measured heavy-tailed differences, the percentile bootstrap roughly doubles L3's false alarm, with no gain in power | `l3_null.json` (2000 replicates, B = 1000). Heavy λ = 0: **0.036 (t) vs 0.081 (bootstrap)**; λ = 1: 0.072 vs 0.113; λ = 3: 0.074 vs 0.138; Gaussian λ = 1: 0.178 vs 0.189. Power for a uniform −0.03 LCx loss is equal (1.000/1.000, 0.982/0.982, 0.944/0.947). Almost all of the excess comes from clause (b): the trimmed clause alone fires on ≤ 0.2 % of heavy nulls | **L3's clause (b) uses the t bound**, mean + t(1 − α, n − 1) · SD / √n. That is the one bound of the look that is not a bootstrap, and the stated rate then holds. `gate.py` does this |
| **F6** | L-A15, L-A21 `transfer` | Rule T reads C on D60 at **eight** thresholds (0.60 … 0.25), and Janus 0 on D60 at t\*. If t_C = 0.25, the report "Janus 0 at t_C" on the locked 100 needs an export Job 0 never made (Job 0 exported 0.50–0.30) | `rule_t.py` `GRID`, `_one` | The export commands in §6.4 |
| **F7** | L-A23, grid row | "Dice at t\* more than 0.03 below 0.934, **with volume ratio ≥ 0.95**". No Job 0 output holds a volume ratio: the scorer's rows have none, and `voxels.json` has predicted counts only | Read: `tf1_score.score_arrays`, `threshold_export.one` | `vol60.py` computes it on the tuning 60 and applies the row (§6.2) |
| **F8** | `collect`'s looks ledger (L-A21) | A ledger written by `collect` after scoring guards the verdict, not the look. The look is the scorer run on C's locked-100 exports, which comes first | Order of operations | `gate.py --preflight` checks the posted sha256 of `select.json` and `rule_t.json`, C's t, and the ledger, and opens the look **before** the scorer runs. The gate then closes it. A second preflight for the same model, or a third model, is refused |

**Checked and found right** (with their self-tests run here; Python 3.13, NumPy 2.5.3, SciPy 1.18.1, scikit-image
0.26.0):
- `threshold_export.py`: its axis order matches nnU-Net's saved `npz` order. An ensemble output passes its 99.9 %
  argmax check, because `ensemble` writes the segmentation as the argmax of the same mean.
- `decide.py select`: Rule W as written. Its keys are `'0.50'` and so on, which is what `rule_t.py dice_bound` reads.
- `rule_t.py`: its input layout (`<dir>/t<t>/<case>.nii.gz`) is `threshold_export.py`'s output layout. `t_C` is a
  float in `rule_t.json`, and the printed sha256 is that of the file's bytes.
- `mde_from_job0.py`: reads the `rows` of `locked100_janus0_argmax.json` and prints JSON only, so `> mde.json` works.
- `error_decomp.py`: refuses everything outside the tuning 60, and its R/P reproduce `tree_f1`.
- `r9_score_icx4.py`: `--set val --splits split_locked100.json` scores exactly the locked 100.

## 3. §5 item 3: S's form

### 3.1 The rule (pre-registered now; reads only Job 0's tuning-60 numbers)

The rule, as pre-registered. §3.2's measurement then fails (b), so S is 0.5 mm. S takes the **0.45 mm form** if and only if:
- **(a)** an L-A23 row that names 0.45 mm fires on Job 0's tuning-60 output. That is either:
  - "Dice at t\* more than 0.03 below 0.934, with volume ratio ≥ 0.95" (`vol60.py`'s `grid_binds`), or
  - "t\* = 0.50 with Dice peaking at 0.50";
- **and (b)** the 115 mm view check (§3.2) passes.

Otherwise S is **0.5 mm**: Janus 0's plans, its warm-start question only. The form is fixed when Job 0's numbers are
posted, so it is set before any training job, and on no locked-100 number. S itself still runs only on L-A18's
trigger.

### 3.2 The 115 mm view check, measured on the 620

`view045.py` runs on ImageCAS-X's segmentations of the 620 training cases, collapsed to four classes.
`fetch_train620.py` fetches exactly those 620 files, checks the L-A1 pin and refuses sealed or locked ids. It answers
three questions for a 256³ patch at 0.5 mm (128 mm) and at 0.45 mm (115.2 mm):
- **Does one patch hold the structure?**
- **Does nnU-Net's forced-foreground patch, centred on a voxel of one class, contain the evidence for its name**
  (LAD → LM and so on)?
- **What share of the image height does one inference window span?**

The pass rule was written in the script before its first run: round 1's 128 mm values, less 0.02.

| On the 620 | 128 mm (0.5 mm) | 115.2 mm (0.45 mm) | Rule |
|---|---|---|---|
| LAD in one patch | 1.000 | 0.998 | — |
| Left tree in one patch | 1.000 | 0.997 | ≥ 0.98 ✓ |
| Right tree in one patch | 0.998 | 0.994 | ≥ 0.97 ✓ |
| Whole tree in one patch | 0.974 | **0.784** | — |
| LAD-centred patch holds the LM (mean; 5th percentile of cases) | 0.985; 0.874 | **0.938**; 0.745 | ≥ 0.95 **✗** |
| LAD-centred patch holds the LCx | 0.994; 0.969 | 0.973; 0.808 | — |
| LCx-centred patch holds the LM | 0.996; 0.977 | 0.981; 0.875 | ≥ 0.97 ✓ |
| RCA-centred patch holds the LM | 0.998; 1.000 | 0.962; 0.511 | — |
| One inference window's share of the image height | 0.931 | 0.838 | — |
| Cases whose LAD → LM containment falls by > 0.05 | — | 195 of 620 | — |

Whole-tree extent (x / y / z): median 107 / 90 / 86 mm; p90 120 / 102 / 99 mm; max 145 / 115 / 122 mm. The p90 x
extent is above 115.2 mm and below 128 mm. Summary: `experiments/Atlas/j1l_r3/view045.json` (no per-case rows).

**The view check fails.**
- **LAD → LM** falls from 0.985 to **0.938**, below the pre-registered 0.95. For a third of the cases (195 of 620),
  more than 5 % of LAD-centred patches lose sight of the LM.
- **The whole tree** fits in one patch in 0.78 of cases, against 0.97 at 128 mm.

At 115 mm, the evidence for naming an LAD voxel (its LM origin) leaves the patch noticeably more often. The
0.45 mm form would buy lumen width, and pay for it in naming context. Whether naming is where Janus 0 loses tF1 is
for Job 0's decomposition to say, and either way the trade is not a warm-start fallback. The comparison at 128 mm on the 620 (0.985) agrees with round 1's 0.97 on 153
cases.

**So item 3 is settled outright: S is 0.5 mm, whatever Job 0 shows.** §3.1(a) is moot. §3.3–3.4 stay on record,
for a later round that would pair 0.45 mm with a larger patch (about 284³ for 128 mm, which is a new network and a
new cost, not S).

### 3.3 The 0.45 mm plans step (no fingerprint, no planner)

Janus 0's network is tied to its 256³ patch, not to its spacing. So the 0.45 mm form keeps everything except the
resampling target:

```sh
# on Trillium, after P (dataset 718 exists with Janus 0's moved plans), CPU
P=$(ls -d $nnUNet_preprocessed/Dataset718_*)          # #306 names the dataset
python - "$P" <<'PY'
import json, sys
P = sys.argv[1]
p = json.load(open(f'{P}/nnUNetResEncUNetPlans_60G_iso05.json'))
p['plans_name'] = 'nnUNetResEncUNetPlans_60G_iso045'
c = p['configurations']['3d_fullres']
assert c['patch_size'] == [256, 256, 256] and c['batch_size'] == 2 and c['spacing'] == [0.5, 0.5, 0.5], c
c['spacing'] = [0.45, 0.45, 0.45]
c['data_identifier'] = c['data_identifier'].replace('iso05', 'iso045') if 'iso05' in c['data_identifier'] \
    else c['data_identifier'] + '_iso045'
json.dump(p, open(f'{P}/nnUNetResEncUNetPlans_60G_iso045.json', 'w'), indent=1)
PY
nnUNetv2_preprocess -d 718 -plans_name nnUNetResEncUNetPlans_60G_iso045 -c 3d_fullres -np 10
```

- **The plans check** (#306's `check`) changes as follows:
  - the 0.45 plans equal Janus 0's once `dataset_name`, `image_reader_writer`, `plans_name`,
    `configurations.3d_fullres.spacing` and `data_identifier` are removed;
  - the network block (`architecture`), the patch, the batch and the intensity properties are identical;
  - a preprocessed case's shape is (0.5/0.45) ≈ 1.11× Janus 0's along each axis, ± 1 voxel.
- **Normalisation and the fingerprint are Janus 0's**, so S at 0.45 mm differs from Janus 0's recipe only in data
  (the 620) and spacing.
- `finetune_load` is not used, because S starts from scratch.

### 3.4 t\* and Rule T on the new grid, and cost

- **Rule T carries to 0.45 mm unchanged.** nnU-Net exports probabilities on each case's original grid, whatever the
  network's spacing. `threshold_export.py` and `rule_t.py` work on that grid, in mm (`distance_transform_edt(…,
  sampling=sp)`). So S's t_S is Rule T on S's own D60 probabilities against Janus 0 at t\*, as L-A18 says. No
  "t = 0.50" fallback is needed. If Rule T's scope clause applies (t\* was held by a guard), t_S = t\*.
- **Cost:**
  - **training:** the patch and batch are unchanged, so the step time is unchanged. 1000 epochs × 181 s ≈ 50 h plus
    overhead ≈ **53 GPU-h**, as at 0.5 mm;
  - **preprocessing:** ≈ 1.37× the voxels of 0.5 mm, on CPU and disk;
  - **inference:** ≈ 1.37× the sliding windows, about +0.5–1 GPU-h for the 160 cases.
  - **S at 0.45 mm ≈ 54–56 GPU-h**, against the judge's 55–60.

## 4. §5 item 4: calibration, if Job 0 gives t\* = 0.30, FP rising at every t < 0.50, or a guard-held t\*

**What a temperature can and cannot do.** Rule W picks one mask from the family {Σ vessel probability ≥ t}. A single
temperature T keeps every voxel's argmax, and it keeps the order of the foreground probability wherever one vessel
class dominates. So, on a straight vessel, the calibrated family is the **same masks met at other t**. Order can
change only where two vessel classes compete. `calib.py tables` measures that on a synthetic LM → LAD/LCx
bifurcation, at T = 0.7 and T = 1.5, for rim slopes of 2 and 4 per mm:
- **1–9 % of a mask's voxels** change between the mask at t and the calibrated mask of the same size;
- the share is largest for soft rims (2 per mm), and below 3 % for sharper ones.

So a temperature mostly re-labels Rule W's grid, but not entirely.

**The rule:**

| Job 0 shows | Then (CPU, before #306 freezes) |
|---|---|
| t\* = 0.30, Dice-bound (the grid edge) | Run `calib.py fit` (T by NLL in a 3 mm rim band on the tuning 60; the family mismatch at T = 0.7 and 1.5). **If the mean mismatch is < 0.02 at every t:** calibration is a report, and Rule W's grid is extended once, to {0.25, 0.20}, with the same guards, on uncalibrated probabilities. Rule T's grid already reaches 0.25. **If ≥ 0.02:** Rule W is re-run on probabilities tempered by T̂, Rule T is run on C's probabilities tempered by the same T̂, and the verdict says so |
| FP rises at every t < 0.50 (t\* = 0.50, guard-held) | The FP guard binds. Calibration cannot move FP at a fixed mask size, so `calib.py fit` is a report. t_C = t\* (L-A15 scope). The verdict expects the Q4 branch |
| t\* held by the recall or tF1 guard | t_C = t\* (L-A15 scope). The guard is named on #302. No calibration step |
| None of these | No calibration step |

The fit reads Janus 0's probabilities and ImageCAS-X labels of the tuning 60 only, both of which Job 0 already uses.
It refuses every other case, and it prints aggregates only.

## 5. §5 item 5: if Step T finds class-weighted CE in Janus 0's logs

**What the logs can show.** `nnUNetTrainerICX4._build_loss` reads `$W/ce_class_weights.json` each time a chunk of the
chain starts (`icx4_trainers.py` l. 29–39). It prints `ICX4: class-weighted CE from <path>: [w0, …, w4]` to that
chunk's `training_log_*.txt`. nnU-Net starts a new log file per invocation. So the logs say, chunk by chunk, whether
weights were on and what they were.

**The rule (by Step T's output, before P):**

| Step T shows | The fine-tune (a1, a2) | Why |
|---|---|---|
| `grep -c` 0 in every log | No weights (L-A21 as written) | — |
| Weights in the **last** chunk's log (the one that wrote `checkpoint_final`) | **The same five weights**, from that log line, set on `ce.weight` by `nnUNetTrainer_janus1l` exactly as `_build_loss` does. #306's self-test 6 asserts `ce.weight` equals them, not None | The fine-tune continues the loss Janus 0's final weights were trained under. A loss change would move the rim that Rule W chose t\* on. That makes Rule T's job larger, and "Janus 0's recipe on more data" (H1's reading) untrue |
| Weights only in **earlier** chunks | No weights | The checkpoint's last epochs were trained without them. The report states the weighted epochs |
| A log is missing for a chunk | Stop. The lead posts which chunk; the next round decides | The rule cannot be applied |

- **S is unaffected.** It is Janus 0's recipe from scratch, and takes the same weights on the same epochs only if
  Step T shows them, by the same table.
- This is **not** a recipe change, so no new D-number is needed. It keeps L-A2's "the same recipe".

## 6. §5 item 6: #306's commands, final against the merged scripts

### 6.1 Interfaces, read and self-tested here

| Script (merged unless marked) | Arguments | Reads | Writes | Self-test |
|---|---|---|---|---|
| `experiments/Crucible/j1l_r1/threshold_export.py` | `--probs D --out O --t t… --np n` | `D/<c>.npz` (`probabilities`, nnU-Net order) + `D/<c>.nii.gz` | `O/t<t:.2f>/<c>.nii.gz`, `O/voxels.json` | passed |
| `experiments/Crucible/j1l_r1/decide.py select` | `--scores t0.50=f …` | r9 JSONs | `select.json` on stdout, `chosen_t` a **string** | passed |
| `experiments/Atlas/r9_score_icx4.py` | `--pred --icx --aorta --layout --splits --set val --np [--pair]` | predictions, ImageCAS-X, aortas, CTs | `--out` JSON with `summary`, `rows` (+ `paired`, `rows_pair`) | passed |
| `experiments/Delta/j1l_r2/rule_t.py` | `--j0 --cand --select --out --np` | `j0/t<t*>/`, `cand/t<0.60…0.25>/` on D60 | `rule_t.json`; prints its sha256 | passed |
| `experiments/Delta/j1l_r2/mde_from_job0.py` | positional: `locked100_janus0_argmax.json` | its `rows` | JSON on stdout | read |
| `experiments/Bridge/j1l_r2/error_decomp.py` | `--pred --icx --aorta --layout --np --out` | tuning 60 only | JSON (`summary`, `rows`) | passed |
| `experiments/Atlas/j1l_r3/l0_check.py` (this PR) | positional: `identity_val80.json` | `summary`, `rows`, `rows_pair` | three clauses, counts only | passed |
| `experiments/Atlas/j1l_r3/vol60.py` (this PR) | `--thr --icx --select --np --out` | tuning 60 only | volume ratio per t, and the L-A23 grid row | passed |
| `experiments/Atlas/j1l_r3/calib.py fit` (this PR) | `--probs --icx --np --out` | tuning 60 only | T̂, NLL, ECE, family mismatch | passed (synthetic) |
| `experiments/Atlas/j1l_r3/gate.py` (this PR) | `--preflight` / gate / `--strigger` (§6.5) | r9 JSONs, `select.json`, `rule_t.json`, `l0.json`, mde | `gate.json`, `looks.json` | passed |
| `nnUNetv2_ensemble` (2.8.1) | `-i D1 D2 -o O -np n --save_npz` | `D*/<c>.npz` + `.pkl`, `D1/plans.json`, `D1/dataset.json` | `O/<c>.nii.gz` + `.npz` + `.pkl` | code read |

### 6.2 After Job 0 (replaces the master plan's block; CPU, login node)

```sh
source $HOME/icx14-venv/bin/activate
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0; A=$R/experiments/Atlas/j1l_r3
git -C $R pull --ff-only
python $A/l0_check.py $W/scores/identity_val80.json | tee $W/scores/l0.json          # post; stop unless "L0": true
T=$(python -c "import json;print('%.2f' % float(json.load(open('$W/select.json'))['chosen_t']))")   # F1
python $R/experiments/Bridge/j1l_r2/error_decomp.py --selftest
for t in 0.50 $T; do
  python $R/experiments/Bridge/j1l_r2/error_decomp.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --np 8 --out $W/scores/error_decomp_tuning60_t$t.json
done
python $R/experiments/Delta/j1l_r2/mde_from_job0.py $W/scores/locked100_janus0_argmax.json | tee $W/scores/mde.json
python $A/vol60.py --thr $W/thr --icx $J0/icx --select $W/select.json --np 4 --out $W/scores/vol60.json   # F7
```

**Post on #302:**
- `l0.json`;
- the two decomposition `summary` blocks;
- `mde.json`;
- `vol60.json`.

**Only if an L-A23 calibration row fires** (§4):

```sh
python $A/calib.py fit --probs $W/probs --icx $J0/icx --np 2 --out $W/scores/calib_tuning60.json
```

### 6.3 #306 `check`, `prepare`, `train` (as L-A21; commands of record)

#306 builds `trillium/janus1l/janus1l` with these modes. Its `prepare` and `train` run exactly the steps L-A21
lists. The lead's commands:

```sh
cd $SCRATCH/asclepius/repo/trillium/janus1l
./janus1l check        # self-tests 1-9 of L-A21 + the dry run; prints both sealed-list paths
./janus1l prepare      # dataset 718, Janus 0's plans moved, its fingerprint placed, preprocess only (≈ 1 GPU-h)
./janus1l train        # a1 and a2 concurrent, chained 23:50 jobs; ./janus1l status to follow
```

With §5's weights rule, `check` asserts `ce.weight` from Step T's log line, or None.

### 6.4 `predict` and `transfer` (one GPU job ≈ 3–4 GPU-h, then CPU)

What `./janus1l predict` and `./janus1l transfer` must run. Written against the merged scripts, so #306's
modes can be checked line by line:

```sh
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l; J0=$SCRATCH/janus0; JOB0=$SCRATCH/j1l_job0
TE=$R/experiments/Crucible/j1l_r1/threshold_export.py
TS=$(python -c "import json;print('%.2f' % float(json.load(open('$JOB0/select.json'))['chosen_t']))")
# inputs: the locked 100 and D60 only (refuses sealed, training or tuning ids)
python - "$R" "$W" "$SCRATCH/asclepius/cases" <<'PY'
import json, os, sys
R, W, C = sys.argv[1:]
L = json.load(open(f'{R}/experiments/Crucible/j1l_r1/lists.json'))
D = json.load(open(f'{R}/experiments/Delta/j1l_r2/drift60.json'))['drift60']
S = json.load(open(f'{R}/trillium/sealed_test.json'))
bad = (set(L['locked100']) | set(D)) & (set(S['sealed_icx_test']) | set(S['sealed_quality0']) | set(L['train620']))
assert not bad and len(L['locked100']) == 100 and len(D) == 60 and not set(D) & set(L['locked100']), bad
for name, ids in (('locked', L['locked100']), ('d60', D)):
    os.makedirs(f'{W}/in_{name}', exist_ok=True)
    for c in ids:
        dst = f'{W}/in_{name}/{c}_0000.nii.gz'
        if not os.path.lexists(dst):
            os.symlink(f'{C}/{c}/ct.nii.gz', dst)
PY
# GPU: a1 (fold 0) and a2 (fold 1), each fold separately (F2: never -f 0 1 for E); Janus 0 on D60
for s in locked d60; do for f in 0 1; do
  nnUNet_results=$W/nnunet_results nnUNet_compile=f nnUNetv2_predict -i $W/in_$s -o $W/probs/${s}_f$f \
    -d 718 -c 3d_fullres -f $f -tr nnUNetTrainer_janus1l -p nnUNetResEncUNetPlans_60G_iso05 \
    -chk checkpoint_final.pth --disable_tta --save_probabilities -npp 6 -nps 6 -device cuda
done; done
nnUNet_results=$J0/nnunet_results nnUNet_compile=f nnUNetv2_predict -i $W/in_d60 -o $W/probs/d60_j0 -d 715 \
  -c 3d_fullres -f 0 -tr nnUNetTrainerICX4 -p nnUNetResEncUNetPlans_60G_iso05 -chk checkpoint_final.pth \
  --disable_tta --save_probabilities -npp 6 -nps 6 -device cuda        # F0; if Job 0 ran it (§7), point d60_j0 there
# CPU: E as the mean softmax, with its probabilities (F2, F3)
for s in locked d60; do nnUNetv2_ensemble -i $W/probs/${s}_f0 $W/probs/${s}_f1 -o $W/probs/${s}_E -np 8 --save_npz; done
# transfer: Rule T on E; a1's and a2's as reports (F6: eight thresholds for each candidate)
python $TE --probs $W/probs/d60_j0 --out $W/thr/d60_j0 --t $TS --np 8
for m in E f0 f1; do
  python $TE --probs $W/probs/d60_$m --out $W/thr/d60_$m --t 0.6 0.55 0.5 0.45 0.4 0.35 0.3 0.25 --np 8
done
python $R/experiments/Delta/j1l_r2/rule_t.py --selftest
python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $W/thr/d60_j0 --cand $W/thr/d60_E --select $JOB0/select.json \
  --out $W/rule_t.json --np 8                                            # post the printed sha256 on #302
for m in f0 f1; do python $R/experiments/Delta/j1l_r2/rule_t.py --j0 $W/thr/d60_j0 --cand $W/thr/d60_$m \
  --select $JOB0/select.json --out $W/rule_t_report_$m.json --np 8 > /dev/null; done   # reports (L-A15)
```

**Post on #302:**
- `rule_t.json` and its sha256;
- `rule_t_report_f0.json`'s and `rule_t_report_f1.json`'s `dr_mm` only.

If a1 and a2 shift in opposite directions, the report says "seed noise", and nothing changes.

**Disk.** The `npz` of the locked 100 and D60 for two folds, plus E, is ≈ 3× Job 0's 160-case `probs`. Check
`diskusage_report` before the job. The `npz` may be deleted once `collect` has run.

### 6.5 `collect` (CPU; the one look)

```sh
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l; J0=$SCRATCH/janus0; JOB0=$SCRATCH/j1l_job0; A=$R/experiments/Atlas/j1l_r3
TE=$R/experiments/Crucible/j1l_r1/threshold_export.py
TC=$(python -c "import json;print('%.2f' % json.load(open('$W/rule_t.json'))['t_C'])")
SEL=<select.json sha256 as posted>; RT=<rule_t.json sha256 as posted>
python $A/gate.py --selftest
python $A/gate.py --preflight --name "Janus 1-L.1" --alpha 0.025 --cand-t $TC --select $JOB0/select.json \
  --select-sha256 $SEL --rule-t $W/rule_t.json --rule-t-sha256 $RT --ledger $W/looks.json      # F8: opens the look
python $TE --probs $W/probs/locked_E --out $W/thr/locked_E --t $TC --np 8
for f in 0 1; do python $TE --probs $W/probs/locked_f$f --out $W/thr/locked_f$f --t 0.5 $TC --np 8; done
python $TE --probs $JOB0/probs --out $W/thr/locked_j0 --t $TC --np 8                    # Janus 0 at t_C (F6)
SC="python $R/experiments/Atlas/r9_score_icx4.py --icx $J0/icx --aorta $J0/aorta --layout $JOB0/layout.json \
  --splits $JOB0/split_locked100.json --set val --np 20"
$SC --pred $W/thr/locked_E/t$TC  --out $W/scores/locked100_C.json > /dev/null           # the look
$SC --pred $W/thr/locked_j0/t$TC --out $W/scores/locked100_janus0_tC.json > /dev/null   # reports from here on
$SC --pred $W/thr/locked_f0/t0.50 --out $W/scores/locked100_a1_argmax.json > /dev/null
$SC --pred $W/thr/locked_f1/t0.50 --out $W/scores/locked100_a2_argmax.json > /dev/null
$SC --pred $W/thr/locked_f0/t$TC --pair $W/thr/locked_f1/t$TC --out $W/scores/locked100_a1_vs_a2_tC.json > /dev/null
python $A/gate.py --name "Janus 1-L.1" --alpha 0.025 --cand-t $TC --select $JOB0/select.json --select-sha256 $SEL \
  --rule-t $W/rule_t.json --rule-t-sha256 $RT --ledger $W/looks.json \
  --base $JOB0/scores/locked100_janus0_argmax.json --cand $W/scores/locked100_C.json \
  --j0-tc $W/scores/locked100_janus0_tC.json --mde $JOB0/scores/mde.json --out $W/gate_C.json
python $A/gate.py --strigger --gate $W/gate_C.json --base $JOB0/scores/locked100_janus0_argmax.json \
  --a1-argmax $W/scores/locked100_a1_argmax.json --a2-argmax $W/scores/locked100_a2_argmax.json \
  --l0 $JOB0/scores/l0.json
```

**Post on #302:**
- `gate_C.json`, without its `L3` per-case detail. It holds no per-case rows;
- the `paired` block of `locked100_a1_vs_a2_tC.json` (σ_g = |mean| / √2);
- the `--strigger` output.

The remaining reports of L-A6 come from the same scorer JSONs. They decide nothing.

### 6.6 S (only if `--strigger` says `S_triggers: true`; D49 Q-R2-4)

- **The form:** 0.5 mm (§3), with Janus 0's plans.
- **The run:** Janus 0's recipe from scratch on dataset 718, 1000 epochs, final validation skipped
  (`ICX4_SKIP_FINAL_VAL=1`), one run.
- **Its look:** the same §6.4–6.5 with:
  - `-tr nnUNetTrainerICX4` and S's plans;
  - `--name "Janus 1-L.2" --alpha 0.0125`;
  - Rule T on S's D60 probabilities against the same Janus 0 at t\*.
- `gate.py` refuses α ≠ 0.0125 for 1-L.2, and refuses a third model.

### 6.7 The decomposition reading (L-A22)

This needs the two posted `summary` blocks, so it is not settled here. The reading is mechanical:
- per group, the macro ceiling: ≥ 0.030 → an arm may be costed; 0.015–0.030 → only after a no-training test on the
  60; < 0.015 → no arm;
- the `distal` contrast share overrides an extent arm;
- LCx is read first.

It decides only what a later round may propose (L-A22), so it does not hold up convergence of Janus 1-L.1's plan.

## 7. What Step T, Job 0 and F0 would change

**F0** is read here as **Janus 0's label-free pass on D60**: Rule T's reference, the "Janus 0 × D60" line of L-A21's
`predict`. Foxtrot's round-2 Job 0b was its earlier form. If the lead meant another job, this row is the one to
re-read.

| Output | Changes |
|---|---|
| **Step T** `SHA256SUMS` (with the fingerprint) | Nothing if `sha256sum -c` passes on Trillium. A mismatch stops P (L-A20) |
| Step T `grep -c "class-weighted CE"` | §5's table: no weights, the last chunk's weights, or a stop |
| Step T `nnUNet_compile` line | Sets #306's `nnUNet_compile` (L-A21). No decision |
| **Job 0** L0 (`l0.json`) | Fail: stop (L-A8). Round 4 cannot rule converged |
| Job 0 `select.json` | t\*; L-A23's rows; §4. It no longer sets S's form (§3) |
| Job 0 `vol60.json` | L-A23's grid row (F7). Reported; S's form is already fixed at 0.5 mm |
| Job 0 decomposition | §6.7, for later rounds only |
| Job 0 MDE | The stated MDE, and "under-powered" in the wording if the tF1 MDE is above 0.025. No margin moves (L-A7) |
| **F0** (Janus 0 on D60) | Rule T's reference. **Run it inside Job 0** (≈ 1 GPU-h, moved out of `predict`, so the total cost is unchanged). Then a D60-side failure is seen before any training: for example, cases where Janus 0 draws nearly nothing at t\* on a quality-0 image, which would leave Rule T few shared points. Pre-registered: if Janus 0 at t\* draws nothing on more than 20 of the 60 cases (`threshold_export.py`'s `voxels.json`, count 0), Rule T has too little reference, so t_C = t\* and the verdict says why. It changes nothing else |

## 8. Questions for the lead

None. D49 answered the open ones, and every branch here is fixed in advance. The only action is the one already on
record: **run Step T before the Fir purge (about 2026-12-20), then Job 0.**

---

## Appendix A. The converged plan text (§5 item 7)

This is the master plan with L-A1 to L-A25, D46, D49 and this version's proposed amendments (marked **[R3]**) written
through. Nothing in it is superseded, and nothing refers to an earlier clause for its meaning. If the judge adopts
§2–§6, it can replace [[Master plan - Janus 1-L]] as it stands, with its §5 commands replaced by §6 above.

### A.0 Binding

- **D45:** the split, Trillium, the lead runs every job.
- **D46:** Q1–Q8, as amended by D49.
- **D49:**
  - E with a2 as a member;
  - D60 label-free;
  - Q4 with "Dice not shown worse";
  - S without another round.
- **D25, D8:** four classes by territory, on ImageCAS-X's lumen.
- **D27/D32:** the seals.
- **D35:** pool questions only.
- **D34:** naming.
- **D40:** pool overlaps become ignore.

Track 1-F shares only the split. The main master plan still governs pool work, D35 and the seal.

### A.1 Data

| Set | Cases | Use |
|---|---|---|
| Train 620 | ImageCAS-X train 560 + dev 44 + 16 of open-36; pin `1350cb1f…1152` | Training (folds 0 and 1, the same split entry) |
| ↳ tuning 60 | dev 44 + those 16 | Rule W on Janus 0's probabilities (Job 0), before any 1-L training; the 10 lowest ids are nnU-Net's fold val (display only) |
| Locked 100 | val 80 + 20 of open-36; pin `bbd9c687…5895` | The one decision. Never trained on, never used to choose, never nnU-Net's val |
| D60 | `drift60.json`, pin `916e8a18…004e` | Rule T only, label-free (D49 Q-R2-2) |
| Sealed | ImageCAS-X test 80 + quality-0 20 | Never read, predicted, scored or trained on |

- **Split file:** `experiments/Delta/j1l_r1/janus1_split_proposal.json` (`19b832fe…4dd3`), which goes to
  `configs/janus1/split-2026-11.json`.
- **Labels:** `territory.to_four`, as dataset 715.
- **Pool reads:** none in Janus 1-L. The later pool fine-tune is member-wise:
  - a1′ from a1 and a2′ from a2, with E′ as the candidate;
  - the 620 are the replay set, and the locked 100 replace val 80 in G2 and in L3's form;
  - D35 decides;
  - D44 reads are collapsed by territory before D40, and material classes follow D46 Q8.

### A.2 Recipe

| Item | Setting |
|---|---|
| Start | Janus 0 `checkpoint_final.pth`, full strict load with heads (`finetune_load`, bitwise, sha256 logged), via `nnUNetTrainer_janus1l` (subclass of `nnUNetTrainer_segtrain_finetune`; `perform_actual_validation` a no-op) |
| Plans | Janus 0's, moved to dataset 718 by `nnUNetv2_move_plans_between_datasets`; equal to Janus 0's except `dataset_name` and `image_reader_writer`. Janus 0's `dataset_fingerprint.json` placed in the preprocessed folder. `nnUNetv2_preprocess` only; no fingerprint or plan step |
| Schedule | 2500-iteration linear warm-up to 1e-2, then poly; SGD, Nesterov 0.99; 250 epochs × 250 iterations |
| Loss | DiceCE with deep supervision. Class weights: **none, unless Step T shows them in Janus 0's last chunk, then those weights [R3, §5]** |
| Augmentation | nnU-Net default, mirroring off in training and inference |
| Validation | Fold val = 10 tuning cases; final validation skipped; `checkpoint_best` never read |
| Environment | `SEGTRAIN_FINETUNE_FROM`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_SAVE_EVERY=10`, `SEGTRAIN_SAVE_PROBABILITIES=0`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, `nnUNet_compile` as Janus 0's; `SEGTRAIN_ITERATIONS`/`SEGTRAIN_EPOCHS` unset; segtrain editable (or `SEGTRAIN_SEALED_LIST`, `SEGTRAIN_POOL_SEAL` set) |
| Runs | a1 = fold 0, a2 = fold 1, concurrent |
| Candidate | **C = E at t_C.** E = the mean softmax of a1 and a2, made **only** by `nnUNetv2_ensemble --save_npz` from each fold's `--save_probabilities` output, **never `nnUNetv2_predict -f 0 1`**, for the look and for every later prediction of the shipped model **[R3, F2, F3]**. If a2 has not finished 250 epochs in two chained jobs, C = a1 at t_C, with Rule T on a1. If a1 has not finished, nothing is scored |
| Inference | `checkpoint_final`, `--disable_tta`, probabilities saved for the locked 100 and D60 |

**Rule W (t\*).**
- On Janus 0's tuning-60 probabilities, at t ∈ {0.50, 0.45, 0.40, 0.35, 0.30}: the highest mean whole-tree Dice,
  subject to:
  - tF1 ≥ tF1(0.50) − 0.005;
  - FP ≤ FP(0.50) + 0.10;
  - no class's centreline recall falls.
- Ties (Dice within 0.002) go to the larger t.
- `decide.py select`; `select.json`'s sha256 is posted before training.
- **[R3, §4]** If t\* = 0.30 at the grid edge and the measured family mismatch is < 0.02, the grid is extended once to
  {0.25, 0.20} with the same guards. If the mismatch is ≥ 0.02, Rule W and Rule T are run on probabilities tempered
  by T̂.

**Rule T (t_C).**
- **Reference:** Janus 0 at t\* on D60, its skeleton and its local radius.
- **Measure:** dr(t), the 10 %-trimmed mean of C(t)'s radius minus Janus 0's, on the shared centreline, pooled.
- **Choice:** t_C = the t ≤ 0.50 on {0.50 … 0.25} with the smallest |dr|. Ties within 0.005 mm go to t\*, then to
  the larger t.
- **Scope:** if t\* was held by a guard, t_C = t\*. **[R3, §7]** Also if Janus 0 at t\* is empty on more than 20 of
  the 60 D60 cases.
- `rule_t.py` on E (a1's and a2's dr are reports). `rule_t.json`'s sha256 is posted before `collect`.

### A.3 The decision on the locked 100

**L0, before anything** (all three clauses, read by `l0_check.py` **[R3, F4]**):
- Trillium's Janus 0 val-80 decisive macro is 0.909 ± 0.003;
- each class is within 0.01 of LM 0.945, LAD 0.903, LCx 0.857, RCA 0.938;
- ≥ 95 % of cases are within 0.01 of Fir's predictions.

Otherwise stop.

**The look:**
- C against Janus 0 at argmax (Job 0), decisive tF1 @ 1.5 mm at A1c `24441cf8…5254`, with Janus 0's A1 aortas;
- A1a/A1b;
- paired by case; 10 000 bootstrap resamples; one-sided α = 2.5 % per bound (1.25 % for S);
- **L3's upper bound is the t bound [R3, F5].**

| # | Test | Passes when |
|---|---|---|
| H1 | tF1 non-inferior, nothing lost | LB Δ macro tF1 > −0.02; no class mean Δ < −0.03; L3 holds; C's FP ≤ 1 per case |
| H2 | Width | LB Δ whole-tree Dice > 0 |
| H3 | tF1 superior | LB Δ macro tF1 > 0 |

**L3:** for no class may either hold:
- the 10 %-trimmed mean Δ `recall` is < −0.02;
- or the mean is < −0.02 with t-bound UB < 0.

Its stated false-alarm rate is 3–8 % (heavy-tailed), up to about 19 % (broad). The report prints excess kurtosis.

| Outcome | Verdict |
|---|---|
| H1 fails | Not adopted; G5 lists five cases per class with mean Δ < −0.05; S if its trigger fires |
| H1, LB in (−0.02, −0.015], H2 fails | Not adopted |
| H1, LB > −0.015, H2 fails, **UB Δ Dice ≥ 0** | **Adopted** (D46 Q4 as amended by D49 Q-R2-3): "non-inferior at 0.015, not shown better" |
| H1, LB > −0.015, H2 fails, UB Δ Dice < 0 | Not adopted: "lumen width shown worse" |
| H1 + H2 | Adopted: "better in lumen width, tF1 non-inferior at 0.02", with the share sentence |
| H1 + H2 + H3 | As above, "and in tF1" |

- **The wording of record** is L-A16's, filled by `gate.py`.
- **What ships is C as tested:** E at t_C, made by `nnUNetv2_ensemble`.
- **Reports, which decide nothing:**
  - Janus 0 at t_C;
  - a1 and a2 at t_C and at argmax;
  - E − a1;
  - σ_g = |a1 − a2|/√2, with A37's rule if > 0.02;
  - C at every t;
  - per-class tF1, Dice, volume ratio, recall, precision and FP;
  - val 80 and locked 20 apart.

**Looks:** at most two in the track. The ledger is opened by `gate.py --preflight` before C is scored **[R3, F8]**.

**S (Janus 1-L.2):**
- **Trigger:** H1 fails, a1 and a2 at argmax both have point Δ < 0, and L0 passed (`gate.py --strigger`).
- **The run:** Janus 0's recipe from scratch on the 620, 1000 epochs, final validation skipped. On the trigger, the
  lead runs it without another round (D49 Q-R2-4).
- **Its form [R3, §3]:** 0.5 mm, with Janus 0's plans. The 0.45 mm form failed the 115 mm view check on the 620.
- **Its look:** t_S by Rule T on S; the same sequence with every bound at 1.25 %.
- **If S fails,** Janus 0 stays.

**Naming:**
- Janus 1-L.1 = C; Janus 1-L.2 = S. The adopted model is Janus 1-L.
- a1, a2, Janus 0 at t_C and every argmax export take no number.

### A.4 Cost (Trillium, 1 × H100, 181 s/epoch)

| Job | GPU-h |
|---|---|
| Step T | 0 |
| Job 0 + F0 (Janus 0 on D60) | 3–4 + ≈ 1 |
| P | ≈ 1 |
| a1 + a2 | ≈ 25–27 |
| predict (2 folds × the locked 100 and D60) | ≈ 2–3 |
| After-Job-0 CPU steps, transfer, collect | 0 |
| **Total** | **≈ 33–35**, ceiling ≈ 60 |
| S on its trigger (0.5 mm) | +≈ 53 |
| E on all 1000, if adopted (two folds + `nnUNetv2_ensemble` + export at t_C) | ≈ 4–8 |

### A.5 Commands

- **Step T** and **Job 0:** as [[Master plan - Janus 1-L]] §5, unchanged.
- **F0:** `sbatch experiments/Atlas/j1l_r3/f0_janus0_d60.sh`, after Step T.
- **After Job 0:** §6.2 above. It replaces the master plan's block (F1, F4, F7).
- **#306** (`check`, `prepare`, `train`): §6.3.
- **`predict`, `transfer`:** §6.4.
- **`collect`:** §6.5.
- **S:** §6.6.

### A.6 Order of record

1. Step T, before ~2026-12-20.
2. Job 0 + F0.
3. Post L0, `select.json`, `vol60.json`, the decomposition and the MDE.
4. The round that reads them rules converged.
5. #306 is built.
6. P, then a1 + a2.
7. predict, then transfer (post `rule_t.json`).
8. collect: preflight, score, gate.
9. S on its trigger.
