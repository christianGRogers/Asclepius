---
tags: [plans, experiment, janus1-L, lumen-width, threshold, transfer, calibration, L-A4]
author: Delta
round: 2
track: 1-L
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
code: experiments/Delta/j1l_r2/transfer_phantom.py, experiments/Delta/j1l_r2/rule_t.py, experiments/Delta/j1l_r2/drift_set.py
---

# t* transfers to Janus 1-L by matching width on the shared centreline of unlabelled quality-0 cases, not by freezing the threshold

**Question** (Janus 1-L Round 1 ruling §5, item 3).
- Rule W chooses t* on **Janus 0's** probabilities for the tuning 60. It is then applied, frozen, to a model trained
  on those same 60 cases.
- No ImageCAS-X case with a label is left outside the locked 100.
- So: how would a calibration shift between Janus 0 and the candidate C show? And is there a pre-registered rule
  that corrects one without any locked-100 number?

## 1. A set the transfer can be measured on: D60

`drift_set.py` derives it from ids alone. No image or label is read.
- ImageCAS has 1000 cases, and ImageCAS-X has 800 of them: the train 620, the locked 100 and the sealed 80.
- The other **200 are quality-0** cases, with no ImageCAS-X label. Removing the 20 sealed ones (A14) and the 24
  declared development cases leaves 156.
- **D60** is the first 60 of those 156 by sha256(`asclepius-janus1l-drift60:` + id).
  - Pin: sha256 of the sorted ids joined by `\n` is `916e8a18…004e`.
  - `drift60.json` lists them.

**D60 meets every condition:**
- no Janus model trained on it;
- it is not the locked 100, and not sealed;
- it is not in the SegQueue14 pool, so it is not D27, D35 or the reserve;
- it is not in Janus-M's sets (checked against `configs/janusm/sealed-r1.json`);
- Trillium already holds its CTs (`fetch_cases.py` fetches all 1000).

**Only the two models' predictions on D60 are compared.** Its original ImageCAS masks are never read.

**The caveat:** quality-0 images are worse than ImageCAS-X's, which is why ImageCAS-X left them out. Rule T compares
two models on the same image, so image quality enters both sides. It is still a domain caveat, and the rule's report
prints the per-case spread.

## 2. Rule T (`rule_t.py`, self-tested)

**The reference** is Janus 0 at t\* on D60: its skeleton S, and its local radius r₀ = EDT on S.

**For each grid t:**
- take the points of S that C(t) also covers;
- dr(t) is the 10 %-trimmed mean of EDT(C(t)) − r₀ over those points, in mm, pooled over the 60 cases.

**The choice:**
- t_C is the grid t ≤ 0.50 with the smallest |dr|.
- Ties within 0.005 mm go to t\*, then to the larger t.
- The grid is 0.60 … 0.25. 0.60 and 0.55 are reported only; the lever only widens.

**Scope:** Rule T applies only when t\* is Rule W's Dice optimum, not a choice held back by a guard (`select.json`:
Dice at t\* within 0.002 of the best Dice over the five thresholds). Otherwise t_C = t\*, as the ruling has it now.

**Why the shared centreline, not the volume:** a model that draws more distal branches would push a volume match
towards a higher t, and so thin every vessel. On the shared centreline, extent does not count.

## 3. Phantom test (`transfer_phantom.py`)

The test uses synthetic trees on a 0.5 mm grid:
- a tapering trunk, 2.0 → 0.8 mm, and two side branches;
- a model's probability is sigmoid((R − b − d)/τ);
- **Janus 0** = b 0.07 mm, τ 0.22 mm, which gives an argmax volume ratio of **0.859** (measured on Janus 0: 0.867);
- Rule W on 12 tuning trees chooses **t\* = 0.40**, inside Crucible's prediction of {0.45, 0.40};
- C differs from Janus 0 in one way per scenario;
- Rule T reads 12 drift trees (no labels), and Dice is measured on 12 other trees.

| C differs from Janus 0 by | t\* frozen | Rule T | Volume match | Oracle t | Dice: frozen → Rule T (oracle) | Volume ratio: frozen → Rule T |
|---|---|---|---|---|---|---|
| nothing | 0.40 | 0.40 | 0.40 | 0.40 | 0.964 → 0.964 (0.964) | 0.99 → 0.99 |
| a sharper boundary (τ × 0.6; more training) | 0.40 | **0.35** | 0.35 | 0.35 | 0.966 → **0.970** (0.970) | 0.93 → 0.98 |
| a softer boundary (τ × 1.6) | 0.40 | **0.45** | 0.45 | 0.45 | 0.926 → **0.979** (0.979) | 1.07 → 0.96 |
| two members ± 0.15 mm, averaged (an ensemble) | 0.40 | 0.40 | 0.40 | 0.45 | 0.957 → 0.957 (0.962) | 1.01 → 1.01 |
| a real width gain (b = 0) | 0.40 | **0.50** | 0.50 | 0.50 | 0.914 → **0.979** (0.979) | 1.10 → 0.96 |
| more extent (a distal branch Janus 0 misses) | 0.40 | 0.40 | **0.45** ✗ | 0.40 | 0.984 → 0.984 (0.984); volume match 0.977 | 1.03 → 1.03 |

**What it shows.**
1. **A frozen t\* fails exactly where the candidate's calibration moved.** It over-widens a softer model (Dice
   −0.053). It over-widens a model that learned the width itself (−0.066), and that is the case H2 hopes for. It
   under-widens a sharper one.
2. **Rule T recovers the oracle threshold in five of six scenarios.** In the sixth (the ensemble) it keeps t\*, and
   loses 0.005 Dice against the oracle.
3. **A plain volume match is wrong when extent changes.** Rule T is not.
4. **When nothing changed, Rule T returns t\*.** It costs nothing in the case the ruling assumes.

**Limits.**
- This is a phantom. The real calibration shift between Janus 0 and a 250-epoch warm child, or their ensemble, is
  unknown until it is measured, and dr(t\*) on D60 is that measurement.
- The EDT is quantised on a 0.5 mm grid. The pooled trimmed mean over thousands of skeleton points resolves 0.01 mm
  in the phantom, and the 0.005 mm tie band sits below one grid step (about 0.05 mm here).
- D60's image quality differs from the locked 100's (§1).

## What it changes

- **Item 3 has a pre-registered alternative to the frozen rule** (Delta v2 §3). It never reads a locked-100 number
  or a label. Its result, `rule_t.json`, is frozen and its sha256 posted on #302 before `collect` scores C.
- **The calibration shift becomes visible before the look.** It is the printed dr(t\*), in mm, with per-case values.
- After the look, the ruling's report of C's Dice at every t on the locked 100 shows whether Rule T's choice was
  right. It is a report: nothing is re-chosen.
