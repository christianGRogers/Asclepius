---
tags: [plans, judgement, round10, janus, D35, D27, fir]
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Round 10 ruling

This is the first round after a four-class model came back. **Janus 0** (icx4, D34) scored val-80 decisive tF1
**0.909** [0.880, 0.932]. It passed the A26 identity check and met A15, and P2 was withdrawn ([[icx4 - Results]]). The
recipe is settled and nobody relitigates it.

All five candidates agree on the shape of what follows:
- **Janus 1** is a warm fine-tune of Janus 0, with ImageCAS-X replay;
- it is decided on a 35–50-patient D35 set against the reads, with a val-80 guard against ImageCAS-X;
- seed anchoring acts on vessel **extent**, not lumen width;
- the left-ostium residual is report-only.

They disagree on four things:
- where the D35 set comes from, and its size;
- whether the seal grows now or is sized at wave 1;
- how many runs Janus 1 needs;
- how anchoring is detected.

**The judge's checks this round:**
- **The five D35 files**, against the pinned seal (`sealed-pool-2026-10.json`, sha256 `e71141b4…0690`): the counts, the
  overlap with the seal and the extension order, and the serve positions under D23's order.
- **The five power outputs.**
- **The two paired-noise outputs.**
- **The anchoring JSON** of Bridge and Delta.
- **Two hashes:** Atlas's and Delta's proposal files hash to the sha256 their candidates state.
- **Self-tests were not re-run.** This environment has no scipy, so the Delta and Bridge self-tests could not run here.
  They run in the Fir venv.
- **No sealed case, and no read of any patient, was opened.**

## 1. Ruling: Delta v10 takes the title, as amended (A33–A44)

**Delta v10** is the plan in force. This is the first change of holder since Round 1. It wins on the three questions
that decide this round:

1. **The decision set is drawn on the right principle.** It is proportional to the primary pool, which is the seal's own
   population, so decisions are made on patients who look like the acceptance set. A draw from the 61 free patients is
   51–71 % Taiwan, from five sources. Training data drawn from the same free patients is also about 70 % Taiwan. A
   fine-tune that fits Taiwan would win on such a set and lose at acceptance.
2. **It has the only pre-read anchoring measurement that needs no new code** (Job S): TotalSegmentator's seed extent
   against ImageCAS-X on val 80. It runs now, for ≤ 1 GPU-h.
3. **It takes D28 at its word.** Janus 1 runs two seeds of the primary arm plus the 1e-3 arm.

**Atlas v12** is the most complete operational text, and its J1–J7 rules supply most of the adoption gate (A38). But
its decision set has the weakest composition. Its A31.2′ test, used alone, fires with no anchoring at all (§3.4). And
its A22′ reads more into two measured pairs than they hold (§3.3).

**Bridge v9** contributes:
- the cleanest seal-sizing rule (rule C), merged into A35;
- the strongest anchoring evidence, from 80 val trees;
- the Fir job pattern.

**Crucible v11** contributes:
- the val-80 gate's rationale: anchored reads reward shortening vessels, and ImageCAS-X does not;
- the `trillium/janus1` launcher on the proven icx4 Fir path;
- the timing reconciliation.

**Foxtrot v6** contributes:
- the model-decision versus recipe-decision distinction in A22 (A37);
- the two contouring studies that turn anchoring from a hypothesis into an expectation.

Its seal-200-now and its 50-patient set are refused (§3.1–3.2).

**One part of A33 needs the lead (Q1).** The adopted draw caps the seal's growth at 228 instead of D27's 250. Until the
lead answers, the A33 freeze covers every patient in all three candidate draws (§5, Q1). Nothing waits on that answer
except P0 and Janus 1, which wait on #116 anyway.

### Binding amendments (Round 10)

#### A33: the D35 decision set

| | Value |
|---|---|
| Population | The **161 non-sealed primary-stratum real patients** (`segtrain.pool_seal.ingest_patient`, D32/D33). **Reserve included.** Excluded: ImageCHD (D35), ImageALCAPA and the other spacing-suspect sets (D29; a mm-tolerance metric means nothing on a suspect grid) |
| Size | **35 patients.** That is D35's own 15 % of the real base of 235 non-sealed, non-ImageCHD patients. "About 50 of about 347" was a pre-D32 name-rule count (Atlas's, admitted). Going from 35 to 50 buys 0.001–0.004 of MDE once A22's seed term is in (Crucible, Delta), and 0.003 on the case term alone (Atlas: 0.018 → 0.015). D35 delegates the exact size to this round, so this is settled here and only confirmed by the lead (Q5) |
| Salt | `asclepius-decision-round10-pool:` (Delta, Atlas and Bridge use the same salt) |
| Draw | Delta's: per-source quota proportional to the source's share of the **primary pool**, by largest remainder, capped by availability, with ≥ 1 for any source with ≥ 5 eligible patients; within source, ascending sha256(salt + patient) |
| The list | `experiments/Delta/r10/d35_decision_set_proposal.json` (sha256 `1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1`): 35 patients and 51 volumes from 10 sources (Taiwan 11, cy54ttk3fj 5, EpicardialFat 4, VMR 4, Kaggle-CAD 3, CardiacCT15 2, RIDER 2, TotalSegmentator-cardiac 2, HeartSR 1, SLAWT 1). Checked here: 0 sealed; 12 free; 11 from extension positions 1–50; 12 from positions 51–100. Taiwan is 31 % of the set, against 29 % of the seal |
| Unit and scoring volume | The patient. Every volume of a D35 patient is withheld from training. **Amended from Delta:** the decisive volume is the patient's **first volume in D23's serve order** (as Bridge and Crucible do), not the lowest-hash volume, so decisions come earliest. Checked: 23 of the 35 are served by position 242, 27 by 300, 30 by 450, and all by 600. Other volumes are reported |
| Use | Decides pool fine-tune and recipe questions (A17, A22) by paired model-vs-read tF1 at A1c `24441cf8…5254`, A1 aortas, flagged trees apart (A1b). Hosts the A35 contrast and the A40 measurements. **Never trained on.** No image or per-case error list of a D35 patient is opened for tuning: decisions read only the pre-registered paired statistics (Delta) |
| Freeze | #116 copies the patient and volume lists byte for byte to `configs/segqueue14/decision-set-2026-10.json`, recomputes the scoring volume by the rule above, and pins its sha256. Refusal is by patient in `convert` and the trainer; scoring is allowed. **Until #116 merges, no pool read is exported for analysis or training.** No read exists yet, so nothing is lost |
| If the lead declines Q1 | Atlas's draw (`experiments/Atlas/r10/decision_set_proposal.json`, sha256 `bc47690c…6b042`; 35 patients, 42 volumes, outside the seal and the whole reserve) replaces it, with Atlas's pre-registered tranche 2 to 50 if the seal ends below 250. The rest of this ruling applies unchanged |

#### A34: the reserve and the extension order

- A30's extension order is kept, and the extension **skips D35 patients**, as D32 skipped sealed ones.
- **The seal file is not edited by this ruling.** The skip is applied in the one explicit seal PR that A35 triggers.
- Under A33, 23 of the order's 101 entries are D35 patients. 78 remain, so the seal can grow to **228**. That is Q1.
- **The reserve** is those 78 patients. They stay untrained, unprelabelled and uninspected (no read exported for
  analysis) until A35 has fixed the seal size. Then the entries not sealed are released to training, by an explicit PR
  to the held-out file (#116).
- The wave-1 tools (`experiments/Bridge/wave1/common.py`, `EXTENSION_RESERVED = 100`) take the reserve from the #116
  module, so there is one definition.

#### A35: the seal stays at 150 now, and is sized at wave 1 on the measured contrast (replaces A31.1's f/k trigger)

- **Why the trigger is replaced.** f and k > 1.2 fires by chance 47–71 % of the time at wave-1 sizes (Bridge's
  `trigger_false_alarm.py` and `extension_rule.json`, and Crucible's simulation). It also ignores ρ, the per-patient
  correlation between model-vs-read and inter-read, which moves P(pass) at 150 from 0.76–0.80 (ρ = 0) to 0.95–0.996
  (ρ = 0.3–0.5).
- **f and k stay as a report.**
- **When:** ≥ 50 primary, non-sealed, non-reserved patients (D35 plus trainable) have two approved reads.
- **What is computed.** For Janus 0, per patient and class:
  - d = (mean over the two reads of tF1(Janus 0 vs read)) − inter-read tF1;
  - decisive trees only;
  - centred at 0 (human level).
- **The size.** The seal is the smallest of **150 / 200 / cap** (cap = 228 under A33, 250 under the fallback) at which
  the simulated A10 (all four classes non-inferior at D6's 0.05) passes with P ≥ 0.80. This must hold at the
  **80th percentile of the patient-bootstrap SD of d** (Atlas's conservative clause, equivalent to Delta's lower 80 %
  bound).
- **Unweighted and weighted.** It is computed both unweighted and weighted to the seal's source mix (Delta). **The larger
  n of the two decides.**
- **If the cap still gives < 0.80,** the seal is the cap and the shortfall goes to the lead (D6's design is the lead's).
- **Code:** `report_wave1.py` gains this beside the f/k report (#116 item 7), from Crucible's `p_pass_d` and Delta's
  `repower_contrast.py` weighting.
- **Hard order:** the extension PR merges **before any sealed read is scored and before any reserve patient is trained on
  or inspected**.
- **Janus 1 does not wait for it.** If A35 has not run when A39's other conditions hold, Janus 1 trains without the
  reserve (Delta). Crucible's default of 200 is not adopted: waiting costs nothing.
- **Foxtrot's 200-now is refused.**
  - D27 makes extension conditional on wave-1 evidence.
  - It withholds 50 patients that a measured ρ may show are not needed.
  - It makes 250 unreachable at the same stroke.

#### A36: the Janus 1 recipe

| Item | Setting |
|---|---|
| Start | **Warm fine-tune from Janus 0's `checkpoint_final.pth`.** A17a trainer (`nnUNetTrainer_segtrain_finetune`): full load including heads, 2500-iteration warm-up, then poly. Janus 0's plans adopted field by field |
| Epochs | 250 (≈ 13.3 h at Janus 0's 192 s/epoch; one 23:50 Fir job) |
| Data | **ImageCAS-X train 560** (dataset 715's collapsed labels, replay) **+ every trainable pool read**, each read a sample (A11′). Trainable = approved reads that are not sealed, not D35, not reserved, and not spacing-suspect (until re-gridded). Non-sealed ImageCHD reads are trainable and reported apart (D29) |
| Mix | **Uniform per sample** (Bridge, Crucible, Foxtrot). Atlas's 50 % pool oversampling is not adopted: its prior is CLEAR's 50–50 split in reinforcement learning (Rolnick et al. 2019, found in the text, "CLEAR will use a 50-50 split of new and replay data"), which is not evidence for CT. Uniform is the untuned default |
| Validation | nnU-Net fold-0 val = **ImageCAS-X val 80**, never trained on. **No pool read is held out by `segtrain index`** (val and test fractions 0); D35 is the only pool hold-out |
| Task | A new **task 717** (`configs/tasks/Dataset717_*.yaml`). **Task 716 is not run for wave 1:** it has no replay and its own 30 % pool hold-out, and it refuses neither D35 nor the reserve. It stays on `dev`, marked "superseded by 717" |
| From scratch | Not for Janus 1. Costed at about 55–60 GPU-h per run against ≈ 15 warm, and below D35's resolution as a comparison (MDE ≥ 0.04 with two seeds per arm; all five agree). Kept for the lead's final-retrain question (Q7) |

#### A37: Janus 1's runs and seeds, and what A22 requires (D28)

- **Three concurrent runs**, the same data, epochs and export:

  | Run | Arm | Seed |
  |---|---|---|
  | a1 | primary (peak LR 1e-2) | 1 |
  | a2 | primary | 2 |
  | b | lr1e3 (A17b) | 1 |

  Each run is ≈ 15 GPU-h. **≈ 45 GPU-h** in all (range 40–55; ceiling 3 × 23.6).
- **Names (D34):** read in the order a1, a2, b, so they are **Janus 1, 2, 3**.
- **D28.** D28 says "the first retrained decision adds a second seed to its control". a2 is that second seed, on the
  primary arm. The alternative reading, a second from-scratch Janus 0 (≈ 60 GPU-h), measures nothing Janus 1 needs. The
  lead is asked to confirm this reading (Q4).
- **A22 is clarified** (from Foxtrot):
  - a **model decision** compares fixed checkpoints, for example "ship a1 rather than Janus 0". It uses the paired
    patient CI, and which run ships is pre-registered, never best-of;
  - a **recipe claim**, for example "this recipe beats that one", includes the seed term. That is max(measured σ from
    a1 − a2, 0.012).
- **Atlas's A22′ is not adopted.** It would drop the seed term because both measured pairs put run-to-run noise inside
  the case term. But:
  - one pair (atlas3 F1 − F0) shares seed and data stream;
  - the other (run 1 − B) differs in window, on the retired D0 labels;
  - each has 1 df.

  Bridge's bound (σ ≤ 0.012 at 95 %) stands as the floor until a1 − a2 measures it on the master family.
- **If a1 − a2 differs by more than 0.02 macro** on D35 or val 80, later recipe decisions need ≥ 2 runs per arm.

#### A38: Janus 1's adoption gate (pre-registered)

Each run is scored against Janus 0 as fixed predictions.
- On D35: model-vs-read, both reads, patient bootstrap.
- On val 80: `r9_score_icx4.py --pair`, decisive tF1 against ImageCAS-X.
- On open-36: confirmation.

| # | Check | Rule |
|---|---|---|
| G1 | Pool gain (model decision) | D35 macro Δ(a1 − Janus 0) has its **lower 95 % bound > 0**, **and** a2's Δ is > 0 (the replicate agrees in sign). Decided on the D35 patients double-read when A39 holds (≥ 25); confirmed when all 35 are read, and a sign reversal is reported, not reversed (A26's rule) |
| G2 | Forgetting (val 80) | Lower 95 % bound of Δ macro > **−0.02** (MDE at n = 80 is 0.012–0.024; Atlas, Bridge, Foxtrot), and no class mean Δ < −0.03 |
| G3 | Not learning the seed | No class's val-80 **centreline recall** against ImageCAS-X falls by more than 0.02 (Atlas J4, Crucible). A D35 gain bought by stopping where seeds stop shows here |
| G4 | Open-36 | Val-80 Δ has the same sign; a reversal is reported, not adopted (A26) |
| G5 | Class review | Any class down by more than 0.05 (point) on D35 or val 80: review that class's worst decision patients before adoption, whatever the macro says (Bridge) |
| G6 | FP (A15) | Reported on val 80 and D35. Binding only at acceptance |

**If a1 passes G1–G5,** a1 (Janus 1) replaces Janus 0 as the base. a2 is the replicate; it is never shipped in a1's
place.

**If a1 fails G2 or G3 only,** b (Janus 3) is adopted if it passes G2–G5 and its own G1 lower bound is > 0. b has no replicate, so the a2 clause does not apply (A17b fallback). b against a1 is
not a superiority test (its MDE is about 0.05), and ties go to the primary arm.

| Other outcome | Then |
|---|---|
| G1 fails | "No gain detected". Janus 0 stays; the comparison repeats at the next export under the same rules; no new arm is added |
| G2 fails in all runs | One rerun of a1 with ImageCAS-X sampled 2:1, then stop |
| Two exports without a gain, with ≥ 100 trainable primary patients | The warm recipe reopens in Round 11 |

Delta's "both pass and within 0.032, lr1e3 wins" is not adopted. It picks an arm on a difference below the set's
resolution.

#### A39: when Janus 1 starts

All of the following hold:
1. #116 is merged (with #114's guard) and P0 is done.
2. A21's dry run passes on the first real four-class double-read export.
3. **≥ 25 D35 patients have both reads approved.** Under D23's order this is about position 242–300 of 675 (checked:
   23 by 242, 27 by 300). If the lead takes Q2, it is about position 35.
4. **≥ 40 trainable primary patients have both reads approved,** ImageCHD not counted and the released reserve counted.

If A35 has not yet sized the seal, Janus 1 trains without the reserve, and the reserve joins at the next export.
Delta's ≥ 30 is not adopted: it waits until about position 450 for a 0.002 MDE gain.

#### A40: seed anchoring, measured before reads and declared on a joint signature

**Before any read: Job S** (Delta), ≤ 1 GPU-h. TotalSegmentator `coronary_arteries` (the D23 seed model) runs on the
val-80 CTs, and `seed_vs_icx.py` reports, per class:
- seed recall and precision against ImageCAS-X;
- Janus 0 against the named seed.

| Job S, per class | Reading |
|---|---|
| Seed recall ≥ 0.95 | The anchoring cost there is ≤ about 0.03 (Delta's simulation: a seed 5 mm short gives d = −0.046 / −0.061 / −0.040 in LAD / LCx / RCA; checked in `anchoring_summary.json`) |
| Seed recall < 0.90 in any class | L5 is live before wave 1, and Q3 is put to the lead then, not after reads |

Foxtrot's M1 is the same measurement and is not run twice.

**On reads: anchoring is declared in a class only when all three hold** (none suffices alone):
1. **A31.2's flag:** seed-vs-read ≥ inter-read − 0.02, LM excluded (Bridge).
2. **Reads add little to the seed:** the median read has < 10 % of its voxels outside the seed (Bridge's edit sizes;
   Delta's 10 % line).
3. **Atlas's A31.2′:** model-vs-read precision − recall < −0.03 with its patient-bootstrap CI excluding 0, **while
   inter-read precision is not also low.**

**Why the conjunction:**
- The flag fires with a near-complete seed and no anchoring (Bridge's 96 % row; Delta, seed within 5 mm).
- The precision–recall gap fires whenever the model traces further than independent reads do. The judge found this in
  Delta's own "independent" condition: a full-extent model has recall 1.000 and precision 0.920–0.944 in LAD/LCx/RCA,
  a gap of −0.06 to −0.08, with no seed at all.
- What separates anchoring is that anchored reads also agree with each other (inter-read 0.99–1.00) and add nothing to
  the seed.

All three signals and Bridge's seed-edit sizes are reported every wave, whether or not anchoring is declared. If it is
declared: L5 (Q3) goes to the lead with δ̂, G3 binds every later fine-tune, and A10's report splits the class's contrast
into its recall and precision halves.

**The annotator instruction** to trace each vessel past the seed's end, to where the lumen is no longer confidently
distinguishable, is the label protocol already. Issuing it as a SegQueue14 note is the lead's (Q6). It is internal, so
D31 does not apply.

#### A41: the A31 domain check and per-source reporting (report only)

- **The domain check:** Janus 0 against each allowed pool volume's TotalSegmentator seed, per source, from P0's
  predictions. It reports, side by side:
  - plain Dice;
  - 1-voxel-tolerant Dice;
  - volume ratio;
  - centreline recall and precision (`r10_dice_check.measure`);
  - the share of Janus 0's centreline inside the seed (Crucible).
- A source is flagged (report only) if its median tolerant Dice is below 0.75 × the pool median (Atlas), or its
  centreline-in-seed share is < 0.85 (Crucible: there, anchored reads would cost a correct model about 0.05).
- A width-only difference is not domain shift.
- **Model-vs-read per source** (A31.3) is reported with CIs, split into seen and unseen sources (Foxtrot), and decides
  nothing at 1–12 patients per source.

#### A42: the left-tree ostium residual (report only)

- Delta's `ostium_residual.py` runs in Job 0. Stage 1 reads the A29 run's `per_case.jsonl`; stage 2 opens only the val
  cases that carry the gap.
- **Paired contrasts are unaffected,** to first order: both sides of A10, and both sides of Janus 1 against Janus 0, use
  the same A1 ostium on the same reference (Bridge, Crucible).
- If most carriers root past the first bifurcation, a candidate A1b flag rule comes to Round 11 and is validated on
  open-36 (A26). A1 is unchanged.

#### A43: the Fir jobs, in order, and the role:swe issues

- **#116 is the critical path.** #114's reserve refusal is #116 item 2; close #114 when #116 merges.
- **#118's (a)–(c)** (pinned files, refusal, the replay task) are folded into #116, to build one guard and one task.
- **#118 keeps (d) and (e)** (the Fir GPU string for `segtrain scinet`, and the dry-run test). It **blocks nothing in
  this plan.**
- **Janus 1 is submitted through `trillium/janus1`** (#116 item 6). It is built on icx4's launcher, the only path proven
  on Fir, rather than through `segtrain scinet`, which has never run there.
- The jobs are §4 below.

#### A44: what carries over, changes or lapses

- **Carried:** A1/A1a/A1b/A1c (`24441cf8…5254`), A2/A15, A9, A11′, A12, A17a/b, A19, A21, A23 (report), A26, A28,
  A30's seal (150 patients, unchanged until A35).
- **Changed:**
  - A22, clarified by A37;
  - A31.1, replaced by A35 (f/k as a report);
  - A31.2, read through A40;
  - A31.3 and A31.4, through A41.
- **Closed:** A27 (Janus 0 read), A29 (P2 withdrawn), the 500-epoch fallback and Job B (D28).
- **Not adopted:**
  - Foxtrot's seal-200-now and its 50-patient D35;
  - Atlas's A22′ and its 50 % pool share;
  - Bridge's "better of W1/W2 is Janus 1" (winner's curse);
  - Crucible's two-run Janus 1 and its default seal of 200;
  - Delta's ≥ 30 start and its lr1e3 tie-break.

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence, (c) fit to D35, D27 and Fir, (d) risk/cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit (D35 / D27 / Fir) | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Delta v10** | 4.5. Allocating D35 to the seal's mix answers the question D35 exists for. Job S sizes L5 before any read. Takes D28 literally. Corrects its own Round 9 error (macro SD for a per-class contrast). Weak points: the ≥ 30-patient start (late), the lr1e3 tie-break on a sub-MDE difference, and a 0.05 L5 margin that is loose | 5. Proposal hash `1a75fe41…` verified; 35/51, 0 sealed, 23 from the reserve, as stated. `power_r10.json`: 0.803 at 150 (f = k = 1, ρ = 0) as quoted. `anchoring_summary.json`: the 5 mm row −0.046/−0.061/−0.040 as quoted. `citations.md` records its drops (Tversky & Kahneman unverified, no "anchoring in contouring" study found). The last is a search gap: Foxtrot found two such studies | 4.5 / 4 (cap 228, honestly routed to the lead) / 4.5 | 4.5. ≈ 50 GPU-h; Job S needs the TotalSegmentator licence typed by the lead | **Holds the title**, as amended |
| **Atlas v12** | 4. The most complete operating text; J1–J7 are the backbone of A38. But it draws D35 where composition is worst: 51 % Taiwan from 5 sources, with 25 of the 26 trainable patients also Taiwan. A31.2′ alone false-alarms (§3.4). A22′ overreads 1-df pairs | 4. Hash `bc47690c…` verified; 35/42, 0 sealed, one at extension position 101 (as stated). `seal_power.json` 0.789 at 150. Paired SDs 0.0382/0.0411 match. Rolnick 50–50 found in the paper (RL; Atlas says so). Ozdemir (MICCAI 2018) and Ash & Adams found | 3.5 / 5 / 4 | 4 | Lost the title. J-rules adopted (A38); A31.2′ adopted as one leg of A40; its draw is the fallback (A33) |
| **Bridge v9** | 4.5. Rule C is the cleanest statement of what A10's power depends on (s_d already contains f, k and ρ). The re-stated 250-step is ingenious but changes a pre-registered order and leaves 26 trainable. "The better of W1/W2 on D35 is Janus 1" picks a winner on the decision set | 4.5. `power_r10.json`: 0.762 / 0.996 at 150 (ρ = 0 / 0.5), reproducing Round 9's run-1 0.972. 35/47, 14 from extension 51–100. Serve positions verified (23 by 242). Anchoring rows (56 %, 34 %, 20 % seeds) match `anchoring.json`. Abdulkadir 2023 read via its abstract only (stated) | 4 / 4 (250 kept, but by re-stating the order) / 4 (janus0_pool.sh is runnable, but tied to its own reserve) | 4.5 | Rule C merged into A35; anchoring evidence and edit sizes into A40; F0 is Job 0 |
| **Crucible v11** | 4.5. It drops its own P3/P4 on costing, and its rule D and val-80 gate rationale are right. Two runs leave the primary arm without a replicate (against D28's fallback). The default seal of 200 is unnecessary | 4.5. `r10_power.json`: 0.763 / 0.995 at 150. 35/47, 23 from the reserve plus position 101. "25 of 35 by about 480 reads" verified (25 by position 242). Citations reworded after checking (Ghafoorian, M&Ms, Bouthillier) | 4 / 4 (cap 227) / 4.5 (the janus1 launcher on icx4's path) | 4.5 | Population principle shared with the winner; gate rationale (G3), launcher and timeline adopted |
| **Foxtrot v6** | 3.5. Correct that seal, decisions and training compete for one small set, and correct on model-vs-recipe decisions (A37). But it seals 200 with no wave-1 evidence (D27 says "on wave-1 evidence") and takes 31 % of the non-sealed primary patients as D35 | 4. `repower.json` 0.776 at 150. 50/72, all from extension 51–100, verified. Guberina et al. 2026 (tipsRO, "Do AI-based contouring algorithms influence physicians…") and Arjmandi et al. 2025 (JACMP, "…automation bias…") exist with matching titles (Crossref); their numbers sit behind paywalls and were not checked. He, Girshick & Dollár is a known source | 3 / 2.5 / 4.5 | 3.5 | A22 clarification adopted (A37); M1 folded into Job S; the seal and D35 proposals refused |

### Spot-checks this round

**Numbers re-checked against committed JSON:**
- The pool census: 468 patients, 235 non-sealed non-ImageCHD, 161 non-sealed primary, 100 reserved, 61 free. Crucible,
  Delta, Bridge and Atlas agree, and their files agree.
- All five D35 files: sizes, volumes, 0 sealed, overlap with each part of the extension order.
- Serve positions under `pool-2026-10.txt`.
- Seal power at 150 (f = k = 1, ρ = 0): 0.762 / 0.789 / 0.763 / 0.803 / 0.776 across the five, all from CI-derived
  surrogate SDs (LM 0.121, LAD 0.126, LCx 0.135, RCA 0.079). The exact file (`r9_tf1_val.json`) is on Fir: Job 0.
- Paired noise: 0.0382 and 0.0411.
- The anchoring rows of Bridge and Delta.
- No quoted number was found to differ from its file.

**Citations:**
- **Found:**
  - Ash & Adams (arXiv:1910.08475): warm-started models generalise worse;
  - Ozdemir et al. (arXiv:1806.00265, MICCAI 2018): the table was not reached;
  - Rolnick et al. (arXiv:1811.11682): 50–50 in the text;
  - Wald et al. (arXiv:2410.23132, CVPR 2025): Table 3 was not reached in the abstract page;
  - Guberina et al. (doi:10.1016/j.tipsro.2026.100401) and Arjmandi et al. (doi:10.1002/acm2.70425): titles and
    authors via Crossref;
  - Delta's 15-item `citations.md` is consistent with what was opened.
- **No citation was found to be fabricated.** Round 9's checks (Kim JMI 2025, Christodoulou, ImageCAS-X Table 2) carry
  over.

## 3. Rulings on the contested points

### 3.1 The D35 population and size

| Option | Mix | Trainable primary before A35 | Seal ceiling | Changes a human decision? |
|---|---|---|---|---|
| Outside the seal and the whole reserve (Atlas) | 5 sources, 51 % Taiwan | 26 (25 Taiwan) | 250 | No |
| Outside the seal and the 200-step, with the 250-step re-stated (Bridge) | 8 sources, 46 % Taiwan | 26 | 250 | The pre-registered extension order (seal file, D32 precedent) |
| **Across the reserve, extension skips D35 (Delta; Crucible's variant)** | **10 sources, 31 % Taiwan** (Crucible 34 %) | **49** | **228** (Crucible 227) | **D27's 250** |
| Extension positions 51–100 (Foxtrot) | 8 sources, 18 % Taiwan | 62 | 200, sealed now | D27 ("on wave-1 evidence"), and D35's 15 % |

**Ruling: Delta's draw**, conditional on Q1. It is the only option that is both representative of the acceptance
population and leaves training a non-trivial pool before A35 runs.

**What the cap costs:** 228 against 250 is 0.96 against 0.98 power at f = k = 1, ρ = 0, and 0.84 against 0.88 at
f = 1.2 (Delta's table). That is less than what ρ alone moves.

**Why Delta over Crucible:**
- Delta allocates by the primary pool (the seal's mix), Crucible by the eligible 161.
- The two differ by one or two patients per source.
- Delta's principle is the one that ties D35 to A10.

**Size 35:** §1, A33.

### 3.2 The seal size and its rule

**Ruling: 150 now, sized at wave 1 by A35.**
- The four measured-contrast rules (Bridge's C, Crucible's D, Atlas's A31.1′, Delta's weighted rule) differ only in
  detail:
  - analytic versus bootstrap;
  - which patients;
  - source weighting;
  - how conservative.
- A35 takes:
  - the bootstrap form (Crucible, Atlas, Delta);
  - the 80th-percentile SD clause (Atlas, Delta);
  - the larger of the weighted and unweighted answers (Delta's weighting, made conservative);
  - the ≥ 50-patient threshold (Atlas, about Bridge's 49).

**The only unmeasured input that decides the seal is ρ, and wave 1 measures it.** Extending now spends 50 patients
against a risk one measurement removes.

### 3.3 The Janus 1 recipe, arms, seeds, GPU-hours and gate

**Ruling (A36–A38):**
- the recipe: warm fine-tune with replay;
- three runs (a1 and a2 primary, b at 1e-3);
- ≈ 45 GPU-h;
- adoption on D35 (G1) guarded on val 80 (G2, G3).

**Seeds:**
- Crucible's two runs do not replicate the primary arm.
- Foxtrot's two seeds without the 1e-3 arm save 15 GPU-h, but leave A17b untested when G2 or G3 fails. The concurrent
  third run costs no wall-clock.

**The val-80 margin:**
- −0.02 (Atlas, Bridge, Foxtrot) is adopted, not −0.01 (Crucible, Delta).
- At n = 80 the paired MDE is 0.012–0.024, so a −0.01 lower bound would fail a neutral fine-tune about half the time.

### 3.4 Seed anchoring

**Ruling (A40):** measure the seed's extent before reads (Job S), and declare anchoring only on the three-part
signature. The three proposals are each right about what the others miss:
- **A31.2's flag** cannot tell a near-complete seed from anchoring (Bridge, Delta).
- **The precision–recall gap** (Atlas) cannot tell anchoring from a model that is simply more distal than independent
  readers. Delta's independent condition gives a −0.06 to −0.08 gap with no seed.
- **The edit-size and inter-read clauses** separate them.

**The annotator instruction** is recommended (Q6). It costs nothing and acts at the source.

## 4. The first Fir jobs, in order (for the lead; account `def-aso22`)

Every GPU job uses 1 × H100 SXM5 80 GB (`--gpus-per-node=h100:1`, full, not MIG), 12 cores, partition by walltime,
charged to `def-aso22_gpu`. **No job fetches, reads, scores or writes a sealed case or a reserved volume.** Send back
the `slurm-*.out` of any failed job.

| # | Job | Waits on | GPU-h |
|---|---|---|---|
| 0 | Exact seal re-power + ostium residual (CPU, login node) | this PR merged | 0 |
| S | Seed extent on val 80 (A40) | this PR merged; the lead types the TotalSegmentator licence on Fir | ≤ 1 |
| P0 | Janus 0 on the allowed pool volumes + aortas (A41, D35 baseline) | **#116** (with #114's guard) and Q1's answer | 3–4 |
| J1 | Janus 1: a1, a2, b (A37) | **#116** (task 717, `trillium/janus1`), A21's dry run, A39 | ≈ 45 |

**Total to the first Janus 1 decision: ≈ 50 GPU-h. #118 blocks none of these.**

### Job 0: now, login node, CPU (minutes)

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo && git pull --ff-only
python experiments/Bridge/r10/power_r10.py --val $SCRATCH/icx4/r9_tf1_val.json --out $SCRATCH/icx4/r10_power_exact.json
python experiments/Delta/r10/ostium_residual.py --rows $SCRATCH/icx4/delta_p2/per_case.jsonl \
  --icx $SCRATCH/icx4/icx --aorta $SCRATCH/icx4/aorta --pred $SCRATCH/icx4/predictions \
  --out $SCRATCH/icx4/r10_ostium_residual.json
```

- If `delta_p2/` sits elsewhere, use the A29 step's `--out` folder (it holds `SUMMARY.md` and `per_case.jsonl`).
- **Send back on #113:** both printed tables (case ids and numbers only). The re-power replaces §3's surrogate table
  and decides nothing: A35 decides at wave 1.

### Job S: now, ≤ 1 GPU-h (Delta v10 §8, unchanged)

```sh
module load StdEnv/2023 python/3.11.5
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg && mkdir -p $TOTALSEG_HOME_DIR $SCRATCH/seedcal/seeds
totalseg_set_license -l "<the project's TotalSegmentator licence key>"   # typed by the lead on Fir; never committed or posted
C=$(python -c "import json;print(json.load(open('$SCRATCH/icx4/splits.json'))['val'][0])")
CT=$(python -c "import json;print(json.load(open('$SCRATCH/icx4/layout.json'))['cases']['$C']['ct'])")
TotalSegmentator -i $CT -o $SCRATCH/seedcal/seeds/$C.nii.gz -ta coronary_arteries --ml -d cpu   # one case; downloads the weights
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
sbatch $SCRATCH/seedcal/job.sh                        # about 30-60 min
# when finished, on the login node (CPU, about 10 min):
source $HOME/icx14-venv/bin/activate && cd $SCRATCH/asclepius/repo
python experiments/Delta/r10/seed_vs_icx.py --seeds $SCRATCH/seedcal/seeds --icx $SCRATCH/icx4/icx \
  --aorta $SCRATCH/icx4/aorta --splits $SCRATCH/icx4/splits.json --pred $SCRATCH/icx4/predictions \
  --out $SCRATCH/seedcal/seed_vs_icx.json --np 10
```

- **Check:** `seeds: 80 of 80`.
- **Send back:** the printed per-class summary. It contains seed recall and precision, seed tF1, and Janus 0 against
  the seed beside Janus 0 against ImageCAS-X.
- A40's table reads it.

### Job P0: after #116 merges and Q1 is answered (≈ 3–4 GPU-h)

The command surface is #116's (items 4–5, Atlas's comment on #116). **Its README is the copy-paste of record** if the
names differ.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only
test -f trillium/pool/fetch_pool.py || { echo "#116 NOT merged: stop"; exit 1; }
python3 trillium/pool/fetch_pool.py --purpose d35    $SCRATCH/pool/cases   # refuses sealed and reserved before any request
python3 trillium/pool/fetch_pool.py --purpose train  $SCRATCH/pool/cases
python3 trillium/pool/fetch_pool.py --purpose report $SCRATCH/pool/cases
JANUS0=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
[ -f $JANUS0 ] || JANUS0=$(ls ~/projects/def-aso22/$USER/icx4/checkpoint_final.pth $HOME/icx4-keep/checkpoint_final.pth 2>/dev/null | head -1)
POOL_CLUSTER=fir trillium/pool/predict_pool.sh --checkpoint $JANUS0 --cases $SCRATCH/pool/cases --out $SCRATCH/pool/janus0
grep SBATCH $SCRATCH/pool/janus0/job.sh    # h100:1, cpus-per-task=12, mem=280G, time ≤ 11:50, account=def-aso22
```

- **Check the printout.** Under A33 it is **244 volumes** (counted here from the pool list):
  - D35 51;
  - trainable primary 56;
  - report (ImageCHD and spacing-suspect, non-sealed) 137;
  - **sealed 0, reserved 0** (325 sealed and 106 reserved volumes refused).

  Atlas's fallback draw gives 206.
- **Send back:**
  - the printout;
  - the file counts of `$SCRATCH/pool/janus0/{pred,aorta}`;
  - `domain.json`'s per-source table (A41).

### Job J1: Janus 1, at A39 (≈ 45 GPU-h, three concurrent 23:50 jobs)

```sh
# Girder host (the lead): export approved reads; sealed reads are left out, D35/reserved are refused by the #116 guard
segqueue14-export --out /srv/segqueue14/export-janus1 --replicas all
# Fir login node, after copying the export to $SCRATCH/janus1_export
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
mkdir -p experiments && rm -rf experiments/janus1 && cp -r repo/trillium/janus1 experiments/janus1 && cd experiments/janus1
ICX4_CLUSTER=fir TASK=717 ARM=lr1e2 SEED=1 CHAIN=2 EXPORT=$SCRATCH/janus1_export JANUS1_WORK=$SCRATCH/janus1_a1 ./janus1
ICX4_CLUSTER=fir TASK=717 ARM=lr1e2 SEED=2 CHAIN=2 EXPORT=$SCRATCH/janus1_export JANUS1_WORK=$SCRATCH/janus1_a2 ./janus1
ICX4_CLUSTER=fir TASK=717 ARM=lr1e3 SEED=1 CHAIN=2 EXPORT=$SCRATCH/janus1_export JANUS1_WORK=$SCRATCH/janus1_b  ./janus1
grep SBATCH $SCRATCH/janus1_a1/job.sh   # --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00 --account=def-aso22
./janus1 status $SCRATCH/janus1_a1      # after ~2 h: s/epoch, expect ~190-200 (Janus 0: 192)
```

**Check each printout:**
- `refused: sealed N, d35 M, reserved R` (non-zero is expected and correct);
- `train: ImageCAS-X 560 + pool <k> reads`;
- `fold-0 val: ImageCAS-X val 80`;
- `plans = Dataset715`;
- the A1c hash line;
- the A39 counts (≥ 25 D35 patients and ≥ 40 trainable primary patients double-read). **The launcher refuses below
  them.**

**When each is `DONE`:** `./janus1 collect <work>`. It writes:
- val-80, open-36 and dev-44 decisive tF1 with the in-job aortas;
- D35 model-vs-read via `score_wave1.py` with the D35 guard;
- the pairing against Janus 0 (`r9_score_icx4.py --pair` for val 80; the paired helper for D35).

**Send back on #113:** the three `results/` folders. The PM applies A38 and names the runs Janus 1, 2 and 3 in that
order.

## 5. Decisions for the lead (questions, not rulings)

### A. These change, or read, a human decision

**Q1. D27's ceiling: where does D35 come from?**

| Option | What it does |
|---|---|
| **(a) Delta's draw across the reserve; the seal can then reach 228, not 250 (recommended)** | Representative of the seal (10 sources, 31 % Taiwan); 49 trainable primary patients before the seal is sized; power at 228 is 0.96 vs 0.98 at 250 (f = k = 1, ρ = 0) |
| (b) Bridge's draw; the 250-step is re-stated around D35 (skip + continuation), keeping 250 reachable | 8 sources, 46 % Taiwan; 26 trainable; changes the pre-registered extension order by an explicit seal-file PR |
| (c) Atlas's draw, outside the seal and the whole reserve; nothing in D27 changes | 5 sources, 51 % Taiwan; 26 trainable (25 Taiwan); tranche 2 to 50 if the seal ends below 250 |

- **Until answered:** no read of any patient in any of the three draws (or in Bridge's re-stated reserve) is looked at
  or trained on.
- Job 0 and Job S do not wait. P0 and Janus 1 wait on #116 in any case.

**Q2. D23/D30, the serving order: serve the 35 D35 scoring volumes first?**
- (a) **Yes (recommended).** Only these 35 volumes move up; nothing is added or dropped. All 35 D35 patients are then
  double-read by about position 35, instead of 23 by 242 and the last at about 600. G1 is decided on the full set, and
  the D35 part of A35 and A40 comes forward by about 200 positions.
- (b) No, D23 as is (D30). Janus 1 is decided on the ≥ 25 read by about position 242–300 and confirmed on all 35 at
  about 600.

**Q3. L5: if A40 declares anchoring in a class, is A10 on the pool still the acceptance test in that class?**
- (a) A10 alone.
- (b) **A10, and also, in that class (recommended):**
  - A26's sealed-80 red flag, made binding per class: the class's sealed-80 tF1 against ImageCAS-X is no more than
    0.03 below its open-36 value, at the single look;
  - G2 and G3 (val 80 against Janus 0).
- (c) Accept the seed's extent as the pool convention. This changes what D8 means on the pool and what Janus k learns.
  Not recommended.

**Not needed until Job S or A40 says so.** If Job S shows seed recall < 0.90 in a class, it is asked before wave 1.

**Q4. D28's reading.** D28's "the first retrained decision adds a second seed to its control" is read as run a2 (a
second seed of the primary fine-tune arm, ≈ 15 GPU-h), not a second from-scratch Janus 0 (≈ 60 GPU-h).
**Recommended: confirm.**

### B. The lead's calls that change no D-number

**Q5. Confirm D35's size of 35** (15 % of the real 235) rather than 50. **Recommended: confirm.** 50 buys 0.001–0.004 of
MDE, and takes 15 more patients from the seal or training.

**Q6. Issue a SegQueue14 protocol note:** "trace each vessel past the seed's end to where the lumen is no longer
confidently distinguishable". **Recommended: yes, before wave 1.** It is the existing protocol and D12, and it costs
nothing.

**Q7. The final retrain.** **Recommended: decide after Janus 1.** When it happens:
- one from-scratch run (≈ 55–60 GPU-h);
- on ImageCAS-X train 560 + every trainable pool read;
- never D35;
- **keep val 80 and open-36 untrained,** so the final model is checked against the last warm Janus on D35 and val 80
  before its single seal look.

**Q8. L6 (ASOCA). Recommended: not now.** The pool's sources already test multi-source shift.

**Q9. Re-grid the 74 spacing-suspect volumes** (QC). **Recommended: yes, low priority.** They are then trainable and
scorable.

### C. Settled by the amendments (no question)

- The seal sizing rule (A35, replacing f/k).
- The Janus 1 recipe, runs and gate (A36–A38).
- The start trigger (A39).
- Job S and the anchoring signature (A40).
- The domain check (A41).
- The ostium residual (A42).
- The job order and the swe split (A43).

## 6. What would change the ruling

| Result | Then |
|---|---|
| Job 0's exact re-power differs from the surrogate by more than 0.05 at 150 | §3's tables are replaced; A35 is unchanged |
| Job S: seed recall < 0.90 in a class | Q3 is asked now, before wave 1 |
| A35 at the cap still < 0.80 | To the lead: A10 at D6's margin is under-powered on this pool |
| Measured ρ ≥ 0.3 in every class | The seal very probably stays 150; the reserve is released |
| A40 declares anchoring | Q3 is live; G3 binds every fine-tune |
| G1 passes | Janus 1 is the base; Janus k repeats A38 against its predecessor and Janus 0 |
| a1 − a2 > 0.02 | Recipe decisions need ≥ 2 runs per arm |

## 7. Is the plan settled?

**Settled to the first Janus 1 decision,** except for Q1's population, which has a binding fallback. Jobs 0 and S can
run today. P0 and Janus 1 wait on #116.

A Round 11 is due when either of these comes first:
- Janus 1's A38 verdict;
- A35's seal size together with the A40 report from the first ≥ 50 double-read patients.
