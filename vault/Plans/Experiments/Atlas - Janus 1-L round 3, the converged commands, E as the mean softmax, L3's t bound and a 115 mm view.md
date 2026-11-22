---
tags: [plans/experiment, janus1-l, track-1-L, round3, ensemble, threshold, L3, spacing, D45, D49]
author: Atlas
round: 3
track: 1-L
updated: 2026-11-22
issue: christianGRogers/Asclepius#302
---

# Atlas: Janus 1-L round 3, the converged commands, E as the mean softmax, L3's t bound and a 115 mm view

For [[Candidates/Janus 1-L/Atlas v3|Atlas v3]] (track 1-L, round 3). CPU only. No GPU job, no Trillium job.

## Questions

1. **Do the plan of record's commands and the merged scripts fit together** for the look ([[Janus 1-L Round 2]] §5
   item 6)?
2. **Is `nnUNetv2_predict -f 0 1` the same E as `nnUNetv2_ensemble`** (L-A14)?
3. **Does L3, computed with L-A5's bootstrap bound, keep its stated 3–8 % false-alarm rate?**
4. **Can a temperature fit change what Rule W chooses** (§5 item 4)?
5. **Does a 256³ patch at 0.45 mm (115.2 mm) still see what one at 0.5 mm (128 mm) sees**, on the 620 (§5 item 3)?

## Data and rules kept

- **Labels:** ImageCAS-X segmentations of **the 620 D45 training cases only**. `fetch_train620.py` reads exactly
  those 620 files from the public Zenodo zip by range request. It checks the L-A1 pin `1350cb1f…1152` and refuses
  sealed and locked ids. The files sit in the session scratchpad and are not committed.
- **Not used:**
  - no label of the locked 100, the sealed 80 or the quality-0 20 was opened;
  - no D60 image was used (none is on this machine);
  - no TotalSegmentator data was used.
- **Recall differences for Q3:** the committed per-case results of Round 7's warm siblings (atlas3 F1 − F0, val 80),
  read through Delta's `ensemble_power.measured`, as in round 2.
- **Software:** nnU-Net 2.8.1's wheel was downloaded to the scratchpad and **read, not installed or run**. The other
  checks ran on Python 3.13, NumPy 2.5.3, SciPy 1.18.1 and scikit-image 0.26.0.

## Code (`experiments/Atlas/j1l_r3/`)

| File | What | Self-test |
|---|---|---|
| `gate.py` | `collect`'s gate: L-A16 with D49 Q-R2-3, L3 with the t bound, share sentence, G5, S trigger, preflight and looks ledger | passed |
| `l0_check.py` | L0's three clauses from `identity_val80.json` | passed |
| `vol60.py` | Tuning-60 volume ratio per t, and L-A23's grid row | passed |
| `calib.py` | Q2's widths (`tables`); Q4's family mismatch; `fit` for the lead | passed |
| `l3_null.py` | Q3 (`l3_null.json`) | — |
| `view045.py`, `fetch_train620.py` | Q5 | passed |
| `f0_janus0_d60.sh` | F0: Janus 0 on D60 beside Job 0 (for the lead) | `bash -n` |

The merged scripts the commands use passed their own self-tests here:
- `threshold_export.py`, `decide.py`, `rule_t.py`, `r9_score_icx4.py`, `error_decomp.py`.

## Results

### Q1. Eight defects (Atlas v3 §2)

| # | Defect | Effect if left |
|---|---|---|
| F1 | `'%.2f' % chosen_t` with a string `chosen_t` | The post-Job-0 decomposition at t\* never runs (TypeError) |
| F2 | `predict -f 0 1` ≠ `nnUNetv2_ensemble` | An E made the wrong way is a different model from the one tested (Q2) |
| F3 | `nnUNetv2_ensemble` without `--save_npz` | No probabilities for `threshold_export.py`, so E has no t_C export |
| F4 | L0's third clause not in the posted blocks | L0 cannot be read from what is posted |
| F5 | L3 with a bootstrap upper bound | About twice the stated false alarm (Q3) |
| F6 | Rule T's eight-threshold exports; Janus 0 at t_C = 0.25 | Missing inputs |
| F7 | L-A23's grid row needs a volume ratio no job writes | The row cannot be read |
| F8 | The looks ledger is written after the look | A second scoring of C is not prevented |

### Q2. Mean logits and mean probabilities

- **nnU-Net 2.8.1 does two different things:**
  - `predict -f 0 1` sums the folds' logits and divides (`predict_from_raw_data.py` l. 524–530);
  - `nnUNetv2_ensemble` averages the probabilities (`ensemble.py` l. 18–31).
- **For two members and a foreground/background split, they agree exactly at t = 0.5**, since σ(a) + σ(b) = 1 iff
  a + b = 0. They differ at every other t.
- **The width difference** (mm, radial profile, fold rims ±δ apart, rim logit slope k):

| k (per mm) | rims apart | t = 0.45 | t = 0.40 | t = 0.35 | t = 0.30 |
|---|---|---|---|---|---|
| 2 | 0.5 mm | 0.006 | 0.013 | 0.019 | 0.025 |
| 4 | 0.5 mm | 0.014 | 0.027 | 0.040 | 0.052 |
| 8 | 0.5 mm | 0.034 | 0.063 | 0.087 | 0.106 |
| 4 | 1.0 mm | 0.067 | 0.126 | 0.174 | 0.212 |
| 8 | 1.0 mm | 0.204 | 0.277 | 0.317 | 0.344 |

- The mean-softmax E is always the wider one. With rims 0.2 mm apart the difference is ≤ 0.016 mm.
- **It is a real difference at the plan's export, t_C < 0.5:** up to half a voxel, where Rule W and Rule T resolve
  about 0.1 mm.

### Q3. L3's false alarm, t bound against bootstrap

- **Setup:** 2000 replicates, n = 100, B = 1000. The noise is the measured sibling recall differences (heavy-tailed)
  plus a broad component of λ × their variance. True change 0. L3 fires if any class fires.

| Noise | L3, t bound | L3, bootstrap | Trimmed clause alone | Power, uniform −0.03 LCx (t / bootstrap) |
|---|---|---|---|---|
| heavy, λ = 0 | **0.036** | **0.081** | 0.000 | 1.000 / 1.000 |
| heavy, λ = 1 | 0.072 | 0.113 | 0.001 | 0.982 / 0.982 |
| heavy, λ = 3 | 0.074 | 0.138 | 0.002 | 0.944 / 0.947 |
| Gaussian, λ = 1 | 0.178 | 0.189 | 0.170 | 0.806 / 0.808 |

- **The t-bound column reproduces Delta's `l3_fix.json`** (0.037, 0.067, 0.074, 0.174).
- **The bootstrap doubles the false alarm under heavy tails, and buys no power.** With a few large flips, the
  percentile bootstrap of a mean is narrower than the t interval, so clause (b) (mean < −0.02 and UB < 0) fires more.
- **So:** L3's clause (b) must use the t bound for the stated rate to hold. `gate.py` does.

### Q4. Temperature and Rule W's family of masks

- **Why the family is mostly preserved:** a temperature keeps every argmax. Where one vessel class dominates, it also
  keeps the order of the foreground probability, so the masks are the same masks met at other t.
- **Where it is not:** on a synthetic LM → LAD/LCx bifurcation (0.25 mm grid), the mask at t and the tempered mask of
  equal size differ by:
  - **1–9 % of the mask** at T = 0.7 and 1.5 with rim slopes of 2 per mm;
  - **0.7–2.8 %** with rim slopes of 4 per mm.
- **So a temperature mostly re-labels Rule W's grid, but not entirely.** `calib.py fit` measures the same mismatch on
  Janus 0's own tuning-60 probabilities when the lead runs it. Atlas v3 §4 maps its result to an action (re-run below
  0.02, report at or above).

### Q5. The 115 mm view, on the 620

VIEW_RESULT

## What it changes

- **E is made only by `nnUNetv2_ensemble --save_npz`,** for the look and for every later prediction of the shipped
  model.
- **L3's clause (b) uses the t bound.** It is the one bound of the look that is not a bootstrap.
- **The post-Job-0 block is replaced.** The new one fixes F1, reads L0 in full (F4), and computes the volume ratio
  (F7).
- **The look is opened by a preflight** before C is scored (F8).
- **S's form:** VIEW_CHANGE
- **Calibration:** a temperature fit is a report unless the real-data family mismatch is ≥ 0.02.
- **Nothing here reads a locked-100 number, and nothing moves a margin.**
