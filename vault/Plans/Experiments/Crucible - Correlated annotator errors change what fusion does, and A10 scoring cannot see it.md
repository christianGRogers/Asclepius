---
tags: [plans, experiment, double-reads, noisy-labels, correlated-errors, a10, a11]
author: Crucible
round: 4
updated: 2026-10-08
---

# Correlated annotator errors: fusion still barely matters, *unless* annotators have opposite habits, and then A10's scoring cannot tell which fusion is right

## Question

The Round-3 ruling (§4) asks whether the two-read conclusions in
[[Crucible - Simulated double reads and what each fusion rule teaches]] survive four things:

- **correlated errors**: both readers stop at the same stenosis, or share a carina bias;
- **systematic per-annotator bias**;
- **boundary jitter** beyond truncation;
- the judge's **A11 hybrid**: each read a separate sample, a name conflict inside vessel both reads keep → `ignore`,
  and extent differences kept.

## Method

`experiments/Crucible/r5_corr.py`, summary `r5_summ.py`. Setup:

- 14 cases (the first 14 of the 49 in `r2data`);
- K = 8 extra reads per case plus the two "real" reads A and B;
- the read generator of `trillium/crucible/lib/sim.py`: truth T is the ImageCAS mask split into territory classes
  with ramus → LCx (D0, D1, D1b), and every tree is rooted;
- slip rates in every scenario: ramus → LAD 0.3, D1/OM1 swap 0.15.

Scenarios (s = carina shift in mm, r_t = truncation radius in mm):

| Scenario | Error structure |
|---|---|
| indep | s ~ N(0, 2), r_t ~ U(0.6, 1.05), independent per read (the round-3 model) |
| corr_trunc | r_t = 0.8·u_case + 0.2·u_read: both readers stop at the same thin or stenotic point |
| corr_carina | s = m_case + N(0, 0.7), m_case ~ N(0, 2): a carina ambiguity both readers share |
| annot_bias | two annotators with opposite habits. X: s ~ N(+1.5, 1), r_t ~ U(0.8, 1.1). Y: s ~ N(−1.5, 1), r_t ~ U(0.55, 0.8). A = X, B = Y, extra reads alternate |
| team_bias | the whole team shares X's habit |
| jitter | indep plus brush jitter: about 30 % of surface voxels trimmed in smooth random patches per read |

**What a converged model learns** under each scheme is taken as the per-voxel plurality (argmax) of that scheme's
targets over the draws. That is the cross-entropy optimum. Schemes compared:

- single / both (same optimum);
- a11 (A11);
- agree-or-ignore;
- union-or-ignore.

Voxels that are `ignore` in *every* draw have no optimum. They are scored two ways:

- **worst case**: background;
- **FILL**: the label of the nearest supervised voxel, which is how a network extrapolates into unsupervised voxels.

**Scoring:** tF1 @ 1.5 mm against the truth, and against the reads (A10: the mean over the two reads), plus
inter-read tF1. Paired differences against both-as-samples carry a bootstrap 95 % CI over cases.

## Result (14 cases per scenario; tF1)

| Scenario | inter-read | both: vs truth / vs reads | a11 − both vs truth | agree − both vs truth | union − both vs truth | truth scored vs reads | both vs reads − inter-read |
|---|---|---|---|---|---|---|---|
| indep | 0.915 | 0.947 / 0.939 | −0.001 [−0.002, 0.000] | −0.001 | +0.003 [0.000, +0.008] | 0.920 | +0.024 (11/14) |
| corr_trunc | 0.926 | 0.943 / 0.948 | −0.001 | −0.001 | −0.000 | 0.925 | +0.022 (11/14) |
| corr_carina | 0.946 | **0.922** / 0.946 | −0.000 | −0.000 | +0.004 [+0.001, +0.008] | **0.905** | **+0.000** (12/14) |
| team_bias (13) | 0.930 | **0.896** / 0.941 | −0.001 | −0.001 | +0.009 [+0.003, +0.017] | **0.897** | +0.011 (9/13) |
| jitter | 0.909 | 0.943 / 0.888 | **+0.005 [+0.001, +0.010]** | +0.003 | −0.007 | 0.917 | **−0.020** (8/14) |
| annot_bias, worst case | 0.872 | 0.944 / 0.929 | −0.075 [−0.192, +0.007] | −0.075 | −0.067 | 0.910 | +0.058 (13/14) |
| **annot_bias, FILL** | 0.872 | 0.944 / 0.929 | **+0.018 [+0.001, +0.043]** | **+0.021 [+0.004, +0.045]** | **+0.026 [+0.009, +0.051]** | 0.910 | +0.058 |

Against the reads, every fusion is within ±0.002 of both-as-samples in every scenario, including annot_bias with
FILL (a11 − both vs reads −0.001 [−0.003, +0.001]).

## What it implies

1. **The round-3 conclusion survives correlated truncation, a shared carina ambiguity, team-wide bias and brush
   jitter.** Every fusion scheme converges to within about 0.01 tF1 of both-as-samples. A11 is never worse than
   −0.001 there, and it is better under jitter (+0.005, CI excludes 0; tie-sensitive row, see 5). A11 is a safe default on this evidence.
2. **Opposite annotator habits are the exception, and the answer hinges on something only training can show.** When
   the two reads of each case come from annotators with opposite carina and truncation habits, the reads conflict in
   the same band in *every* pair. Ignore-based fusions then leave that band unsupervised everywhere.
   - If the network fills it from the neighbours (FILL), the boundary lands between the habits, near the truth.
     A11, agree and union then **beat both-as-samples by +0.02–0.03 vs truth**, CIs excluding 0.
   - If it does not (worst case), they lose up to 0.07.
   - The prepared Trillium run now uses exactly this read model (`CRUCIBLE_READS=annot_bias`, the default), so the
     GPU answers the FILL-vs-worst question with a real nnU-Net:
     [[Crucible - GPU experiment on training with two reads per case (pending)]].
3. **A10 cannot see any of this.** Scored against the reads, the fusions are within ±0.002 of each other even where
   they differ by 0.02–0.03 against the truth.
   - With correlated errors (corr_carina, team_bias) the converged model drifts from the truth (0.922, 0.896). The
     truth itself then scores *below* the model against the reads (0.905 vs 0.946; 0.897 vs 0.941).
   - A10 rewards learning the team's shared bias. Inter-read agreement cannot detect a bias both readers share.
   - **A team-wide bias needs an external anchor.** The cheapest one already exists: ImageCAS-X's named centrelines
     on 800 of our cases. The *position* of the LM end and of the LAD/LCx split is largely convention-independent,
     even though the lumen extent is not. So the distribution of (team LM-end − ImageCAS-X LM-end) along the
     centreline in wave 1 measures a team-wide carina bias directly.
   - Proposed as an addition to A12 (CPU, minutes).
4. **The A10 expectation "a model should beat inter-read" is conditional.** The margin of a converged model over
   inter-read is +0.024 (indep), +0.022 (corr_trunc), **0.000** (corr_carina), +0.011 (team_bias), and −0.020
   (jitter). The jitter value is tie-sensitive; see 5.
   - Jitter makes every read noisier against the model than against another read, because both reads trim but in
     different places.
   - Under a shared carina ambiguity a converged model only *ties* inter-read, so A10's 0.02 non-inferiority margin
     is not lenient. If the wave-1 refit shows a shared carina ambiguity or strong boundary jitter, re-check the
     margin before sealed-test scoring.
5. **A read-out check, which turned out negative.** Under jitter the converged-model proxy under-segments (foreground
   0.866 of the truth). I tested whether a hierarchical read-out (vessel if vessel votes > background votes, then
   the plurality class) fixes it (`HIER=1`, 3 cases). It barely does: +0.005 tF1 vs truth, foreground 0.858. Most
   of the shortfall is a **tie artefact of the proxy**: K = 8 is even, and 4-to-4 ties go to background. So the
   jitter-row conclusion "a converged model sits 0.02 below inter-read" is **tie-sensitive** and should not be
   relied on. The other rows have few extent ties and are unaffected to the precision shown. Hierarchical read-out
   is not proposed.

## Limits

- The error models are invented and calibrated only loosely; A12's refit on real reads is what makes any of this
  binding.
- The "converged model = plurality of targets" idealisation ignores capacity and finite data. The FILL / worst-case
  bracket is exactly where that idealisation breaks.
- 14 cases; K = 8. The CIs are case bootstraps.
- tF1 is my re-implementation (provisional under A9).
