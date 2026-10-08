---
tags: [plans, candidate, branch-labelling, double-reads, round-4]
author: Bridge
round: 4
status: candidate
updated: 2026-10-08
---

# Bridge v4: the master, with naming judged on the master's own model, at a quarter of the GPU cost

## 0. Improve or start again?

**Improve.** The Round 3 ruling kept Atlas v3 and took three things from Bridge:

- the decision extractor, as an adjudication trigger (A11);
- the naming competitor (A7);
- the D/R/H/O experiment, best run inference-only on Atlas's outputs (A13).

It named three things that would change the ruling:

1. the D/R/H/O result on a real direct model;
2. wave-1 evidence that human naming disagreement is decision-shaped;
3. an aorta-preferred ostium.

No CPU result can deliver (1) or (2). v4 therefore does what can be done before the GPU and wave 1:

- It makes (1) as cheap and as directly relevant as possible: `trillium/bridge` now scores the **Atlas
  model itself**, inference-only.
- It answers (3) with a measured negative.
- It drops the one v3 proposal the ruling could not credit: the branch/jitter lumen rule.

I do not have a recipe that I believe beats the master on tF1. A two-stage segmentation route lost on
evidence in Round 1, and nothing since has revived it.

## 1. Thesis (narrowed)

Naming a predicted coronary tree takes a few discrete decisions per case: ostium, LM end, LAD/LCx side,
tree identity, and the ramus (now a rule, D1b). Structure can make those decisions consistently; a voxel
classifier makes them voxel by voxel. Whether structure *out-names the master's network* is one
measurement: D/R/H/O on Atlas's val softmax. v4 exists to get that measurement at ≤ 4 H100-hours, and to
make the two-read pipeline decision-aware at no GPU cost.

## 2. Recipe

### 2.1 Training, data, metric

[[Atlas v3]] with A1–A13 and D0–D5, unchanged. Bridge proposes no change to the model, the data or the
schedule.

### 2.2 Naming (A7, as ruled)

- **D** = the master's labels.
- **R** = the frozen namer on D's foreground: ramus → LCx, 4 mm naming bridges.
- **H** = exact grammar decoding of D's softmax: LM a connected region containing the ostium; every
  subtree below it wholly LAD or LCx; RCA tree by P(RCA).
- **Shipped only by the A7 rule.**
- **v4 change to H, from the CPU dry run:** the unary is the log of the vertex's *mean* softmax, plus a
  0.5-nat LM prior. The first version let the LM absorb an ambiguous LCx stretch on the fake test.
- The aorta-preferred ostium stays in the namer as a **cross-check flag** (chosen ostium touches no contrast
  pool), not as a re-rank. Measured: it changed 0 of 39 choices
  ([[Bridge - An aorta-preferred ostium changes nothing, because the learned ostium already touches the pool]]).
- **Proposed instead** (untested): add the A1 aorta-contact point as an extra ostium *candidate*. The two
  big ostium failures (c0325, c0800) have no correct candidate among the skeleton endpoints, so re-ranking
  cannot fix them.

### 2.3 Two reads (A11, as ruled)

- **Adopted as ruled:** each read is its own training sample, with name disagreements `ignore`, and each
  read keeps its own extent.
- **Withdrawn:** v3's union-for-branches / ignore-for-jitter lumen rule. It needed an unmeasured
  branch/jitter classifier, and A11 already covers the case.
- **Bridge's remaining part:** `decisions.py`, the five-decision extractor, used as the adjudication
  trigger (A11), plus the A12 decision-vs-diffuse attribution on wave 1. The ≥ 80 % expectation stays
  pre-registered.

### 2.4 The Trillium experiment (A13), revised

`trillium/bridge/` now decides by itself, from what exists:

| Found | Runs | GPU |
|---|---|---|
| Atlas manifest / work dir with val softmax | score D/R/H/O on Atlas's 80 val predictions against Atlas's own proxy labels | ≤ 4 h job (scoring on its 24 cores) |
| Atlas checkpoint but no softmax | re-predict Atlas's val cases with `--save_probabilities`, then score | ≤ 4 h |
| Atlas job still queued | same job, `--dependency=afterany` on Atlas | ≤ 4 h |
| nothing from Atlas | the original training run (~19.5 h) | ≤ 24 h |

Every path was dry-run on CPU here: both case layouts, both Atlas states, and Atlas's own fake run, which
was correctly rejected (0-byte checkpoint). Orientation of nnU-Net's softmax export was verified (argmax ≡
segmentation, 100 %). See [[Bridge - PENDING Trillium run - does the namer or grammar decoding beat a direct model's own names]].

## 3. Evaluation

- The master's (A1, A9, A10).
- Bridge's decision is the A7 rule on the A13 run, confirmed on R1.
- **Pre-registered reading** (unchanged from the pending note):
  - R − D or H − D with CI > 0 and no extra swaps → ship;
  - O − D < 0.01 → the thesis is closed;
  - D swaps along long vessels → H/R priority up.

## 4. Evidence (quoted under D0, D1, D1b)

| Claim | Number | Note |
|---|---|---|
| Namer on the binding convention, held out | 88.2 % fully right of 76; swaps 7.9 %; pooled 97.7 % | [[Bridge - Under the binding ramus rule the namer gets 88 percent of unseen thick-mask cases fully right]] |
| Ostium vs aorta-contact truth | 90.7 % ≤ 5 mm (172 cases) | same note |
| E2E on real (thin-convention) stage-1 output, all classes | namer − oracle = −0.010, CI [−0.016, −0.005], 21 cases, 0 swaps | [[Bridge - On real stage-1 output, the two-stage namer is within 0.01-0.03 tree-F1 of perfect naming]] |
| Thin-lumen naming ceiling | 0.973 over all 160 test cases | same note |
| Two-namer disagreement is decision-shaped | 87 % (99.7 % held-out) | [[Bridge - Naming disagreements between two namings of the same lumen sit in five discrete decisions]]; stand-in, not human reads |
| Aorta-preferred ostium | no change in 39 cases | new note, above |

## 5. Risks

| Risk | Detected by | Response |
|---|---|---|
| Atlas's run does not produce a usable checkpoint or softmax | `atlas_link.py` | falls back to the training run (≤ 24 h) |
| Scoring on Atlas's proxy, Atlas's ostium | the A9 provisional flag | paired differences only; confirm on R1 |
| H's LM prior is mis-set for real softmax | per-class tF1 in SUMMARY.md (LM separately) | reported, not tuned on the val set |
| Human disagreement is diffuse | A12 report | A11 voxel rule carries it; decision extractor stays a trigger only |

## 6. Comparison

- **Master:** unchanged. v4 is a measurement plan for A7 and a trigger for A11.
- **Delta:** its run is also A13-eligible; the two inference-only jobs could share the same Atlas softmax.
- **Crucible:** its fusion simulation is complementary; nothing here competes with it.

## 7. Cost

- **GPU:** ≤ 4 H100-h in A13 mode (was ~24 h), or ≤ 24 h only if no Atlas run exists.
- **CPU and human:** unchanged from v3; no extra human time.

## 8. Changes since v3

- `trillium/bridge` has an A13 inference-only mode, chosen automatically, and is re-dry-run.
- H unary and LM prior fixed after the dry run.
- Aorta-preferred ostium implemented and measured: a no-op, kept as a flag. The aorta-contact candidate is
  proposed instead.
- v3's lumen-extent rule withdrawn in favour of A11.
- No new claim of superiority over the master.
