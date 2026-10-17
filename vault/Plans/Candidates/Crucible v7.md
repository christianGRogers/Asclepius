---
tags: [plans, candidate, double-reads, a11, a10, round-5]
author: Crucible
round: 5
version: 7
updated: 2026-10-09
---

# Crucible v7 — Train on both reads as samples, and drop A11's name-conflict `ignore`: on the GPU it cost 0.035 tF1 on the decisive score and bought nothing against the truth

## 0. Improve or start again?

**Improve v6.** The Trillium run is back: [[Crucible - Trillium two-reads result]]. Everything in v6 stands:

- the master recipe;
- A10 scoring and acceptance;
- A11's case-level third-read rule;
- A12a/A12b with the measured anchor floor;
- `segtrain.reads`.

What changes is A11's voxel rule.

## 1. Thesis

On 50 test cases, in the opposite-habit regime (`annot_bias`), with six equal-step nnU-Net arms:

1. **The second read is worth training on.** Both reads as separate samples beat a single read by **+0.030 tF1
   against the truth**, CI [+0.010, +0.050].
2. **No fusion beats it.**
   - Agree-or-ignore ties (+0.003, n.s.).
   - A11's conflict `ignore` is −0.008 against the truth (n.s.) but **−0.035 against the reads**, CI
     [−0.046, −0.023]. Against the reads is the master's decisive score.
   - Union is worse on both.
   - The mechanism shows in the LM. In A11 and union the network fills the ignored carina band with LM, so it
     *adopts one annotator's habit*: LM tF1 against the other annotator is 0.51, against 0.79 for both-as-samples.
3. **Truth labels did not beat two simulated reads** (oracle 0.825 vs both 0.830 against the truth).

My own pre-registered rule for narrowing A11 does not fire, because a11 − both vs truth has a CI that includes 0.
But the pre-registered general row selects both-as-samples, and the decisive A10 score separates them clearly. So I
propose **A11′**: keep A11's case level; at voxel level, train on each read as its own sample with **no
name-conflict `ignore`**.

## 2. Recipe change (amendment A11′)

| | A11 (binding) | A11′ (proposed) |
|---|---|---|
| Case level: third read on wholesale disagreement (tF1 < 0.80, ostium/LM > 5 mm, swap > 5 %, Bridge's decision flags); ramus-only exempt | yes | **unchanged** |
| Voxel level: each read a training sample | yes | yes |
| Name conflict inside vessel both reads keep → `ignore` | yes | **no**: each sample keeps its read's labels |
| Extent differences kept | yes | yes |

Implementation needs one change. `segtrain.reads.a11_targets` gets a `conflict_ignore` switch (default per the
ruling), or the converter simply uses the reads as they are. No ignore label is needed in the dataset.

**When A11 would still be right:** if real reads show no annotator habits (A12a), all schemes behave alike in
simulation and the choice is moot. A11′ is never worse in any measured regime.

## 3. Evaluation

Unchanged (A1, A9, A10). Two notes from the run:

- **A10's per-class test is informative.** It failed LAD, LCx and RCA (models 0.73–0.84 vs inter-read 0.94–0.97)
  while the LM passed (models about 0.79 vs inter-read 0.64 under opposite habits). It rejects classes, not
  whole models.
- **Scoring against single annotators understated every arm** by 0.03–0.07 relative to the truth.

## 4. Evidence

| Claim | Evidence |
|---|---|
| both − single = +0.030 [+0.010, +0.050] vs truth; +0.017 [+0.001, +0.036] vs reads | [[Crucible - Trillium two-reads result]] |
| a11 − both = −0.008 [−0.018, +0.003] vs truth; **−0.035 [−0.046, −0.023] vs reads** | same |
| The mechanism is the LM: a11 LM vs read B 0.505, both 0.785 | same (results.json per-class aggregates) |
| agree − both = +0.003 / +0.002 (n.s.); union − both = −0.015 / −0.042 | same |
| oracle 0.825 ≤ both 0.830 vs truth | same |
| In the CPU study, A11 was within 0.001 of both under independent and correlated errors | [[Crucible - Correlated annotator errors change what fusion does, and A10 scoring cannot see it]] |

**Withdrawn claim from v5:** "against the reads every fusion is within ±0.002". It held for the CPU plurality
proxy and fails for a trained network under habits.

## 5. Risks

| Risk | Detection | Response |
|---|---|---|
| Real habits are weaker than `annot_bias`, so the A11 vs A11′ gap shrinks | A12a on wave 1 | A11′ is never worse in any measured regime, so no harm |
| Contradictory training targets blur the carina boundary without `ignore` | Branch-swap rate and LM tF1 on R1 val | The GPU run shows the opposite under habits (both: LM 0.930 vs truth; a11: 0.889) |
| One seed, small patch | — | The master's A11 test on real reads (if A12 finds habits) re-checks it, judged on the carina anchor |

## 6. Comparison

**Master (A11).** v7 changes one voxel rule, on measured GPU evidence. Agree-or-ignore (Atlas's original proposal)
is statistically tied with both-as-samples, so Atlas's position is not refuted; A11's hybrid is.

## 7. Cost

None. A11′ removes the ignore label from the training datasets.

## 8. Changes since v6

- GPU result incorporated.
- A11′ proposed.
- One CPU prediction withdrawn ("A10 cannot choose a fusion").
- Noted: the truth-trained arm does not beat two simulated reads; a11-vs-agree is unexplained (one seed).
