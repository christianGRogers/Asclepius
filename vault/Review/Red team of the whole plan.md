---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: The whole vault, the repo, and the strategy
---

# Red team: is this the right plan at all?

Reviewer 10 of 10. Slice: the whole, and the strategy. 2026-09-26.

---

## 1. Verdict in five lines

**No.** The plan's stated contribution — "the contribution is the per-branch
labelling" (`vault/Training method/Training plan.md:96`) — no longer exists, and I
verified that independently: ImageCAS-X is real, 800 cases, 14 classes, CC BY 4.0.
A defensible contribution does exist, but it is a different one: **the first
per-branch voxel segmentation benchmark on a public CCTA cohort, plus a
cross-site reproducibility check on ImageCAS-X's protocol** — and it costs
roughly a tenth of the planned work.
Of the plan as written I would drop: the from-scratch annotation programme, four
to six of the ranked experiments, the heart-crop run, the ResEnc run, and run A.
The single largest process risk is not technical: a plan of record containing
three known errors is still governing, while `docs/` and `configs/` have already
silently forked from it.

---

## 2. The contribution problem and its resolution

### 2.1 What I verified myself

Everything below was checked this session against primary sources, not taken
from the vault.

| Claim | Status |
|---|---|
| ImageCAS-X exists; arXiv:2608.30404; Bransby, Øksnebjerg, Kjær, … Kofoed, Paulsen | **Confirmed** (arXiv abs + HTML) |
| 800 scans, voxel lumen **and coronary segments**, centerlines, mesh surfaces | **Confirmed** |
| 14 classes: LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other (≥1.8 mm) | **Confirmed** (Supp. Table 4); no proximal/mid/distal split |
| Split 560 train / 80 val / 160 test | **Confirmed** |
| Benchmark: CAS-Net 91.2±2.8, nnU-Net 89.8±3.2, nnU-Net+clDice 90.0±3.5, inter-observer 92.8±3.1 | **Confirmed** |
| nnU-Net+clDice worsens topology: βerr 5.6 → 8.0 | **Confirmed** — this closes Verification log **entry 13**, which the log still lists as *unfinished* (`vault/Research/Verification log.md:23`) |
| ~35 min/case analyst time; 200 h centerline + 270 h lumen correction total | **Confirmed** — closes entry **15**, also listed unfinished |
| Zenodo 10.5281/zenodo.21887809, CC BY 4.0 | **Confirmed** (record indexed and titled ImageCAS-X) |
| **"six pretrained baselines"** (`vault/Proposed changes to the training plan.md:70-71`) | **Wrong — eight.** 5 coronary-specific + 3 general-purpose (TotalSegmentator, 3D-FFR-UNet, ADE-HTL, Swin-UNETR, ImageCAS 2023, nnU-Net, nnU-Net+clDice, CAS-Net) |
| **ImageCAS-X benchmarks only two tasks: lumen segmentation and centerline extraction.** Per-segment numbers in the paper are *inter-observer only*; there are **no automated per-segment results** | **Confirmed** (arXiv HTML + `kitbransby.github.io/ImageCAS-X/`). No leaderboard, no announced challenge. |

That last row is the whole answer. **Bransby et al. released the labels and did
not use them.** They published a 14-class dataset and then benchmarked eight
models on the merged binary lumen. The per-branch task is open, on their own
data, with their own inter-observer ceiling already measured per class as the
comparator, and their test set already sealed.

My literature search for prior per-branch *voxel* CCTA results found: 3-class
trunk work (Kim et al. 2025, J Med Imaging 12(1):016002 — nnU-Net 0.794 Dice on
LAD/LCx/RCA), centerline/graph *semantic labelling* work (Hampe et al.; ACC
classifier arXiv:2307.11959), and 2D X-ray SYNTAX-schema work (ARCADE, YOLOv8
Dice 0.49). Nothing at 14-class voxel granularity on CCTA. I did not run an
exhaustive search; treat this as "none found in a targeted search", not "proven
absent".

### 2.2 Candidate contributions, ranked by defensibility

1. **The per-branch benchmark and the model that defines it.** Strongest by a
   wide margin. Precise claim: *first voxel-level 14-class coronary segmentation
   benchmark on public CCTA, scored against a measured per-class human ceiling,
   with detection and topology metrics rather than mean Dice.* It survives
   "Bransby already did that" because they did not. It turns the labels from a
   threat into an asset: sealed test set, published ceiling, eight lumen
   baselines, CC BY 4.0, no REB exposure. Note that your own research already
   wrote this sentence — `vault/Research/Metrics and clinical validation/Proposed
   changes.md` **E36**: *"first per-branch voxel benchmark on ImageCAS (factual,
   level-1)"*. The consolidated proposals' §0 never offers it as an option. It is
   the answer, and it was already in the vault, unpromoted.
2. **A cross-site reproducibility study of the schema.** Second, and cheap.
   ImageCAS-X's inter-observer numbers are *within one team, one protocol, one
   tool* — they cannot measure whether the schema reproduces across sites.
   Independently re-annotating 30–60 of their cases at a different institution,
   with a different tool, measures exactly that, and is a publishable finding
   whichever way it comes out. This is the only defensible surviving purpose for
   the annotation programme, and it is ~40 hours of analyst time, not a term.
3. **The evaluation framework.** Third. Per-class detection rate, Betti matching
   and per-component purity, dominance/disease subgroups, NSD tolerance derived
   from inter-rater surface distances, stated averaging rule. Genuinely better
   than what the field does, but alone a reviewer files it as reporting practice.
   Strong as the *method* of contribution 1, weak as a contribution itself.
4. **A clinical question.** Highest ceiling, zero groundwork. If you could show
   that per-branch labelling changes segment-level stenosis reporting or FFR-CT
   decision agreement, that beats everything above. The hook exists in your own
   notes — the BCS paper (arXiv:2607.28327) ties bifurcation connectedness to
   FFR-CT decision agreement. But there is no clinician, no outcome data, no REB,
   and no mention of any of these in 84 notes. Not reachable on this timeline
   without a named collaborator. Do not plan around it; do write one paragraph
   saying it is the next step.
5. **The annotation methodology.** Weak. SegQueue's gold/duplicate/review design
   is sound engineering, but Mask SAM 3D's authors already published the same
   nnU-Net-seed-then-refine-in-Slicer workflow (Verification log, second pass),
   and CoronaryExplorer is the published coronary-specific tool. You would be
   describing an independent reimplementation.
6. **The schema.** Not a contribution. Your own §2.1 concedes it: *"No published
   work validates one schema against another on the same data. This stays a
   judgement call, made on grounds of compatibility, not measured superiority."*
   Adopting someone else's schema is the correct decision and zero credit.
7. **The labels.** Dead. 800 of 1000, CC BY 4.0.
8. **The model.** Dead as novelty. A configured nnU-Net is a baseline, and
   nnU-Net+clDice is already in ImageCAS-X's table. Frame it as "a strong,
   released baseline", never as a method.

### 2.3 Plainly

**As planned, the project has no contribution.** It has a good pipeline, a
careful configuration, and a stated novelty claim that a paper published in
August 2026 removed. Reframed as 1 + 2 + 3 it has a solid, honest, achievable
one. The reframe is not a consolation prize: it is a *better* project, because
the test set, the ceiling and the baselines all arrive pre-built and the
comparison is against measured human agreement rather than an under-trained
21k-iteration baseline.

---

## 3. The three attacks, in the order they land

### Attack 1 — "What is new here?"

*"Your labels are Bransby et al.'s. Your schema is Bransby et al.'s. Your model
is nnU-Net with the default trainer and a bigger patch. Your evaluation metrics
are Metrics Reloaded's. What did you contribute?"*

**Does the plan have an answer? No.** The plan's answer is at
`Training plan.md:96` — "the contribution is the per-branch labelling" — and it
is false as of August 2026. Worse, the plan still asserts the premise at
`Training plan.md:26-27`: *"per-branch labels are produced by our annotators and
do not exist yet."* A reviewer who reads that sentence and then reads
arXiv:2608.30404 concludes the authors did not check the literature. That is the
single most damaging impression available and it is on page one.

**Fix:** §2.2 item 1. Reframe, and say in the introduction that the labels exist,
that you use them, and that what is missing is the benchmark. Recoverable in an
afternoon of writing. Unrecoverable if left implicit.

### Attack 2 — "Your evaluation cannot support your claims."

*"Single-centre, single-vendor (Siemens 128-slice dual-source). Your reference is
one team's annotation. Your rare classes have 8 and 9 test cases. There is no
external per-branch validation anywhere, and you compare to a human ceiling
rather than to any clinical outcome. What does a number from this mean?"*

**Does the plan have an answer? Partially, and only in the unapplied document.**
`Training plan.md:132-142` has none of it. The proposals do: E12 (thresholds
measure agreement, not utility), E13 (CLAIM item 32 single-centre limitation),
E22 (do not gate on n=8 classes), §3.3 (ASOCA external validation, and *state
plainly that no external per-branch benchmark exists*), §2.5 (Sim & Wright:
no affordable duplicate rate stabilises a 1 %-prevalence class). That is a good
answer. It is sitting in a file marked `status: awaiting review` and has not
reached the plan of record.

One part has no fix: **there is no external per-branch CCTA set.** D19/D35 say so
after a 2023–2026 search; my own search agrees. ASOCA is binary lumen only. The
honest answer is disclosure plus contribution 2 — a second independent annotation
*is* the closest thing to external per-branch validation you can build, which is
another reason it is the right use of annotator time.

### Attack 3 — "Your one architectural claim is unmeasured, and you got the threshold wrong."

*"Your central design decision is a 70 GB patch budget with no heart crop,
justified by arithmetic. nnU-Net Revisited showed VRAM scaling going negative on
three of six datasets. The published ImageCAS patch-size curve stops at 64³. And
the gate you wrote to protect the decision cites the wrong threshold — 12.5 %
when nnU-Net's `lowres_creation_threshold` is 0.25 — so your claimed margin of
'more than double' is actually two to five points."*

**Does the plan have an answer? No, and this is the attack it is least prepared
for.** `Training plan.md:74` still states 12.5 %. `README.md:43` still states
12.5 % publicly. The research note the plan cites as its evidence base —
`vault/Research/Datasets and benchmarks/Research context.md:171,223` — explicitly
asserts the 12.5 % gate is *"correctly stated"*. The corrected figure has reached
`configs/tasks/Dataset710_CoronaryLumen.yaml:33` and
`docs/TRAINING-PHASE1.md:154` and nowhere else.

The measurement that would answer this is ranked **second** in §3.4 (patch-budget
sanity run at `--gpu-mem 24` vs `70`). It should be first, because every compute
estimate in the plan depends on it and because half of it — reading the planner
printout — needs no GPU at all and has never been run.

---

## 4. Internal contradictions

Plan of record vs. proposals, and vs. what has actually shipped.

1. **`vault/Training method/Training plan.md:26-27`** — "ImageCAS ships one merged
   binary lumen mask per case; per-branch labels are produced by our annotators
   and **do not exist yet**." Contradicted by `vault/Proposed changes to the
   training plan.md:36-41`, by `configs/tasks/Dataset711_CoronaryLumenX.yaml`
   (which is built on ImageCAS-X), by `docs/TRAINING-PHASE1.md:24`, and by the
   primary source. **The governing document's central premise is false.**
2. **`Training plan.md:96`** — "The contribution is the per-branch labelling."
   Same cause. See §2.
3. **`Training plan.md:140-141`** — "inter-observer agreement ≈ 0.856 — the
   ceiling, not a target." Flagged **WRONG** in `vault/Research/Verification
   log.md:31-36` (it is ASOCA's *binary lumen* agreement) and in `Proposed
   changes:91-100`. Still in force.
4. **`Training plan.md:74`** — gate (a) "patch fraction ≥ 12.5 %". Wrong; 25 %.
   Corrected in `configs/tasks/Dataset710_CoronaryLumen.yaml:33` and
   `docs/TRAINING-PHASE1.md:154`, not in the plan.
5. **`README.md:43`** — "above the 12.5 % threshold at which nnU-Net would plan a
   cascade." The public README carries a known error. This is the one an external
   reader hits first.
6. **`vault/Research/Datasets and benchmarks/Research context.md:171,223`** —
   asserts the 12.5 % figure and that the plan's gate is "correctly stated".
   Directly contradicted by `vault/Research/Architectures and training/Proposed
   changes.md:18-25` (verified in nnU-Net source at three tags). Two research
   folders disagree, and the plan cites the wrong one as its evidence base
   (`Training plan.md:17-18`).
7. **`vault/README.md:29-31`** — claims `[[Research context]]` is "deliberately
   unresolved: the condensed ImageCAS and nnU-Net notes live **outside** the
   repository." But `vault/Research/Datasets and benchmarks/Research context.md`
   exists and Obsidian resolves the wikilink to it. So the vault README says the
   plan's evidence base is absent, while in fact it resolves to a note carrying
   item 6's error.
8. **`Training plan.md:94-95` and `:81-85`** — calibrates the binary run against
   82.96 %. `Proposed changes:133-141` demotes that as an under-trained baseline
   measured against labels a re-annotation scores at 41.8 % Dice. `docs/TRAINING-
   PHASE1.md:23-24` has already split this into run A (chain test, 82.96 %) and
   run B (the model you keep, 89.8/92.8). The plan knows nothing about run B.
9. **`Training plan.md:86-87`** — "Multiclass model on the same configuration
   **once annotated cases flow**." Superseded: the multiclass model no longer
   waits on annotators (`vault/Research/Class schema/Proposed changes.md` §2).
   The critical path in the plan of record is a path that no longer exists.
10. **`vault/Training method/Plan status.md:44-47`** — "Per-branch labelling has
    not started… Per-branch labels have to be produced by the annotation team."
    Same false premise, stated a second time in a second governing note.
11. **`Plan status.md:24`** and **`Proposed changes:112`** — both reference
    `configs/tasks/Dataset710_Coronary.yaml`, deleted in commit `405e7c3` and
    replaced by `Dataset710_CoronaryLumen.yaml` + `Dataset711_CoronaryLumenX.yaml`.
    Two stale paths.
12. **`Plan status.md:36-37`** — lists class schema, fold scheme, loss, acceptance
    thresholds and annotation protocol as open. The proposals close or narrow four
    of the five. `Plan status.md` is a changelog that no longer tracks the change.
13. **`Proposed changes:50-52`** (§0, option 1) — "redirect annotators to the 200
    cases ImageCAS-X excluded." `vault/Research/Datasets and benchmarks/Proposed
    changes.md` **D12** says those 200 were excluded **for image quality** and
    should "stay out of every split unless reported as a separate non-diagnostic
    set." §0 proposes spending a term of annotator effort on the non-diagnostic
    residue without saying that is what it is. **This is the most consequential
    thing the consolidation dropped.**
14. **`Proposed changes:70-71`** — "six coronary segmentation methods." Eight.
    And they are *lumen* models, so they are comparators for the binary task only
    — `Proposed changes:75-76` ("the comparators for a paired experiment, without
    training any of them") overstates their value for the multiclass work, where
    they are not comparators at all.
15. **`Training plan.md:138`** — asks for an "AHA-segment confusion matrix", while
    the adopted schema is SCCT-18 with landmark cuts removed. Terminology drift;
    small, but it is the kind of thing a reviewer circles.
16. **`Training plan.md:22-23`, `Plan status.md:41`** — "1 × H100 SXM 80 GB per
    job, 24-hour walltime… Everything below assumes that card." Trillium's GPU
    subcluster is 63 nodes of **4× H100 80 GB** (252 GPUs), 24 h max walltime.
    Nothing in 84 notes considers `nnUNetv2_train -num_gpus 4`, which would
    collapse the three-block chain the plan is architected around into roughly one
    block. Whether single-GPU jobs are charged as a quarter node or a whole node I
    could not verify and SciNet docs did not answer; **that one question changes
    the compute budget by 4×** in one direction or the other.
17. **`Proposed changes:230-232`** rules clDice out marked **[reported]**, resting
    partly on Verification log entry 13, which the log itself lists as
    *unfinished* (`Verification log.md:23`). I verified it this session — the
    decision is correct, the evidence chain was not. Same for entry 15's 35
    min/case, which underpins every annotation cost estimate.
18. **Dropped in consolidation, and worth keeping** (folder → consolidated):
    `Losses and topology/Proposed changes.md` §4 (the ban must extend to the
    **per-label** `determine_postprocessing` variant — the more dangerous form for
    a multiclass model); `Architectures and training` §13 (per-class validation
    Dice logging during training — the only way you will notice a rare class still
    improving at the loss-based stop); §6 (ensembling position); `Annotation` §8
    (active learning does not beat random — a useful *don't*); `Annotation` §2
    (the separate 30–50-case dominance mini-study, which is precisely contribution
    2); `Class schema` §2c (derived-dominance prevalence check as a cheap
    rare-class collapse alarm, ~5 minutes to compute, high value).
19. **Split arithmetic.** `Proposed changes:210-211` proposes "5-fold CV over the
    remaining 640". ImageCAS-X's own split is 560/80/160, so your folds will not be
    theirs. Numbers from 5-fold CV over 640 are **not** directly comparable to
    their table; only a run trained on their 560 and scored on their 160 is. Say
    which you are doing.

### Is leaving the plan of record wrong a process risk?

Yes, and it is the risk that has already fired. Commit `405e7c3` (2026-09-20) put
the ImageCAS-X pivot, the 25 % threshold, run B, the leakage constraint and the
89.8/92.8 comparators into `configs/` and `docs/TRAINING-PHASE1.md` — while
`vault/Training method/Training plan.md` still says per-branch labels do not
exist, the ceiling is 0.856, and the gate is 12.5 %. **The implementation has
forked from the plan of record and nothing in `CONTRIBUTING.md` requires them to
converge** (§4 lists a `docs/` branch prefix "for documentation and the vault"
and says nothing about decision records). An operator who follows
`docs/TRAINING-PHASE1.md` and a reader who follows the vault are now working from
two different projects.

**The right workflow is not "hold everything for one review."** Split it:

- **Apply now, no review needed** — §1.1 through §1.7 and the stale paths. These
  are corrections of falsehoods, not decisions. Nobody needs to approve deleting
  a wrong number. Do it in one `docs/` commit: the false premise at
  `Training plan.md:26-27`, the 0.856 ceiling, the 12.5 % gate (plan **and**
  `README.md:43` **and** `Research context.md:171,223`), the renamed config paths,
  six→eight weights, and the §0-option-1/D12 conflict. An hour's work.
- **Decide, then apply** — §0's strategic question, §2.1 schema, §2.2 folds. One
  review, one decision, recorded in `Plan status.md`.
- **Leave as proposals** — §3.4's ranked experiments, §2.3, §2.4. These are
  scheduling, revisited when the baseline exists.

A plan of record whose premise is false is worse than no plan, because it is
cited. The corrections are not the decisions and should not wait on them.

---

## 5. What is entirely missing from 84 notes

I grepped the whole vault, `README.md`, `CONTRIBUTING.md` and `docs/*.md`.

- **Ethics, REB/IRB, data-use agreements: zero hits.** Not one occurrence of REB,
  IRB, ethics, data use agreement, consent, de-identification or anonymisation
  anywhere. You are running a self-hosted Girder copy of a public Chinese CCTA
  dataset, served to a class of student annotators, and in-house annotation is
  proposed. Whether that needs REB review (likely a secondary-use/exempt
  determination, but a determination), whether ImageCAS's terms permit
  redistribution to annotators, and whether student annotators need any training
  record — none of it is written down. §3.7 covers *weight release* licensing and
  stops there. ImageCAS's masks have **no stated licence**, and you are already
  redistributing them via Girder.
- **A clinical user.** Nothing in `Training plan.md` or `Proposed changes.md`
  names who would use a per-branch segmentation or for what. The research folder
  has the material (`What downstream coronary tasks need from a segmentation`,
  `Regulatory and clinical deployment evidence`) and its conclusion is sobering:
  cleared products are *adjunctive, human-supervised* tools, and plaque analysis
  — a main downstream use — needs the **outer wall boundary that a lumen-only
  schema cannot supply by construction** (Metrics `Handoffs.md`). That handoff was
  never answered and never reached the consolidated document.
- **Who reviews the annotations clinically.** SegQueue has gold cases, duplicates
  and "senior review". No note says whether a cardiologist or radiologist ever
  sees a label, or who arbitrates an anatomical disagreement. ImageCAS-X used
  trained analysts under a lead analyst with clinical oversight. Your protocol has
  a role named "senior" and no person behind it.
- **A release plan.** No note covers what gets released, where, when, or in what
  form: weights, labels, code, the evaluation harness, a model card. §3.7 is
  licences only. Contribution 1 is only a contribution if the benchmark is
  reproducible by someone else.
- **What happens if the binary run fails.** The plan assumes run A lands near
  82.96 % and run B near 89.8. There is no written branch for "it comes out at
  0.71". No triage order (labels? spacing? normalisation window? patch fraction?
  epochs truncated by the chain?), no stop rule, no decision about whether to
  proceed to multiclass anyway.
- **Whether the Girder copy of ImageCAS is complete and matches the release.** No
  checksum, no case count assertion, no comparison against the Kaggle
  distribution anywhere in the vault or in `src/segtrain`. `segtrain index` counts
  what it finds; nothing says what it *should* find. Stent prevalence and
  calcification burden are also unknown (D20, §5: "**Unknown.** Not documented").
- **A deadline, a deliverable, or a scope constraint.** Zero hits for thesis,
  committee, supervisor, deadline, defence, or a target venue. Eighty-four notes,
  ~11,600 lines, and nothing states what this is *for* or when it is due. Every
  sequencing judgement in section 6 and 7 below is unanchored as a result, and so
  is every one in the plan. **This is the most surprising omission in the vault.**
- **The annotation tool cannot produce the chosen schema.** `grep -rn centerline`
  over `slicer/` and `src/` returns **nothing**. SegQueue is a voxel
  paint/trim tool ("Divide the mask by trimming, one vessel at a time"; "Circle a
  branch in the 3D view"). Adopting the ImageCAS-X schema means adopting
  nearest-centerline voxel assignment (`Class schema/Proposed changes.md` §3), and
  that is an unbudgeted rewrite of the annotation extension. Nobody costed it.
- **Inference and deployment cost.** §2 accepts "~3–4× more sliding windows at
  inference" and the plan never states what a single case costs to predict at
  ~256³ patches with 50 % overlap on a full 512×512×250 volume. That number
  decides whether the model is usable by anyone.

---

## 6. Highest-risk assumptions, ranked, each with a cheap test

### Rank 1 — "There is a contribution."

Failure wastes **everything**: a term of annotation, several thousand GPU-hours,
and a manuscript that gets desk-rejected on novelty. Everything else on this list
is recoverable; this is not.

**Test, this week, no GPU, ~1 day.** (a) Write the abstract and the "what is new"
paragraph *now*, before any further work, in three sentences that survive being
read next to arXiv:2608.30404. If you cannot, stop and re-scope. (b) Email
Bransby et al. (DTU Compute / Copenhagen University Hospital) two questions: do
they plan a per-segment benchmark or challenge on ImageCAS-X, and would they
comment on a second independent annotation of a subset. Both answers are decisive
and both are free. A "yes, we're running the per-segment benchmark" saves you the
entire project; a "no" is the strongest possible evidence for contribution 1.

### Rank 2 — "The ImageCAS-X download is usable and matches the paper."

The pivot, the schema, the folds, the annotation redirect and the leakage
constraint all rest on it. §0 flags it itself: the Zenodo page says "coronary
segments" without naming the schema.

**Test, ~1 day, no GPU.** Download the 1.4 GB archive. Assert 800 cases; dump
unique label values per case and confirm 14 + background, not a merged mask;
confirm centerlines and `Descriptors.xlsx` are present; map ImageCAS-X case IDs
onto your Girder ImageCAS copy and **compute the intersection between ImageCAS-X's
160 test IDs and ImageCAS official Split-1's 250 test IDs** (D10 — this is the
leakage fact, and it is a five-line script). In the same sitting, verify your
Girder copy: 1000 cases, checksums against the Kaggle release, and per-case
spacing/shape histograms. Spot-check 20 cases against your own conventions. Until
this passes, every number in the plan is conditional.

### Rank 3 — "The 70 GB, no-crop, native-spacing configuration is what the planner actually produces."

If the planner returns a patch fraction of 22 %, or drags target spacing coarse,
or fires the anisotropy branch, the plan's central architectural decision is
wrong and three of its written justifications go with it. The margin is 2–5
points, not "more than double" — the plan's own gate was misstated.

**Test, half a day, no GPU.** Run `segtrain plan --task 710 --gpu-mem 70` and read
the four values (patch fraction vs 0.25, target spacing, batch size, anisotropy
branch). Run `--gpu-mem 24` in the same sitting so the paired comparison is ready.
Read the normalisation window out of `dataset_fingerprint.json`. This is already
the plan's own pre-submission gate; it has simply never been executed, and it is
the cheapest high-information act available.

### Rank 4 — "A term of from-scratch annotation is worth doing."

Test: the cost arithmetic in §7.0 below, on one page, next to §0's three options
and D12's note that the 200 excluded cases are the non-diagnostic ones. Half a
day. My expectation is that it kills the programme in its planned form.

### Rank 5 — "One H100 per job is the right compute unit."

Test: one email to `support@scinet.utoronto.ca` — is a single-GPU job charged as a
quarter node or a whole node, and is `--gpus-per-node=4` DDP supported for a
single job? Then one `nnUNetv2_train -num_gpus 4` smoke run. If a GPU job bills a
whole node, the plan is discarding 75 % of its allocation and the chain
architecture exists to solve a problem that four GPUs mostly dissolve.

### Rank 6 — "SegQueue can produce labels in the chosen schema."

Test: open `slicer/SegQueue/` and answer whether a centerline-named-segment
workflow is a feature or a rewrite. Zero occurrences of "centerline" in the
codebase suggests the latter. One afternoon of reading.

---

## 7. Revised plan

### 7.0 The cost of the plan as written

Stated so the drops are arguable. Both figures are estimates; I flag the
assumptions rather than hide them.

**Compute.** A ~256³ patch at batch 2 is ~35–40 M voxels per step against
nnU-Net's default ~4 M — roughly 9–10× the per-step cost, at the same 250 k
iterations. A default `3d_fullres` run is order 12–24 GPU-hours on an H100, so one
fold here is order **100–200 GPU-hours**, i.e. **4–8 chained 24 h blocks**. The
plan sets `chain_max: 3` (~71 h). *That is probably too few, and nobody has
measured it.* Summing the plan as written — run A, run B, 5-fold multiclass, six
ranked experiments (several paired, so two arms each), the heart-crop run, the
rotation ablation, and a ResEnc run at 3.9× — gives order **2,500–3,500
GPU-hours**: 4–6 months of *continuous* single-GPU occupancy, and with 24 h blocks
and queue waits on a shared 252-GPU subcluster, realistically **8–14 months
elapsed**. I could not verify per-epoch time; treat this as an order of magnitude
whose first digit the Rank-3 test would fix.

**Human.** ImageCAS-X: 470 analyst hours for 800 cases, ~35 min/case, with
automated centerline seeds and a purpose-built Slicer extension. Your annotators
would work without that tool, with 20–30 cases to proficiency. At 60–90 min/case
for 1000 cases that is **1,000–1,500 hours**, plus 5 % gold, 5 % duplicates,
sampled review and arbitration — call it **1,250–1,900 hours**. A student at 6
h/week for a 12-week term contributes ~72 h, so: **17–26 annotators for one term,
or 8–10 for two**, plus the unbudgeted centerline rewrite of the annotation tool,
**to reproduce labels that already exist for 800 of the 1000 cases under CC BY
4.0**. That is the opportunity cost, stated plainly.

### 7.1 The shortest path to a defensible result

1. **Write the contribution claim first.** Three sentences: what is new, against
   what, measured how. Then Rank-1's email to Bransby et al. One day. If the claim
   does not survive, nothing below matters.
2. **Fix the plan of record today.** Apply §1.1–§1.7 plus the stale paths, the
   six→eight correction, the §0/D12 conflict, and `README.md:43`. Record in
   `Plan status.md` that the false premise at `Training plan.md:26-27` was removed
   and why. One commit, one hour. Do **not** wait for the strategic review.
3. **Verify the data.** Rank-2's test: ImageCAS-X download, label-value audit,
   ID intersections, Girder integrity check, 20-case spot check. One day.
4. **Run the CPU gates.** Rank-3's test at `--gpu-mem 70` and `--gpu-mem 24`,
   plus the fingerprint normalisation window and the anisotropy check. Half a day.
   Send the SciNet single-GPU-vs-node question (Rank 5) in parallel.
5. **Train one binary model: run B only, on ImageCAS-X's 560, fold 0, test on
   their sealed 160.** It proves the Trillium chain (run A's stated real purpose),
   produces the presegmentation seeds, gives a comparison against a table that
   means something (89.8 / 91.2 / 92.8), and satisfies the leakage constraint by
   construction. One run instead of two.
6. **Close the schema and the folds by decision, not by research.** Adopt the
   ImageCAS-X 14 classes and their 560/80/160 split. Write the taper rule. Record
   both in `Training plan.md` with "chosen for compatibility, not measured
   superiority" stated out loud. One afternoon.
7. **Train the multiclass model on ImageCAS-X's 560, fold 0.** This is the
   project. Everything before it is setup; everything after it is refinement.
8. **Build the evaluation before you need it, not after.** M5 (the `inf` → `None`
   bug that deletes the worst cases from the means), M8 (per-class headline),
   M6/M12 (NSD tolerance), M2 (detection), M3 (components/Betti), M4 (confusion
   matrix), M7 (MASD). These are the *method* of contribution 1 and they gate
   whether run 7 can be reported at all. M5 and M8 before any number is quoted
   anywhere.
9. **Run the cheap dominance-prevalence sanity check** (`Class schema` §2c):
   predicted non-empty R-/L-PDA/PLA against 91.1 / 5.1 / 3.8 %. Minutes, and it is
   your earliest warning that the rare classes collapsed.
10. **Then, and only then, two experiments.** Binary-init fine-tuning vs
    from-scratch (free, and the leakage constraint is already satisfied by step 5),
    and Skeleton Recall (the one topology loss with a defensible case, judged on
    per-class detection, not mean Dice). Fold 0 only.
11. **Redirect annotation to contribution 2: a 30–60-case independent
    re-annotation** of ImageCAS-X cases, stratified toward left- and co-dominant
    hearts, measuring cross-site protocol reproducibility. ~40 analyst hours, not
    a term. This is the only annotation work that produces a publishable finding,
    and it doubles as the closest available substitute for external per-branch
    validation.
12. **Five-fold CV on the final configuration, external binary check on ASOCA,
    write up.** State the single-centre limitation, the n=8/n=9 rare classes, the
    absence of any external per-branch benchmark, and that the metrics measure
    agreement with a human reference and not clinical utility.

### 7.2 What to drop

- **Run A entirely.** Its two purposes are chain validation (run B does it) and
  comparison to 82.96 % (a number the proposals themselves demote as an
  under-trained baseline scored against labels that disagree with a re-annotation
  at 41.8 % Dice). Beating it proves nothing and costs 100–200 GPU-hours plus the
  official-split plumbing. If you want it, run it *after* there is a result worth
  contextualising, as a one-paragraph appendix.
- **The from-scratch annotation programme for 1000 cases.** Replaced by step 11.
  This is the single largest saving in the plan: roughly 1,250–1,900 analyst hours
  and an unbudgeted annotation-tool rewrite.
- **Annotating the 200 ImageCAS-X-excluded cases.** They were excluded for image
  quality (D12). Do not spend a term on the non-diagnostic residue.
- **The heart-crop paired run.** ~200 GPU-hours to re-litigate a decision already
  made on good evidence, against a failure mode (silently clipped low-running RCA)
  you have already argued is unacceptable. If step 4's planner printout is clean,
  there is nothing to test.
- **The ResEnc paired run.** Your own §3.4 says a paired difference under ~0.5
  Dice is noise, the isolated ablation put it at +0.37, and it costs 3.9× the
  training time against a 24 h wall. You have pre-registered the reason not to run
  it. Don't.
- **The rotation ablation** as a scheduled item. Two arms, ~200 GPU-hours, to
  resolve a disagreement between two papers about mean Dice — a metric you have
  already decided is the wrong one for this task. Keep nnU-Net's default (rotation
  on, mirroring off at train **and** test time) and revisit only if the baseline
  shows an orientation-specific failure.
- **cbDice, per-class inverse-frequency weighting, deep supervision,
  elastic-deformation ablation, TTA/overlap tuning.** Already conditional in the
  proposals. Leave them conditional and do not schedule them. Each needs a
  specific observed failure first.
- **Partial-annotation self-training (§3.4 rank 5).** `[unverified]`, abstract
  only. Its entire value was saving annotator hours, and step 11 removes the hours
  it would save.
- **Uncertainty estimation (E28–E31), active learning (`Annotation` §8), clDice as
  a loss.** Correctly ruled out already; keep them ruled out.
- **`Plan status.md` as a separate note.** It now contains two false statements
  (items 10, 11 in section 4) and duplicates the plan's premise, so it is a second
  place for the plan to go stale. Fold it into a short changelog section inside
  `Training plan.md`.

That leaves roughly **600–900 GPU-hours** (down from 2,500–3,500), **~40 analyst
hours** (down from 1,250–1,900), and a contribution that survives the first
question a reviewer will ask.

---

### One closing observation

The research is good. The verification log is unusually honest — it found its own
error, marked its own unverifiable claims, and corrected its own counts. The code
is ahead of the plan rather than behind it. The failure is not rigour, it is
**routing**: the finding that changes the shape of the project was written down on
2026-09-20, reached `configs/` and `docs/` the same day, and never reached the
document that governs. Six days later the plan of record still says the labels do
not exist. Fix that in the next hour, and the rest of this report is a scheduling
argument rather than a rescue.
