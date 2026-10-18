---
tags: [plans, judgement]
round: 9
updated: 2026-10-18
issue: christianGRogers/Asclepius#48
---

# Round 9 ruling

This is the first round under the four-class schema (D25), with ImageCAS-X's lumen as drawn (D8), team reads only on the 675 pool volumes (D22, D23, D26) and **Fir** as the compute. All five candidates agree on the model: **run `trillium/icx4` unchanged** (nnU-Net v2.8.1 ResEnc, 60 GB plan, 0.5 mm, 256³, batch 2, mirroring off, default window, DiceCE, 1000 epochs, ImageCAS-X 560/80/160 collapsed by `territory.py`). They differ on four things:

- how the first result is scored and read;
- whether a second seed runs beside it;
- how the schedule copes with Fir's 12 cores per GPU;
- where acceptance (A10, D6) can be measured now that no sealed case will ever have two reads.

The code under judgement is the icx4 job on `dev`, which now includes #66. I read it rather than relying on the candidates' descriptions:

- `lib/sealed.py` is the one filter. The launcher and every job refuse to start unless the split is exactly 80 sealed + 36 open + 44 dev.
- In the last job, `aorta.py` + `tf1_score.py` + `report.py` give decisive tF1 at the A1c hash, on open-36 and dev-44 only.
- `ICX4_WORK` gives an independent second run.
- `ICX4_EPOCHS` is read by the trainer, and `CHAIN` defaults to 4.

Every candidate's fallback "if #66 has not merged" is therefore **moot**, and is struck from the plan.

## 1. Ruling: Atlas v11 holds the title, with amendments that adopt the others' evaluation work

No candidate changes the model, so the title goes to the most complete operational plan, and the other four contribute amendments. **Atlas v11** is that plan. It is the only one that:

- scores the **val 80** decisively. It gets aortas from atlas2, which I confirmed: `trillium-results/round6/atlas2/results/aorta.log` lists 116 masks, the 80 val + 36 open cases. It does this with a self-tested CPU scorer that pairs seeds.
- sizes the chain for the measured loader risk;
- names the anomalous-anatomy strata.

**Bridge v8's** evaluation design is the strongest single contribution of the round, and it is adopted almost whole (A27, A30, A31).

### Binding amendments (Round 9)

**A25: the first Fir job is icx4 as on `dev`, unchanged, with `CHAIN=5`.**
- The model and recipe are exactly `trillium/icx4`, on `def-aso22`, with the Fir profile (`h100:1`, 12 cores, 280 G, 23:50).
- **`CHAIN=5`**, from Atlas. Five jobs give 118 h of walltime, enough for 1000 epochs at up to about 400 s/epoch. A spare job exits within a minute, so the extra job costs nothing if unused.
- **Atlas's 500-epoch fallback is not adopted.** Nothing waits on icx4's wall-clock: D23/D26 serve the pool from TotalSegmentator seeds, so no annotator is idle because of it. Cutting the schedule would make the first model a different recipe from every later one (A22). If job 1 shows more than 400 s/epoch, the lead re-runs `./icx4` once the chain ends; it resumes. The epoch count stays 1000.
- **A 24-core request is not the default.** It is charged as about 2 GPUs (Foxtrot, Atlas). Nibi (14 cores) remains the lead's fallback for a long queue.
- **Expected cost: 60–75 GPU-h** (range 55–85, ceiling 118). Training is 53–68 h at Foxtrot's measured 190–245 s/epoch, plus about 2 h of preprocessing and about 4 h of prediction, aortas and tF1. Atlas's measurement (181–305 s/epoch) brackets it.

**A26: which cases decide.**

| Set | Use |
|---|---|
| **Val 80** (ImageCAS-X fold 0, atlas2 aortas) | **Decides** every recipe-level question on icx4 and its successors. nnU-Net does not select a checkpoint on it (prediction uses `checkpoint_final.pth`), and n = 80 resolves about 2.5× more than the open 36 (Bridge: MDE 0.013 case-only at 80, 0.019 at 36) |
| **Open-36** | Out-of-sample confirmation. A decision whose sign reverses on open-36 is reported, not adopted. Any **rule or threshold** (post-processing, P2 below) is validated on open-36, never set on it |
| **Dev-44** | Reported apart, never decides alone |
| **Sealed ImageCAS-X 80** | One blind look, at the **final** model, against collapsed ImageCAS-X (single read). This is a model-vs-expert milestone, not A10 (it has no inter-read). Crucible's red flag is pre-registered: macro tF1 more than 0.03 below the open-36 value means investigate before release |
| **Sealed quality-0 20** | **Retired from scoring.** No reference can ever exist for them. They stay excluded from training and inspection, for hygiene (Bridge, Crucible, Atlas) |

- The val-80 scorer is **`experiments/Atlas/r9_score_icx4.py`**. Before its val numbers decide anything, it must reproduce the in-job `tf1_per_case.json` on open-36, given the same predictions and the in-job aortas (`$SCRATCH/icx4/aorta`): identical per case and per class. A9 allows one metric. Three wrappers around it (in-job, Atlas, Delta) are allowed only if they agree.
- Val is not "clean" in the A14 sense. Advocates inspected run-1 predictions and val references in Rounds 5–9. But none of that tuned anything icx4 ships, and a recipe decision on a retrained network is not biased by having looked at a different model's errors. That is why val may decide recipe questions but not rule or threshold choices.

**A27: pre-registered reading of icx4's first result** (val 80, decisive tF1 at A1c `24441cf8…5254`, A1b flags apart). This merges Bridge's, Atlas's, Crucible's, Delta's and Foxtrot's tables. No absolute baseline exists: run 1's 0.896 used the retired thick convention, which is about 0.19 tF1 away (Crucible, Round 1). So these lines are **triggers for a look, not acceptance**.

| Result | Then |
|---|---|
| Macro < 0.80 | **Stop.** Something is wrong with the job, the collapse, the resume or the scorer, not the recipe. Check 5 val cases end to end before more GPU is spent (Bridge, Crucible) |
| 0.80 ≤ macro < 0.85 | The recipe reopens. First: the flagged and provisional share, the per-class split, and a cut census on ImageCAS-X (Atlas R2) |
| Any class < 0.80, or LCx < 0.80 | Review that class's 10 worst val cases (calcified and side-branch-heavy LCx first) before any fine-tune. The Round 8 LCx guard of 0.83 was set on the thick mask and is replaced by 0.80 (Atlas R3). On ImageCAS-X the LCx class is 35 % side branch (Crucible, Atlas), and its human inter-observer DSC is 84.8 ± 19.8 |
| Flagged trees > 30 % in any class | The A1b review comes first, and decisions on that class wait for it (Bridge) |
| Whole-tree Dice on the open 80 < 88.3 | Report only: check preprocessing, collapse and window before the predictions are used (Foxtrot F7.1). Indicative, not paired: ImageCAS-X's Table 2 includes our sealed 80 |
| FP per case ≤ 1 (A15 met) | A24's FP-loss line is closed (Delta row 5) |
| FP per case > 1 | Run atlas2's census script on icx4's val. If confident components beside the tree dominate again, a properly weighted FP term (5–20 % of the loss) becomes a two-seed candidate (A22), not a single run |

**A28: Dice decides nothing (Delta P1, now evidenced on the new reference).**
- On 80 val references, a roughly 5 mm proximal cut leaves LAD/LCx Dice at a median of 1.000 while their tF1 is 0. That is 140 of 160 vessels, which I checked in `experiments/Delta/r9_summary.txt`.
- Dice is reported for the literature only.
- Foxtrot's per-class Dice readings against the four-class human floor (F7.2) are **report-only**. The floor derivation is sound: the Dice of a merged class is at least the volume-weighted mean of its segments' Dice. But it decides nothing.

**A29: Delta's P2 (ImageCAS-X start points as the ostium of record) is conditional, decided on CPU.**
- The evidence is solid:
  - start points equal the label-rule ostia in 709/709 and 720/720 cases;
  - the CT-free thick rule misses the right ostium by more than 5 mm in 29/720 cases;
  - 38/720 cases are flagged under A1 as written, almost all through the cross-check.
- The comparison that matters, though, is P2 against **A1 with TotalSegmentator aortas**, not against the CT-free rule. Those aortas now exist for all 160 non-sealed val and open cases: in-job for open-80, atlas2 for val-80.
- So **Delta's GPU aorta job is not needed.** Run `experiments/Delta/r9_fir/score_tf1.py --aorta-dir <both aorta folders>` on CPU after icx4. Delta's own pre-registered test decides:
  - ostia within 2 mm in ≥ 95 % of trees, **and** |Δ macro tF1| ≤ 0.005;
  - if it passes, P2 becomes the rule of record **for ImageCAS-X references only**, together with its flag rule;
  - if it fails, P2 is withdrawn.
- Team reads keep A1 as written.

**A30: a candidate pool seal is frozen now, before any read exists.**
- Bridge's `experiments/Bridge/r9/sealed_pool_proposal.json` is the **candidate A10 set**: 150 primary patients (216 volumes), plus 20 ImageCHD patients as report-only, with a pre-registered extension order.
- Until the lead rules (§5, L1), **no volume of a listed patient is trained on, prelabelled or inspected**, and no read of one is exported for analysis.
- Annotators do nothing differently. These volumes are in the D23 queue and get their two reads like any other.
- Freezing the list costs nothing and preserves the option. If the lead declines the pool seal, the list is released back to training, unchanged. Whether it **becomes** the acceptance set is the lead's decision (§5).
- Before wave 1, QC confirms the patient grouping per source against source metadata. Crucible and Bridge both flag the name heuristic, and Bridge keeps Figshare `PA0`/`PA1` apart.
- Why Bridge's draw rather than Crucible's or Delta's:
  - it is by patient, as is Crucible's;
  - it keeps ImageCHD out of the primary aggregate, which is where Atlas's anomalous-anatomy point leads;
  - it pre-registers its extension order;
  - its power table reproduces exactly (§3).

**A31: wave-1 measurements, pre-registered, on non-sealed pool reads only.**
1. **f and k** (Bridge): the pool's per-case spread relative to val, and inter-read spread relative to the model's. The power table is re-run on icx4's own per-case val tF1. If f or k > 1.2, the seal extends along its pre-registered order (200, then 250 patients) **before any sealed read is scored**.
2. **Seed-vs-read tF1** (Crucible P2): how much of each read is the TotalSegmentator seed (D26 starts every class as a full copy of it). If seed-vs-read ≥ inter-read − 0.02 in a class, agreement between reads is partly agreement with a shared anchor. The A23 diagnostic is then reported first beside A10, and the question goes to the lead (§5, L5). **This is the most important new risk this round surfaced.**
3. **Model-vs-read tF1 per source** (Foxtrot F8, Crucible P2). This is reported with CIs and decides nothing at n ≈ 30: A10 at 30 patients passes a human-level model at most about 0.2–0.37 of the time under either power model. Foxtrot's F8 pass/fail table is therefore adopted **as a report**, not as a decision.
4. Atlas's pre-read domain-shift check (F2: icx4 against each pool volume's TotalSegmentator seed, per source; about 3–4 GPU-h) is **approved as optional**, after Job A, report only.

**A32: what carries over and what lapses.**
- **Carried:** A1, A1a, A1b, A1c (hash `24441cf8…5254`), A2/A15 (FP gate, raw), A9, A11′ (each read a sample), A12 (first-50 report, now on pool reads), A17a/b (fine-tune trainer, LR 1e-2 with a 1e-3 arm), A19, A21, A22 (seed rule), A23 (report only).
- **Lapsed with D8/D12:** A3 (convention monitor), A4 (proxy QA), A17c (proxy admission), all proxy labels.
- **Closed:** A24 (run 3 not adopted; the term was too weak to test).
- A `coronary_icx4` segtrain task config (Echo's gap) is needed **before wave-1 fine-tuning, not before icx4**. It becomes a `role:swe` issue when wave 1 approaches.

## 2. Scorecards

Scores are out of 5: (a) reasoning, (b) evidence, (c) fit to Fir and D25, (d) risk/cost.

| Candidate | (a) Reasoning | (b) Evidence | (c) Fit | (d) Risk/cost | Verdict |
|---|---|---|---|---|---|
| **Atlas v11** | 4. The most complete plan: the val-80 scorer with seed pairing, `CHAIN=5`, strata for ALCAPA and ImageCHD. Two weaknesses: thesis 3 compares icx14 *trunk* pseudo-Dice with human DSC, which Echo had already said is not comparable (Atlas disclaims it, but builds a thesis on it); and the 500-epoch fallback trades the recipe for wall-clock nobody needs | 4. Loader cost measured (3.3–6.1 CPU-s/sample, matching its note); census matches Crucible's. Citations: BraTS-GoAT 0.8315 vs 0.8310 **found** in the PDF; nnFoundation's hepatic-vessel 0.669 found, but Table F30 itself not reached (not counted against). **Hampe 2024 is quoted in the candidate marked "[WF; re-read before quoting]"**. The paper exists (J Med Imaging 11:034001), but putting an unverified number in a candidate counts against it | 4.5 | 3.5. Job B doubles Phase F1's GPU (lead's call) | **Holds the title**, with A25–A32 |
| **Bridge v8** | 5. Identified all three evaluation failures (Dice-only, the seal opened, A10 with no cases) and sized the fix from data. The patient as the unit of n (517 patients in 675 volumes) is the key correction | 5. **Power table reproduced exactly** (`a10_pool_power.py`: 0.966 / 0.582 at n = 150, 0.836 / 0.30 at n = 100). Zenodo listing (one segmentation per case) is consistent with Crucible's and Atlas's independent listings | 4.5. The 0.85/0.88 reading lines are set from run 1, a different convention (it says so) | 4.5 | Evaluation design adopted (A27, A30, A31); seal list frozen as the candidate |
| **Crucible v10** | 4.5. Seed-anchored reads (D26) as a threat to A10's meaning is the round's most important new insight. Correctly says P1 needs no second seed (not a comparison) | 4. Power JSON matches its table (0.785 / 0.4425 at n = 150). Its contrast SDs come from simulated reads, an assumption it labels as one. Territory audit checks out (82/90 Other pieces, 99.6 %; LCx side share median 0.352). Kim et al. 2025 is cited as "segment binary with nnU-Net and name afterwards"; the abstract does not say this (not found, minor) | 4.5. Includes ImageCHD in the scored seal | 4.5 | Seed-vs-read measurement adopted (A31.2); val-80 tF1 requirement folded into A26; P3/P4 recipe deferred to Round 10 |
| **Delta v9** | 4. P1 and P2 are well argued. But **P4 sizes the seal at 60 patients from a macro paired-training SD (0.041)**, which is the wrong quantity: A10 is per class on a model-vs-inter-read contrast. At n = 50–60, both power models give a human-level model a 0.18–0.37 chance to pass | 4.5. Every number checked matches `r9_summary.txt` (29/720, 38 flagged, 140/160, c0106). Citation file supplied | 4 | 4.5. Its GPU aorta job is redundant now that #66 computes aortas in the job (A29) | P1 adopted (A28); P2 conditional on CPU (A29); P4's size refused |
| **Foxtrot v5** | 4. A measured job budget, plus two cheap outside reads of the result. The F8 decision table at n = 30 is under-powered as a decision (adopted as a report) | 4. Loader measurement matches its note (7.9 / 9.4 CPU-s per batch → 190–245 s/epoch). External drops cited to real papers: Zhang JIIM 2025 found, on ASOCA + GeoCAD; Kim JMI 2025 found, but "Taipei" not confirmed from the abstract; Seg2RefineNet is paywalled, unchecked. Small command errors: `ls cases \| wc -l # expect 1000` (the ImageCAS layout has 2000 entries) and Globus `alliancecan#fir` (the inventory says `alliancecan#fir-globus`) | 4.5 | 5. The cheapest plan | Budget adopted (A25); F7 report-only (A28); F8 as a report (A31.3) |

### Citation and number spot-checks (this round)

**Found as cited:**
- ImageCAS-X (arXiv:2608.30404, Bransby et al.);
- LWT-ARTERY-LABEL (arXiv:2508.06874);
- Christodoulou et al. (arXiv:2409.17763: 221 papers, 1 with CIs, runner-up inside the CI in > 60 %);
- Åkesson, Töger, Heiberg (Comput Biol Med 180:108944);
- Zhang et al. (JIIM 2025, ASOCA + GeoCAD);
- Ren et al. (BMC MIDM 23:249, segment labelling);
- Kim et al. (JMI 12(1):016002, multi-institutional coronary segmentation);
- BraTS-GoAT (arXiv:2609.15524; 0.8315 / 0.8310 in its text);
- nnFoundation (arXiv:2609.26924, with a 1000 → 150 epoch comparison).

**Partly found or not reachable:**
- nnFoundation Table F30 (not reached in the HTML);
- Seg2RefineNet (paywall);
- Kim's Taipei cohort (not in the abstract).

**Vault links:** all resolve, in all five candidates.

**Numbers checked against notes and outputs:**
- Bridge's power table, by re-running the script;
- Crucible's power JSON;
- Delta's summary;
- Atlas's and Foxtrot's loader notes;
- Crucible's territory audit;
- atlas2's aorta coverage.

No quoted number was found to differ from its note.

## 3. Contested facts

1. **How many sealed pool patients does A10 need?**
   - Bridge says P(pass at human level, n = 150) = 0.97. Crucible says 0.79.
   - Both reproduce. They differ only in the assumed contrast SD:
     - Bridge uses run 1's model SD per class with an inter-read SD equal to it (LCx contrast ≈ 0.157, RCA ≈ 0.11);
     - Crucible uses Round 6's simulated-read contrast SDs (LCx and RCA 0.19).
   - Neither is measured; wave 1 measures it (A31.1).
   - What both agree on decides the plan:
     - 100 patients is under-powered (0.51–0.84, and 0.19–0.30 if the pool is harder);
     - 150 is the right order;
     - the set must be extendable on non-sealed evidence;
     - 60 is too small.
2. **Is val 80 a fair decision set?** Yes, for recipe decisions (A26). Bridge preferred the open 80. The open 80 stays the confirmation set.
3. **Do icx14's numbers say icx4 is near human level?** No. They are trunk pseudo-Dice with side branches penalised (Echo). icx4's first decisive tF1 starts the series (Foxtrot, Crucible).
4. **Is A10 on the pool comparable to A10 on ImageCAS-X?** Not yet known. The pool has a different domain (26 sources), and its reads are seed-anchored. This is a named Round 10 gap (§6).

## 4. What would change the ruling

- icx4's val-80 result in A27's stop or reopen rows.
- Delta's P2 test (A29), either way.
- Wave-1 f, k or seed-vs-read beyond A31's lines.
- The lead's answers to §5. In particular, if ImageCAS-X's second reads are obtained, A10 also runs in-domain on the sealed 80.

## 5. Decisions for the lead

These are questions, not rulings. Each could change a D-number or the meaning of one, or is a budget call.

**L1. Where is acceptance (D6) measured?** No case in the A14 seal will ever have two reads (D22, D23), and ImageCAS-X's second-analyst reads are not in the Zenodo release (checked independently by Bridge, Crucible and Atlas).

| Option | Cost | Note |
|---|---|---|
| (a) Seal 150 pool patients (A30's frozen list), extendable to 200–250 on wave-1 evidence; D6 is scored there | About 32 % of the primary pool patients are withheld from fine-tuning; no extra reads | Measures the deployment population. P(pass at human level) is 0.79–0.97 if the pool is like ImageCAS, 0.44–0.58 if it is harder (§3) |
| (b) Ask the ImageCAS-X authors (Bransby et al.) for their blind second-analyst reads of the 160 test cases; D6 on the sealed 80 | An email; D19 says the lead handles access requests | In-domain and expert. No annotator time |
| (c) **Both (recommended)** | (a) + (b) | Two independent checks: in-domain experts and out-of-domain team reads. Passing requires both where both exist |
| (d) Route about 30 sealed ImageCAS-X cases into SegQueue14 for two team reads | About 60 reads; **changes D23** ("no ImageCAS case") | A three-way convention check (team, team, ImageCAS-X) |
| (e) Delta's 60 pool patients | Least withheld | **Not recommended:** at this size a model as good as a reader fails A10 most of the time |

**L2. A second icx4 seed (Job B), concurrent.**
- Cost: +55–85 GPU-h.
- What it gives:
  - σ_seed on the actual model (A22 currently borrows 0.013 from a small model);
  - a check on the run (icx14 lost a run to a resume bug);
  - a two-model ensemble, decided on fixed predictions (Atlas R5).
- **Recommended: yes**, submitted only after Job A's first job has started, so it can never delay A (Bridge). Job B's usage also lowers fairshare for A's later chain jobs, but modestly (RawUsage 0, one-week half-life).
- If declined, A22's fallback stands: the first retrained decision adds a second seed to its control.

**L3. Anomalous anatomy in acceptance.** ImageALCAPA (30 volumes; the left tree arises from the pulmonary artery, so A1 cannot place an aortic ostium) and ImageCHD (83, congenital). **Recommended:** report them as their own stratum, outside the A10 aggregate (Atlas, Bridge). The 74 header-spacing-suspect volumes stay out of A10 until re-gridded.

**L4. Many phases of one patient** (60 patients have 2–20 volumes). Under D23 each volume is read twice. **Recommended:** serve one volume per patient first and the other phases after (Bridge Q2). This changes the order D23 sets, so it is the lead's call.

**L5. If wave 1 shows that reads keep the seed's extent** (A31.2): is A10 against seed-anchored reads still the acceptance test? Or should acceptance also require model-vs-ImageCAS-X non-inferiority on the sealed 80? No answer is needed now. The question is asked now so that it is not decided after the data are seen.

**L6. ASOCA registration** (Foxtrot E2; it needs ethics evidence at the UK Data Service). An optional binary external check. Low priority.

**L7. Carried over:** the FP gate's achievability (Round 8 §6.1), to be asked again on icx4's census if A15 fails.

## 6. Is the plan settled?

**Settled for the first Fir job and for the training recipe.** Five independent advocates, with different evidence, converge on icx4 unchanged. No CPU or literature evidence argues for another model, and every recipe lever left (a weighted FP term, Skeleton Recall, ensembling) is under 0.02 and needs A22 seeds. The job, its scoring and its reading are fixed above and in [[Master plan]].

**Not settled for acceptance and for what follows the first model.** A Round 10 should be held **after icx4's results are back** (no CPU-only round before then), to settle:

1. **The reading of icx4** under A27, σ_seed if Job B runs, the P2 verdict (A29), and icx4's FP census.
2. **The acceptance set**, from the lead's answer to L1: the seal size re-powered on icx4's own per-case val spread, and on f and k once wave 1 exists.
3. **The pool fine-tune recipe.** Crucible P3/P4 (from scratch on ImageCAS-X + pool, 2:1 mix arms) and Atlas F3 (warm fine-tune from Job A, A17a) disagree, and neither is costed against A22 on real numbers yet. This includes the `coronary_icx4` segtrain task config.
4. **What team reads measure:** seed anchoring (A31.2), the convention of reads redrawn from a TotalSegmentator seed against ImageCAS-X's lumen, and per-source domain shift. This decides whether A10 on the pool means what D6 intends.
5. **The FP lever**, only if icx4 fails A15 with confident components beside the tree.
