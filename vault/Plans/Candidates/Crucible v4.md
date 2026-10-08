---
tags: [plans, candidate, double-reads, noisy-labels, evaluation, round-3]
author: Crucible
round: 3
version: 4
updated: 2026-10-08
---

# Crucible v4 — Two reads per case: train on both, score against both, and stop treating inter-rater agreement as the ceiling

## 0. Improve or start again?

**Started again on a new question.** The human decisions settled what v1–v3 argued about: D0 keeps the original
ImageCAS mask as target, seed and reference, and D4 forbids 4-class seeds. The convention monitor, seed tagging and
single-convention sealed test are already binding (A3). My CPU training arms became moot (a thin target is no
longer an option), so I stopped them.

D2 (every case read twice) opens a question no plan has measured: **how the two reads should enter training and
evaluation.** That is the noisy-label question this plan was built for.

The model recipe stays the master's ([[Atlas v3]]): nnU-Net v2 ResEnc, 0.5 mm iso, 256³ patch, fixed window,
no mirroring, tF1 @ 1.5 mm, A1–A9.

## 1. Thesis

With two independent reads of the same split mask, three things follow.

1. **The fusion rule barely changes the target a model converges to.** Under symmetric, independent annotator
   errors the population optimum of every scheme (one read, both reads, agree-or-ignore, union-or-ignore) is about
   the per-voxel majority. In simulation they are within 0.004 tF1 of each other (0.953–0.957 against the truth).
   - What differs is supervision volume and gradient noise. Pick the simplest scheme that wastes nothing: **both
     reads as separate samples**, unless the GPU run says otherwise.
2. **A single read is a biased judge.** Against one read, the truth itself scores only 0.922, *below* a model that
   imitates the median annotator (0.933). The decisive score must use both reads.
3. **The inter-read agreement is a floor for a good model, not a ceiling.** The median-annotator model beats
   read-vs-read agreement by +0.057 tF1, in 20 of 24 cases. The master's acceptance rule ("within 5 points of
   inter-rater") would accept a model about 0.11 below what is achievable.

## 2. Recipe (master, plus the two-read policy)

### 2.1 Training target from two reads

- **Default: both reads as two training samples** (case `cXXXX_r1`, `cXXXX_r2`; same image). Iterations per epoch
  stay at 250, so there is no GPU cost. No ignore label is needed.
- **Why not the master's agree-or-ignore by default.** At the optimum it is equal (0.953 vs 0.957). But it
  `ignore`s every voxel where one annotator truncated a distal branch and the other did not. Truncation is the one
  one-sided error in the protocol ("stop where the lumen is no longer confident"), and ignoring it leaves distal
  vessel unsupervised exactly where tF1's rooted recall is decided.
- **The pre-registered GPU run decides between the schemes:**
  [[Crucible - GPU experiment on training with two reads per case (pending)]].
  - Arms: single / both / agree / union / oracle.
  - Same plan, same steps, 200 train / 50 test.
  - Paired CI against single.
  - Its decision table replaces this default if another scheme wins.
- **Adjudication (kept from the master):** a third read when the reads disagree wholesale (inter-read macro tF1
  < 0.80, ostium/LM > 5 mm, LAD↔LCx swap > 5 %). After adjudication, train on all three reads as samples.

### 2.2 Reference and acceptance on the sealed test

- **Decisive score per case = the mean of tF1 against read 1 and against read 2.** This needs no fusion and no
  tF1-with-ignore implementation, and it is unbiased with respect to annotator choice.
  - Also reported: tF1 restricted to voxels where the reads agree.
  - Also reported: per-class inter-read tF1.
- **Acceptance, restated.** Per class, the model's mean-vs-reads tF1 must be **≥ the inter-read tF1 of the same
  cases**, with a paired bootstrap CI excluding a deficit larger than 0.02. This replaces "≥ inter-rater − 5 points".
  The simulation says a converged model should clear inter-read by about 0.06, so "−5 points" is about 0.11 too lenient.

### 2.3 Using the inter-read agreement (D2 gives it for all 1000 cases)

- **Difficulty stratum.** Every metric is reported by inter-read tF1 tercile, so model regressions on hard cases are
  not averaged away.
- **Noise-model refit.** On the first 50 double-read cases, fit the simulation's parameters (carina SD, truncation
  radius distribution, ramus and side-branch slip rates) to the real disagreement. Then re-run
  `experiments/Crucible/r4_fusion.py` (CPU, about 1 h).
  - If real errors are correlated or one-sided (for example both annotators stop at stenoses, or one annotator
    systematically truncates), the "fusion barely matters" conclusion is re-tested before R1 consumes team reads.
- **Annotator QA.** A per-annotator truncation rate (fraction of the partner's distal centreline they drop) flags
  annotators to re-instruct. It costs no GPU.

## 3. Evaluation

The master's (A1, A9), with §2.2 replacing the reference and the acceptance rule. The sealed test is unchanged: 80
ImageCAS-X-test cases plus 20 quality-0 cases, two reads each.

## 4. Evidence

| Claim | Evidence |
|---|---|
| Fusion rules converge to nearly the same model (0.953–0.957 tF1 vs truth) | [[Crucible - Simulated double reads and what each fusion rule teaches]] (24 cases, K = 10 extra reads) |
| Single-read scoring ranks the median annotator (0.933) above the truth (0.922) | same |
| A converged model beats inter-read agreement by +0.057 (20/24 cases) | same |
| The simulated reads are calibrated to inter-read Dice LM 0.81 / LAD 0.93 / LCx 0.90 / RCA 0.96 | same; ImageCAS-X Table 1 for comparison |
| Two-rater STAPLE reduces to vote / does not beat majority vote | [[Fusing multiple annotations and learning from noisy labels]]; Atlas v3 §2.1 |
| Training on noisy labels converges toward the label distribution; a large noisy set can beat a small clean one | Karimi et al. in [[Fusing multiple annotations and learning from noisy labels]] |
| nnU-Net supports partial labels via `ignore` | Gotkowski et al. arXiv:2403.12834; nnU-Net `documentation/ignore_label.md` |
| GPU test ready, contract-compliant | `trillium/crucible/` (smoke-tested on CPU; see the pending note) |

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| Real annotator errors are correlated, so fusion does matter | Refit on the first 50 double reads; re-run the simulation | Switch to the GPU run's winning scheme; adjudicate more |
| "Both as samples" blurs carina boundaries | GPU run: branch-swap rate and LM tF1 by arm | Agree-or-ignore at the carina only (a hybrid), if the run shows it |
| The simulation's tF1 is a provisional re-implementation | A9 port | Re-score with the ported metric |
| Mean-of-two-reads scoring is noisier per case than a fused reference | Report both; bootstrap over cases | — |

## 6. Comparison with the master (Atlas v3)

- **Agree:** model, data, schedule, adjudication trigger, sealed test.
- **Disagree, on evidence:**
  1. The default fusion. Agree-or-ignore discards one-sided truncation voxels that both-as-samples keeps, at equal
     optimum. Atlas lists both-as-samples as ablation A5r; I make it the default and give the ablation a GPU run with
     a decision table.
  2. The reference. Atlas fuses the sealed test; I score against both reads, which needs no ignore-aware tF1.
  3. **The acceptance rule.** "≥ inter-rater − 5" is too lenient by about 0.11 under the simulation.
- **Bridge v3 / Delta v3:** not affected. The namer QA and topology repairs apply to whichever target is chosen.

## 7. Cost

- **GPU:** 0 beyond the master, plus the one prepared Trillium run (≤ 24 H100-h, run by the lead).
- **CPU:** noise refit and re-simulation, about 1 h once.
- **Human:** none beyond D2.

## 8. Changes since v3

- New question and plan: the two-read policy (§2), restated acceptance, and the inter-read agreement used as a
  stratum and a QA signal.
- New notes:
  - [[Crucible - Simulated double reads and what each fusion rule teaches]];
  - [[Crucible - GPU experiment on training with two reads per case (pending)]];
  - [[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]], now with the reverse
    direction (0.746, artefactual RCA cuts). This is now relevant only to comparisons against ImageCAS-X (D0).
- Dropped: the thin/thick/14-class CPU training arms, moot under D0. Their partial results were never valid, because
  the tiny model could not name at a 28 mm patch (tF1 ≈ 0.05).
