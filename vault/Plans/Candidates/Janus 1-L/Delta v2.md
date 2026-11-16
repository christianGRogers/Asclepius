---
tags: [plans, candidate, janus1-L, track-1L, round2, trillium, four-class, D45, D46, locked100, ensemble, lumen-width]
author: Delta
track: 1-L
round: 2
version: 2
updated: 2026-11-13
issue: christianGRogers/Asclepius#302
---

# Delta v2 (track 1-L): make the a1 + a2 ensemble the one candidate, carry t\* by width rather than by threshold, and freeze #306

## 0. Position

**I accept the round-1 ruling.** Crucible v1 as amended (L-A1 to L-A12) is the plan. D46 settles the lead's
questions Q1–Q8, and I build on both. Two parts of Delta v1 are withdrawn:
- its superiority-first ladder (E, then a1, then Janus 0);
- its E − a1 test.

This version answers every item of [[Janus 1-L Round 1]] §5.

| §5 item | Delta v2's answer | Where |
|---|---|---|
| 1. The ship candidate | **C = E** (mean softmax of a1 and a2) at t_C, in a1's place in the same H1–H3 sequence. a1 is never tested, so there is still one look. Pool fine-tunes start from **both** members (cost-neutral against A37's two runs) | §1 |
| 2. The H1-pass/H2-fail branch and the wording | Adopted if H1's lower bound is > −0.015 (D46 Q4), worded "non-inferior, not shown better", exported at t_C. The wording of every outcome is fixed in a table | §2 |
| 3. The transfer of t\* | **Rule T:** C's threshold is chosen so that its width on the centreline it shares with Janus 0 at t\* matches Janus 0's, on **D60**, 60 unlabelled quality-0 cases neither model trained on. Frozen before the look | §3 |
| 4. Job 0 | Not run yet. A table says what each result changes. The MDE is restated by a script from Janus 0's baseline alone | §4 |
| 5. The 60-case decomposition | `decompose60.py`, written and self-tested. The tuning 60 only. A pre-registered rule says which result earns an arm | §5 |
| 6. The fallback when H1 fails | Pre-register **the trigger and the vehicle now, launch only on the trigger**: S = from scratch on the 620 at 0.5 mm, triggered only by the warm-start signature. 0.45 mm is not pre-registered (round 3, on Job 0's numbers) | §6 |
| 7. #306, frozen | The interface, every mode's commands, the self-tests, and the trainer diff, done here by reading both trainers | §7 |
| 8. D28 and naming | a2 runs (D46 Q5) and is a member of C (D46 Q6). This reading needs the lead's confirmation (Q-L1). C is read as Janus 1-L.1 | §8 |

**New evidence this round** (CPU; code in `experiments/Delta/j1l_r2/`). No sealed case, no locked-100 number, no
image and no label was opened.
- [[Delta - Making the two-run ensemble the one candidate costs no look and no training, and never lowers the locked 100's power]]:
  - E is never worse than a1 at the decision, and usually better in both directions;
  - a correction to my own round-1 false-alarm figure for L3.
- [[Delta - t-star transfers to Janus 1-L by matching width on the shared centreline of unlabelled quality-0 cases, not by freezing the threshold]]:
  - D60, derived from ids;
  - Rule T, self-tested;
  - a phantom where a frozen t\* loses 0.05–0.07 Dice when the candidate's calibration moves, and Rule T does not.
- `decompose60.py`: item 5's script. Its recall and precision are asserted equal to the frozen `tree_f1`'s.
- `mde_from_job0.py`: item 4's MDE restatement.
- The trainer diff (§7.3), by reading `icx4_trainers.py` against the segtrain trainers.

## 1. The ship candidate: E, tested in a1's place (item 1)

### 1.1 The rule

- **C = E at t_C.** E is `nnUNetv2_ensemble` of a1's and a2's saved softmax: the mean of the probabilities, which is
  what `nnUNetv2_predict -f 0 1` computes. t_C comes from Rule T (§3).
- **C replaces a1 in H1–H3** exactly as L-A5 states them: same margins, same guards (class, L3, FP ≤ 1), same scorer,
  same bootstrap.
- **a1 is not tested.** a1, a2, a1 at argmax and E − a1 are reports (L-A6). The ruling's one look per candidate
  model (L-A7) holds, because there is one candidate model.
- **If a2 does not finish** (the run fails and its chained resume fails too), C reverts to **a1 at t_C**, with Rule T
  run on a1. This is decided before any locked-100 number exists, from the training logs alone.

### 1.2 Why E, and what evidence the pre-registration needs

Round 1 asked for "the E − a1 evidence a pre-registration needs". My answer: **none on the locked 100.** E is not
chosen over a1 on data. It is chosen because its decision has better operating characteristics, with no assumed gain.
Simulated with the real heavy-tailed noise of the one warm sibling pair, at n = 100:

| Setting | True Δ | P(H1): a1 → E | P(adopt under Q4): a1 → E | P(H3): a1 → E |
|---|---|---|---|---|
| Round 1's optimistic spread, A37's σ_g, E halves per-case noise | 0 | 0.84 → **0.93** | 0.73 → **0.82** | — |
| | +0.01 | 0.96 → **0.996** | 0.92 → 0.98 | 0.58 → **0.64** |
| | −0.02 (a worse model) | 0.29 → **0.24** | 0.16 → **0.10** | — |
| E no better per case (φ = 1), no run offset (the worst case for E) | any | identical | identical | identical |
| Pessimistic spread, σ_g, φ = 0.5 | 0 | 0.63 → 0.69 | 0.50 → 0.52 | — |

- **No mean ensemble gain is assumed anywhere.** All of E's advantage comes from two sources:
  - it halves the run lottery: a model decision ships one draw of the run offset g, and E ships the average of two;
  - it shrinks per-case noise when the members' errors differ.
- **The cost of being wrong about E** is "E fails H1 where a1 would have passed": at most 3 % for any true Δ ≥ 0
  (7 % pessimistic).
- **External direction:**
  - nnU-Net's default inference is an ensemble of folds (Isensee et al., arXiv:1809.10486, §2.4, quoted in Delta v1);
  - Mehrtash et al. (TMI 2020) find ensembling improves Dice (M = 50; Foxtrot v1's reading, which round 1 checked).
  Neither gives a tree-F1 number at M = 2, and none is claimed.
- **The real risk is topological.** A thin segment that one member keeps and the other drops can fall below threshold
  in the average. That is exactly what H1's class and L3 guards test on C. Since C is E, those guards test E itself.

D46 Q6 bounds this: an ensemble is acceptable "if round 2 pre-registers it". This section is that pre-registration.

### 1.3 Inference cost

- E is two forward passes: about 1 extra GPU-minute per case.
- About 3–4 extra GPU-h to predict all 1000 cases for prelabels.
- No extra training: a2 runs anyway (D46 Q5).

### 1.4 The base for pool fine-tunes

**When Round 10's pool stage runs from Janus 1-L** (L-A11), its two primary runs (A37's a1 and a2) start from **E's
two members**:
- pool run 1 from a1;
- pool run 2 from a2.

**The pool candidate is E′**, their ensemble. It is judged against E by A38 as amended in L-A11:
- G1 is on D35, and its replicate clause becomes "both members' Δ > 0";
- G2 and G3 (in L3's form) are on the locked 100.

**Cost:** this costs nothing over Round 10's design, which already runs two primary pool runs. The pool stage's b arm
(1e-3) starts from a1, as a single network.

**If only one pool run is affordable,** it starts from a1, which is pre-registered and never best-of. It is judged
against E, the shipped model, so it must make up E's averaging advantage. That is the honest comparison.

If Janus 0 stays (no adoption), the pool stage starts from Janus 0, as in Round 10.

## 2. The verdict branches and their wording (item 2)

Under D46 (Q3 yes, Q4 yes), in the fixed sequence of L-A5. **C is always exported at t_C.** A C that is adopted is
adopted as the candidate was defined. It is never re-exported at argmax afterwards: that would be a second candidate.

| Outcome | Verdict | Wording (Q7 names) |
|---|---|---|
| H1 fails | Not adopted; Janus 0 stays | "Janus 1-L.1 was not shown non-inferior to Janus 0 in tree-F1 (Δ m [lo, hi]; margin −0.02), or failed the class, recall or FP guard named. Janus 0 remains the model." G5 lists the worst cases of any class with point Δ < −0.05. §6 says whether S is triggered |
| H1 passes, lower bound in (−0.02, −0.015], H2 fails | Not adopted | "Non-inferior at 0.02 only, not shown better; below the adoption margin of 0.015 (D46 Q4). Janus 0 remains" |
| H1 passes, lower bound > −0.015, H2 fails | **Adopted** (D46 Q4) | "Janus 1-L is non-inferior to Janus 0 in tree-F1 at a margin of 0.015 (Δ m [lo, hi]) and passed the class, recall and FP guards; it was not shown better in lumen width or tree-F1. Adopted for its larger training set." CONSORT form: margin pre-specified, superiority claimed only from the same interval (Piaggio et al., JAMA 2012, as Bridge cites) |
| H1 and H2 pass, H3 fails | **Adopted** (D46 Q3) | "Janus 1-L is better than Janus 0 in lumen width: whole-tree Dice +d [lo, hi]. It is not worse in tree-F1 (Δ m, lower bound > −0.02), and passed the class, recall and FP guards. A tree-F1 gain was not shown. Of the Dice gain, a share s comes from the export threshold alone (Janus 0 at t_C against Janus 0 at argmax, report)" |
| H1, H2 and H3 pass | **Adopted** | As above, "… and better in tree-F1 (Δ m, lower bound > 0)" |

**In every adopted wording:**
- "Janus 1-L is a two-network ensemble of fine-tunes of Janus 0, exported at foreground threshold t_C".
- t_C, and whether Rule T moved it from t\*.
- L3's stated false-alarm rate (3–8 %; up to 19 % under a broad shift).
- The val-80 and locked-20 parts, with any sign reversal reported and not acted on (A26).

**One addition to L-A6:** the report prints each class's excess kurtosis of the recall Δ, so a reader can see
whether L3 fired in the regime its false-alarm rate was measured in.

## 3. The transfer of t\* (item 3)

**The problem.** t\* is chosen on Janus 0. C trained on the tuning 60, so its own best threshold cannot be measured on
them. No other labelled case is left outside the locked 100.

A frozen t\* is exactly right only if C's probabilities fall off across the rim as Janus 0's do. In the phantom, a
frozen t\* costs:
- 0.053 Dice when C's boundary is softer;
- 0.066 when C has learned the width itself, which is the case H2 hopes for.

**Rule T (pre-registered; `rule_t.py`):**
- **Data: D60.** These are 60 unsealed, non-development ImageCAS quality-0 cases.
  - They have no ImageCAS-X label, and no Janus model trained on them.
  - They are not locked, not sealed, not pool, not D35, and not in Janus-M's sets.
  - They are derived from ids (`drift_set.py`; pin `916e8a18…004e`). Their CTs are already on Trillium.
- **Reference:** Janus 0 at t\* on D60. Its skeleton gives the centreline, and the EDT on it gives the local radius.
- **Measure:** for each t in the grid {0.60, …, 0.25}, the 10 %-trimmed mean of C(t)'s local radius minus Janus 0's,
  on the centreline points both cover, pooled over D60. This is dr(t), in mm.
- **Choice:** t_C is the t ≤ 0.50 with the smallest |dr|. Ties within 0.005 mm go to t\*, then to the larger t.
- **Scope:**
  - Rule T applies only when t\* is Rule W's Dice optimum, not held back by a guard.
  - Otherwise t_C = t\*, as the ruling has it now. A guard-limited Janus 0 at t\* is not the width to copy.
- **Freeze:** `rule_t.json` is posted on #302, with its sha256 and `select.json`'s sha256, **before** `collect`
  computes any locked-100 number of C. `collect` refuses unless the posted sha256 is passed to it (§7).

**How a calibration shift shows:** as dr(t\*), in mm, before the look, with per-case values. After the look, L-A6's
"C's Dice and volume ratio at every t" shows whether Rule T chose well. It is a report, never a re-choice.

**What Rule T cannot see:**
- a shift that exists on the locked 100 but not on quality-0 images (a domain caveat);
- a width error Janus 0 at t\* already had.
Both are stated in the verdict.

**Why not the alternatives:**
- **Volume matching** is wrong when extent changes (phantom: a 0.977 against 0.984 Dice loss).
- **Choosing on halves of the locked 100** is a look (L-A4).
- **Re-running Rule W on C's tuning-60 probabilities** reads a model on its own training cases.

**Cost:** about 0.5 GPU-h (D60 for Janus 0, a1 and a2 with probabilities). E's probabilities are the average of the
members', so there is no extra pass.

## 4. Job 0 has not run: what each result changes (item 4)

The lead runs Step T and Job 0 (D46 Q1, Q2). Every row below is decided now, so Job 0 cannot be read selectively.

| Job 0 result | What changes |
|---|---|
| **L0 fails** (val-80 macro off 0.909 by more than 0.003, a class off by more than 0.01, or fewer than 95 % of cases within 0.01 of Fir) | Stop (L-A8). Nothing below is read. The PM diagnoses: aortas, CT layout for `pool_thick`, nnU-Net version, `nnUNet_compile`, the class-weight file (§7.3). #306 is not built until L0 passes |
| **t\* = 0.50 and Dice peaks at 0.50** | The export lever is empty for Janus 0. Rule T still runs, and carries Janus 0's argmax width to C. H2 then tests the network alone. The 0.45 mm question (Crucible §7) goes to round 3 with this number |
| **t\* = 0.50 held by a guard** (a lower t has more Dice but fails tF1, FP or recall) | t_C = t\* (Rule T out of scope). The guard that bound is named on #302. If it is FP, the dim components beside the tree are a calibration question for round 3 (Crucible §7's temperature check on the tuning 60) |
| **t\* in {0.45, 0.40, 0.35}, Dice-bound** (Crucible's and the phantom's prediction) | The plan as written. Rule T decides whether C needs a different t |
| **t\* = 0.30, or FP rises at every t < 0.5** | Rim miscalibration, as the ruling says. Rule T's grid already reaches 0.25, so a C that is sharper than Janus 0 can follow. Round 3 looks at calibration on the 60 before #306 freezes t |
| **Dice at t\* still more than 0.03 below 0.934, with volume ratio ≥ 0.95** | The grid binds (Crucible §7). The 0.45 mm run becomes a round-3 proposal, not a fallback (§6) |
| **Dice at t\* minus Dice at 0.50 on the 60 is < 0.003** | Below the locked 100's Dice MDE (0.003–0.006). H2 will likely fail on the threshold alone, and the D46 Q4 branch becomes the expected verdict. Stated on #302 before training |
| **Janus 0's locked-100 per-case SD** | `mde_from_job0.py` restates the MDE for a1 and E (tF1 and Dice). Margins and rules do not change (L-A7). If the tF1 MDE for E is above 0.025, the verdict text says "under-powered", as Bridge proposed |
| **`decompose60.py` output** | §5 |

## 5. The 60-case error decomposition (item 5)

**The script:** `experiments/Delta/j1l_r2/decompose60.py`, self-tested on the scorer's synthetic tree.
- It uses the frozen metric through icx4's `tf1_score`: A1c `24441cf8…5254`, the same crop, ostia and flags.
- It re-derives every class's tree-F1 recall and precision from tree_f1's own pieces, and **asserts they equal**
  `tree_f1`'s before splitting them.
- **It refuses every case outside the tuning 60.** The locked 100 is never decomposed.

**Recall categories** (reference centreline of class c):

| Category | Meaning |
|---|---|
| hit | Predicted c, connected to an ostium |
| naming | Another vessel class, connected |
| cut | A vessel, but its piece does not reach an ostium |
| miss_near | Not drawn, but vessel within 1.5 mm |
| miss_gap | Not drawn, inside the tree |
| miss_tip | Not drawn, the run reaches a tip |

**Precision categories:** correct, naming, out_near (within 1.5 mm of the reference) and out_far.

**Groups:**
- **breaks** = cut + miss_gap;
- **extent** = miss_tip;
- **naming** = both naming terms;
- **width/offset** = miss_near + out_near;
- **extra** = out_far.

For each group, it reports the mean tF1 gain if that group alone were fixed, per class and macro.

**The lead's command** (Trillium login node, after Job 0; CPU, about 20 min):

```sh
R=$SCRATCH/asclepius/repo; W=$SCRATCH/j1l_job0; J0=$SCRATCH/janus0
source $HOME/icx14-venv/bin/activate && git -C $R pull --ff-only
python $R/experiments/Delta/j1l_r2/decompose60.py --selftest
for t in 0.50 $(python -c "import json;print(json.load(open('$W/select.json'))['chosen_t'])"); do
  python $R/experiments/Delta/j1l_r2/decompose60.py --pred $W/thr/t$t --icx $J0/icx --aorta $J0/aorta \
    --layout $W/layout.json --lists $R/experiments/Crucible/j1l_r1/lists.json --out $W/decompose60_t$t.json --np 8 \
    | head -80
done
```

**Post on #302:** the two printed `summary` blocks.

**Pre-registered reading.** It decides nothing about the first jobs, and only what a later round may propose.
- **A group is worth an arm** only if fixing it **entirely** gains ≥ **0.03 macro** tF1 on the tuning 60
  (`worth_an_arm`). A lever that fixes half its group then moves macro tF1 by about 0.015, which is within the locked
  100's model-decision MDE (0.011–0.021). Anything less cannot be seen.
- **Which lever fits which group:**

| Group | Lever for a later round | Why |
|---|---|---|
| extent | A Skeleton Recall arm (Atlas v1's b) | It recovers branches |
| breaks | **Not** a topology loss | On ImageCAS and ImageCAS-X these recover branches but do not connect them; Skeleton Recall doubled disconnected components (BCS, Table 2; Delta's verification note). A connectivity lever needs its own evidence |
| naming | Class-weighted CE (icx4's hook) or the namer | — |
| width/offset | The threshold, already in the plan | t\*'s run shows how much it removes |
| extra | FP work (A15) | — |

- **LCx is read first** (Janus 0's weakest class, 0.857). An LCx-only group gain counts at its macro share.

## 6. The fallback when H1 fails (item 6)

**Pre-register now: the trigger, the vehicle and its look. Launch only on the trigger**, and only with the lead's
allocation. Leaving it to the round after the result would let the result choose the fallback.

| H1 fails because | Then |
|---|---|
| **The macro bound** (≤ −0.02), **with both a1 − J0 and a2 − J0 point Δ < 0** (the warm-start signature, Ash & Adams) | **S is triggered:** one from-scratch run on the 620 at 0.5 mm. Janus 0's plans byte-identical (so the normalisation and t\*'s grid are unchanged). Janus 0's own recipe (`nnUNetTrainerICX4`, 1000 epochs), ≈ 50 h at 181 s/epoch, three chained jobs, ≈ 53 GPU-h |
| The macro bound, with the members disagreeing in sign | Not S. The warm-start penalty is not shown, and σ_g is large (A37's ≥ 2-runs rule applies). Round N+1 |
| A class guard, L3 or FP, with the macro bound passing | Not S. G5's class review and the decomposition (§5) first. Round N+1 |

**S's look:**
- **Candidate:** S (single network) at t_S, with Rule T run on S.
- **The test:** the same H1–H3 sequence against Janus 0, read once.
- **The accounting:** it is the track's second candidate look. Under the fixed sequence, at most one of the two can be
  adopted, so the family-wise one-sided error of a false "better" claim is at most 2 × 2.5 % = 5 %. The verdict says
  so.
- **Name:** Janus 1-L.2.
- **Reports:** a1 − S and E − S (the warm-start penalty measured directly).

**Not pre-registered: the 0.45 mm run.**
- It changes the grid, so neither the warm start nor t\* carries over.
- Its trigger is a Job 0 result (§4), not an H1 failure.
- It goes to round 3 as a proposal, once Job 0's numbers exist.

## 7. #306, frozen (item 7)

#306's body is Delta v1's. It is replaced by this section, which takes in L-A2, L-A9, L-A10 and D46. Built only after
the round that rules the plan converged (round 3 at the earliest).

### 7.1 Interface: `trillium/janus1l/janus1l <mode>`

**Environment:**
- `JANUS0=$SCRATCH/janus0` (Step T's folder);
- `JOB0=$SCRATCH/j1l_job0`;
- `J1L_WORK=$SCRATCH/janus1l`;
- `JANUS1L_DRYRUN=1` (prints, submits nothing).

| Mode | Does | Job | GPU-h |
|---|---|---|---|
| `check` | All self-tests (§7.2), then a dry run: prints the split pins, `select.json`'s sha256 and t\*, Janus 0's sha256, the plans sha256 (must equal Janus 0's), D60's pin, every SBATCH header | login | 0 |
| `prep` (P) | Dataset 718: the 620 + the locked 100, named `cNNNN` (so `refuse_sealed` maps every id), labels by `territory.to_four`. Janus 0's `plans.json` copied with `nnUNetv2_move_plans_between_datasets`; `nnUNetv2_preprocess` only. **No `plan_experiment`, no fingerprint.** `splits_final.json`: two identical entries | CPU job | ≈ 1 |
| `train` | a1 (fold 0) and a2 (fold 1), concurrent: `nnUNetTrainer_janus1l` (§7.3), `SEGTRAIN_FINETUNE_FROM=$JANUS0/…/checkpoint_final.pth`, `SEGTRAIN_CT_WINDOW=off`, `SEGTRAIN_MAX_SECONDS` = walltime − 30 min, chained `--c` if needed (at most one more each) | 2 × 23:50 | 2 × 12.6 |
| `predict` | `afterok` both. Folds 0 and 1 separately, with `--save_probabilities --disable_tta -chk checkpoint_final.pth`, on the locked 100 and D60. Janus 0 on D60 likewise. E = `nnUNetv2_ensemble` of the two fold outputs (`--save_npz`). Threshold exports with Crucible's `threshold_export.py` on the Rule T grid for a1, a2, E on D60, and Janus 0 at t\*. The locked-100 exports are written for a1, a2 and E on the grid **and not scored**. The npz files are deleted after export | 6 h | ≈ 3 |
| `transfer` | `rule_t.py` for C (E, or a1 if a2 failed, §1.1). Prints `rule_t.json` and its sha256, and **stops** | login | 0 |
| `collect` | Refuses unless `J1L_TRANSFER_SHA` equals `rule_t.json`'s sha256 (the value the lead posted). Scores C at t_C and the reports (L-A6) on the locked 100 with `r9_score_icx4.py`; Janus 0's baseline is Job 0's file. Applies L0's re-check, H1–H3 with L3 (§7.2) and the verdict table (§2). Writes `results/SUMMARY.md` and `results/verdict.json` | login | 0 |
| `status` | s/epoch, epochs done, chain state, which files exist | login | 0 |

**The lead's commands:**

```sh
cd $SCRATCH/asclepius && git -C repo pull --ff-only && source $HOME/icx14-venv/bin/activate
pip install --no-deps -e repo                                    # segtrain into the icx14 venv (L-A10)
rm -rf experiments/janus1l && cp -r repo/trillium/janus1l experiments/janus1l && cd experiments/janus1l
JANUS0=$SCRATCH/janus0 JOB0=$SCRATCH/j1l_job0 ./janus1l check     # post the printout on #302
JANUS0=$SCRATCH/janus0 JOB0=$SCRATCH/j1l_job0 ./janus1l prep      # then, when it ends:
JANUS0=$SCRATCH/janus0 JOB0=$SCRATCH/j1l_job0 ./janus1l train     # a1, a2, and predict (afterok)
./janus1l status                                                 # expect ~181 s/epoch
./janus1l transfer                                               # post rule_t.json and its sha256 on #302
J1L_TRANSFER_SHA=<the posted sha256> ./janus1l collect           # post results/SUMMARY.md and verdict.json
```

**Send back on #302:**
- `check`'s printout;
- `status` after the first 20 epochs;
- `rule_t.json` + sha256;
- `results/` (no weights, no volumes);
- the `.out` of any failed job.

**Keep** both `checkpoint_final.pth` in `~/projects/def-aso22/$USER/janus1l/` (Step T's pattern).

### 7.2 Self-tests (`./janus1l check` runs them all; each must fail on a broken input)

1. **Split:** the file sha256 `19b832fe…4dd3` and both list pins (L-A1). The fixture is the file with one id moved.
2. **Seals:**
   - `refuse_sealed` on dataset 718's ids (A14 and D27);
   - `rule_t.py` and `decompose60.py` refuse ids outside D60 or the tuning 60;
   - the fixture is a sealed id, then a locked id, in training.
3. **No plan step:** dataset 718's `plans.json` sha256 equals Janus 0's, and the launcher has no
   `plan_and_preprocess`/`plan_experiment` call. The fixture is a plans file with one changed percentile, which
   `finetune_load` must refuse.
4. **Strict load:** `finetune_load` bitwise on a 5-epoch CPU smoke (`nnUNetTrainer_segtrain_finetune_5epochs`).
5. **t\* applied:** `collect` reads t_C from `rule_t.json` only, and refuses on a sha256 mismatch. The export at t_C
   is byte-equal to `threshold_export.py`'s.
6. **L3 reads the right field.** The decision scorer (`r9_score_icx4.py`) writes per-class tree-F1 `recall` against
   ImageCAS-X. It does **not** write `split.recall_icx_traced`, which came from atlas3's scorer when the reference
   was ImageCAS. With ImageCAS-X as the reference the two are the same quantity.
   - `collect` implements L3 on `recall`. The fixture is a uniform −0.03 LCx recall loss, which must fire. A
     heavy-tailed null drawn from `ensemble_power.py`'s sibling differences must mostly not fire.
   - **Crucible's `decide.py gate` implements A38's G3 as written, not L3, and has no −0.015 branch. `collect` must not
     reuse it unchanged.**
7. **Ensemble:** `nnUNetv2_ensemble` of two copies of one fold's npz reproduces that fold's segmentation.

### 7.3 The trainer diff (done here by reading the code)

Compared: `nnUNetTrainerICX4` (`trillium/icx4/lib/icx4_trainers.py`, Janus 0) against `nnUNetTrainer_segtrain_finetune`
→ `_coronary` → `nnUNetTrainer_segtrain` (`src/segtrain/nnunet_ext/`).

| Setting | Janus 0 (ICX4) | A17a | Same recipe? |
|---|---|---|---|
| Loss | nnU-Net default DC + CE, deep supervision; **optional class-weighted CE if `$W/ce_class_weights.json` exists** | nnU-Net default; no weight hook | Yes, **if Janus 0 ran without the file.** Step T must post `ls $SCRATCH/icx4/ce_class_weights.json` (expected: absent). If present, 1-L must copy its weights |
| Sampling, oversampling | nnU-Net default (uniform cases, `oversample_foreground_percent` 0.33) | Default | Yes |
| Augmentation | `nnUNetTrainerNoMirroring` (mirroring off, `inference_allowed_mirroring_axes = None`) | The same override in `_coronary` | Yes |
| Optimiser | SGD, Nesterov 0.99, nnU-Net weight decay, lr 1e-2 | Same SGD, peak 1e-2 | Yes |
| Schedule | Poly per epoch over 1000 epochs | 2500-iteration warm-up, then poly per iteration, 250 epochs | Intended (L-A2) |
| Iterations, batch, patch | 250 × batch 2, 256³ (from the plans) | Same (plans byte-identical) | Yes |
| Per-epoch validation | 50 patches on fold val | Same; fold val = the locked 100 (display only) | Yes |
| **Final validation** | Skipped when a chunk stops early; otherwise full validation | **Always runs, and saves val softmax** (`SEGTRAIN_SAVE_PROBABILITIES=1`), computing nnU-Net's `summary.json` Dice **on the locked 100** at argmax before Rule T is frozen | **Change:** `nnUNetTrainer_janus1l` (a 10-line subclass) skips the final validation. Prediction is `predict`'s job. No locked-100 number appears before `collect` |
| Deadline/chain | `ICX4_DEADLINE`; `on_train_end` writes `checkpoint_final` | `SEGTRAIN_MAX_SECONDS`, pause without `on_train_end`, `--c` resumes from `checkpoint_latest` | Equivalent; the launcher uses segtrain's |
| Checkpoint every | 10 epochs | 50 (set `SEGTRAIN_SAVE_EVERY=10`) | Not a recipe setting |
| Sealed guard | None in the trainer | `refuse_sealed` on train + val ids | Stricter; ids must be `cNNNN` |
| Window check | None | `SEGTRAIN_CT_WINDOW=off` (L-A2) | — |
| `nnUNet_compile` | `f` (job_body) | Set `f` in the launcher | Must match |

**Conclusion:**
- "The same recipe" holds except the intended schedule.
- One thing to check in Step T: the class-weight file.
- One change to make: skip the final validation.

### 7.4 Cost

| Job | GPU-h |
|---|---|
| Job 0 (Crucible's, unchanged) | 3–4 |
| P | ≈ 1 |
| a1 + a2 | ≈ 2 × 12.6 = 25.2 (+ ≈ 1 if one chains) |
| predict (locked 100 × 2 folds, D60 × 3 models) | ≈ 3 |
| transfer, collect, decompose60 | 0 (CPU) |
| **Total** | **≈ 33–35**, ceiling ≈ 60 (L-A9). S, only on its trigger: +≈ 53 |

## 8. D28 and naming (item 8)

- **D28/D46 Q5:** a2 runs, and σ_g = |a1 − a2|/√2 is reported for 1-L and 1-F, with A37's ≥ 2-runs rule if
  |a1 − a2| > 0.02.
- **D46 Q5 says a2 is "report only, never shipped". D46 Q6 accepts "a two-network ensemble" if pre-registered.** I
  read them together:
  - a2 is never shipped **alone or in a1's place**, which is the best-of that A37 forbids;
  - as one of E's two members it is shipped under Q6.
  This is the lead's to confirm (Q-L1). If the lead reads Q5 as excluding a2 from any shipped model, C = a1 at t_C
  (with Rule T on a1), and everything else here stands.
- **Naming (D46 Q7):** the candidate read is **Janus 1-L.1** = E at t_C. If adopted, it is **Janus 1-L**. a1, a2, a1
  at argmax and Janus 0 at t_C are reports under 1-L.1 and take no number. S, if triggered, is **Janus 1-L.2**.

## 9. Amendments proposed to the ruling

| # | Change | Replaces |
|---|---|---|
| D2-1 | C = E at t_C; a1 at t_C if a2 fails | L-A3's "a1 is the ship candidate"; L-A5's C |
| D2-2 | Rule T on D60, frozen before `collect`; t_C = t\* when Rule T is out of scope | L-A4's "t\* applied unchanged" |
| D2-3 | Pool stage starts from E's two members; candidate E′ | L-A11's "the parent is the adopted Janus 1-L" (made specific) |
| D2-4 | The S trigger and look (§6) | §5 item 6, open |
| D2-5 | #306 as §7, including the final-validation skip and L3 on `recall` | L-A10's partial spec |
| D2-6 | L3's stated false-alarm rate: 3–8 %, up to about 19 % under a broad shift; kurtosis in the report | L-A5's "about 4 %" |

**Withdrawn from Delta v1:** the superiority ladder, the E − a1 test, rule W's "closest to 1" and its second
locked-100 test (already refused in L-A4), and "plan and preprocess dataset 718" (already corrected in L-A2).

## 10. What would change this plan

| Observation | Then |
|---|---|
| Job 0's rows (§4) | As §4 says |
| The lead reads D46 Q5 as excluding a2 from any shipped model (Q-L1) | C = a1 at t_C; Rule T on a1; §1.4 becomes "pool runs start from a1" |
| `rule_t.json`: \|dr(t\*)\| > 0.05 mm | A real calibration shift. t_C moves, and the verdict says by how much. A shift that big also says C's rim is not Janus 0's: round 3 decides whether Rule T stays the rule for pool fine-tunes |
| `rule_t.json`: dr has no minimum inside the grid (all one sign) | t_C at the grid edge (0.25 or 0.50). Stated; the edge is not extended after the fact |
| a2 fails twice | C = a1 (§1.1). No ensemble, no σ_g; D28's replicate is reported missing |
| `decompose60`: a group passes `worth_an_arm` | That arm is proposed in round 3 (§5's mapping), never added to the first jobs |
| S's trigger (§6) | S runs only with the lead's allocation. Its look is the track's second, and the verdict says so |

## 11. Questions for the lead

- **Q-L1 (reads D46 Q5 and Q6).** Is a2 allowed into the shipped model as one of the ensemble's two members, with
  "never shipped" meaning never alone and never in a1's place?
  - **Recommended: yes.** It is the reading under which Q6 can apply at all. E's members are a1 and a2 (L-A3).
- **Q-L2 (allocation, no D-number).** If S's trigger fires, will you run S (≈ 53 GPU-h on Trillium) before round N+1
  rules?
  - **Recommended: yes**, because the trigger and the look are fixed now. If not, S goes to round N+1 like any other
    proposal.
- **Action, not a decision (with Step T).** Post `ls $SCRATCH/icx4/ce_class_weights.json` and Janus 0's
  `nnUNet_compile` setting (§7.3).

## 12. Evidence and code (`experiments/Delta/j1l_r2/`)

| File | What | Checked |
|---|---|---|
| `drift_set.py` → `drift60.json` | D60 from ids; guards against seals, the locked 100, training and Janus-M | Run; 200 → 180 → 156 → 60; pin `916e8a18…004e` |
| `ensemble_power.py` → `.json` | C = a1 against C = E: H1, Q4, H3, H2, L3 | Run; t bound = bootstrap in 97 % of draws |
| `l3_fix.py` → `.json` | L3 against L3′ under heavy and Gaussian shifts | Run |
| `transfer_phantom.py` → `.json` | Frozen t\* against Rule T against volume match | Run (≈ 3 min) |
| `rule_t.py` | Rule T, for `transfer` | Self-test passes |
| `decompose60.py` | Item 5's decomposition | Self-test passes; recall and precision equal `tree_f1` |
| `mde_from_job0.py` | Item 4's MDE restatement | Run on a synthetic rows file in the scorer's format; the real input is Job 0's baseline file, which does not exist yet |

**External sources:** none new this round. Those used are cited and checked in Delta v1 §7, Bridge v1 (Piaggio et al.)
and Foxtrot v1 (Mehrtash et al.), as verified in [[Janus 1-L Round 1]] §2.
