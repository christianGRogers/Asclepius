---
aliases: [Human decisions, D0]
tags: [plans, decision-record, human]
status: living
updated: 2026-10-19
---

# Human decisions

Decisions the judge ruled belong to the project, not the tournament (see
[[Round 1]] §5 and [[Round 2]] §5). Recorded as given by the project lead on
2026-10-05. They are binding on every candidate plan from Round 3 on; a plan
that contradicts one of them cannot win.

| # | Question | Decision | Status |
|---|---|---|---|
| D1 | Side-branch convention | **Territory.** A branch takes the class of its parent: diagonals → LAD, obtuse marginals → LCx, RCA's PDA and PLV → RCA. | Decided |
| D1b | Ramus intermedius | **LCx**, always. (Matches the ImageCAS-X → 4-class mapping already used in the tournament's experiments.) | Decided |
| D2 | Labelling order and double reads | **Every case is labelled twice**, by two annotators. The team is large enough for this. | Decided |
| D3 | tF1 gap tolerance | **1.5 mm.** A gap in a predicted vessel up to 1.5 mm long is forgiven; a longer gap counts as a break and everything past it scores as missed. | Decided |
| D4 | Starting labels shown to annotators | **No four-class starting labels.** Annotators start from the single-class ImageCAS segmentation (the original ImageCAS lumen mask, annotated by physicians) and split it into the four classes. | Decided |
| D5 | Redoing Girder-seeded cases | **Moot: no labelling has happened yet**, so nothing needs redoing. | Decided |
| D0 | Lumen convention | **The original ImageCAS mask** (the current Girder mask; "convention B / thick" in the tournament's terms), split into four classes, is the target, the seed and the reference. Confirmed after being told ~47 % of its voxels sit at 16–38 HU. ImageCAS-X is a secondary cross-check only. | Decided |
| D6 | Acceptance margin (A18) | **0.05 per class.** The final model is accepted if, for each of LM, LAD, LCx and RCA, its tF1 against the team's reads is non-inferior to inter-read tF1 within 0.05. | Decided 2026-10-11 |
| D7 | Redrawing the mask outline | **Keep the outline**, except where the original ImageCAS segmentation has a **major error**, which is expected to be rare. Such corrections are allowed and must be recorded in the case note. | Decided 2026-10-11 |
| D8 | Lumen target (supersedes D0) | **ImageCAS-X exactly as drawn.** The original ImageCAS masks are no longer considered usable as labels. | Decided 2026-10-11 |
| D9 | Class schema | **All 14 ImageCAS-X classes**, no grouping into four vessels: LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other. Supersedes the four-class goal and D1/D1b's grouping. | Decided 2026-10-11 |
| D10 | What annotators start from (supersedes D4) | **The 14-class model's prediction, on all 1000 cases**, including the 800 that already have ImageCAS-X labels. Annotators correct it in SegQueue, which must gain the 14 classes. | Decided 2026-10-11 |
| D11 | Reads per case (supersedes D2) | **One corrected read on the 800 ImageCAS-X cases** (ImageCAS-X is the second, expert read) plus ~10 % blind duplicates there; **two reads on the 200 cases ImageCAS-X does not cover.** | Decided 2026-10-12 |
| D12 | Outline (supersedes D7) | **Annotators may freely redraw the outline to the contrast-filled lumen**, consistent with D8. | Decided 2026-10-12 |
| D13 | Required classes | **LAD, LCx and RCA must be non-empty to submit**; the other 11 classes are optional. | Decided 2026-10-12 |
| D14 | Case order | **ImageCAS-X cases first** (scored automatically against ImageCAS-X), then the 200 unlabelled ones. | Decided 2026-10-12 |
| D15 | Prelabel refresh | **Yes, once**: after ~300 corrected cases, fine-tune and regenerate prelabels for the cases not yet done. | Decided 2026-10-12 |
| D16 | Held-out test | **The 160 ImageCAS-X test cases are annotated last** and kept out of the D15 refresh, so they stay a fair test of the model. | Decided 2026-10-12 |
| D17 | More data and parallel build | **Top priority: source as many CCTA scans as possible, unlabelled included**, so annotator time is never idle. Everything new (14-class SegQueue, new data) is built **in parallel with the live system** and replaces nothing until the project lead validates it. | Decided 2026-10-12 |
| D18 | SegQueue14 defaults | **Accepted as built:** review if mean Dice vs ImageCAS-X < 0.60, or LAD/LCx/RCA < 0.70, or a read pair agrees < 0.60 (adjustable in the `segqueue14.reference` setting); new datasets queue after the 200 unlabelled ImageCAS cases and before the 160 test cases; each annotator's first five reads are always reviewed; deploy by merging into main and installing from there, after validation. | Decided 2026-10-12 |
| D19 | Extra data sources | **HeartSR included** (no licence stated; flagged, not to be redistributed until clarified). The project lead handles access requests and sign-ups to gated sources directly (kept out of the repository). Girder upload minimum chunk size lowered to 1 MB so large CT can be uploaded through nginx. | Decided 2026-10-12 |
| D20 | More data, round 2–3 | **Taiwan AI CUP cardiac CT included** (licence unclear; flagged, not to be redistributed until clarified). **CCTA-Pool stays cardiac-focused**: no non-gated chest/aortic CTA or CTPA (T3). **No animal data** (pig CT skipped). Search agents keep finding and ingesting open-licensed cardiac contrast CT; unclear-licence finds come back to the project lead. | Decided 2026-10-13 |
| D21 | Round-3 data | **Removed:** MVAA 2026 mitral crops (coronaries out of view) and the Kaggle mrdurch set (release exposed patient names). **Kept:** CCA-200 training split (GPL-3.0), stored like every other set. **Not included:** 5 unlicensed GitHub cases, OsiriX CARDIX/MAGIX (no redistribution), Aliza 4D Cardio. | Decided 2026-10-13 |
| D22 | Girder layout (supersedes D10/D11 for the 800 labelled cases) | **The 800 ImageCAS cases that ImageCAS-X already labels are not annotated**; they moved, with the ImageCAS-X labels, to a new collection `ImageCAS-X` (cases/ + labels/). **SegQueue/cases** = the 200 unlabelled ImageCAS cases + a copy of every CCTA-Pool CT volume (CT only; several volumes of one patient are separate cases). **Names:** `<Source>__<Case>[__<Part>]` everywhere (e.g. `ImageCAS__0001.nii.gz`, `ImageCHD__1001.nii.gz`). CCTA-Pool stays as the archive. The live SegQueue's case records are untouched; SegQueue14 is populated from the new layout. Every added volume gets a QC report (nothing deleted). | Decided 2026-10-14 |
| D23 | SegQueue14 queue (supersedes D10, D14, D16 for SegQueue14) | **SegQueue14 serves only the 675 new pooled volumes** (`configs/segqueue14/pool-2026-10.txt` on `claude/segqueue14`: QC annotatable, then limited, then the three sets with suspect header spacing); no ImageCAS case, labelled or not. Each case starts from its **binary TotalSegmentator `coronary_arteries` mask** (`SegQueue/seeds-totalseg`), which annotators divide into the 14 classes; the mask is a helper and is never submitted. Two reads per case (D11, unlabelled). | Decided 2026-10-16 |
| D24 | SegQueue14 release line (supersedes D17's "beside, replaces nothing" for the Slicer module) | **SegQueue14 replaces the 4-class SegQueue module and continues its version numbers**: published as `SegQueue-<v>-Slicer-<x.y>.zip` under `segqueue-v<v>` from **0.14.0**, so SegQueue 0.13's update button installs it; the archive's `SegQueue.py` is a stub that sends "SegQueue" to SegQueue14. SegQueue14 updates itself from then on (only archives carrying SegQueue14). The 4-class module (`slicer/SegQueue`, 0.13.0) is no longer released; the live server and its queue are untouched. | Decided 2026-10-17 |
| D25 | Class schema again (reverses D9; restores D1, D1b) | **Four classes: LM, LAD, LCx, RCA.** Side branches take their parent's class (D1): diagonals → LAD; obtuse marginals, the ramus intermedius (D1b) and a left-sided PDA/PLA → LCx; a right-sided PDA/PLA → RCA; ImageCAS-X "Other" (D3/D4, OM3/OM4) → the nearest LAD/LCx. Kept: ImageCAS-X's lumen (D8), free redrawing of the outline (D12), LAD/LCx/RCA required and LM optional (D13), the 675-volume pool queue with TotalSegmentator seeds (D23). SegQueue14 serves the four classes from module 0.15.0 (protocol 15; a 14-class module is told to update); the icx14 jobs were cancelled and `trillium/icx4` trains the 4-class model on ImageCAS-X collapsed by territory (dataset 715). | Decided 2026-10-17 |
| D26 | Starting point on a seeded case | **Every class starts as a full copy of the vessel seed, hidden by default**; the annotator shows one class at a time and cuts it down to that vessel. The seed itself stays visible as a guide and is never submitted. A case is refused while any voxel is in two classes, which also catches a class left untrimmed. Drafts are never refilled. SegQueue 0.16.0, protocol 16 (a 0.15.0 module is told to update). | Decided 2026-10-17 |
| D27 | Where acceptance (D6) is measured (Round 9 L1) | **A sealed set of pool patients.** D6 is scored on the A30 seal: 150 pool patients, frozen before any read exists, withheld from fine-tuning, extendable to 200–250 on wave-1 evidence (Round 10). The lead chose option (c) **without** its request to the ImageCAS-X authors, so in effect option (a): nobody contacts the authors, and the sealed ImageCAS-X 80 keeps only its one blind model-vs-expert look (A26). | Decided 2026-10-18 |
| D28 | A second icx4 seed (Round 9 L2) | **No.** Only Job A runs. A22's fallback stands: the first retrained decision adds a second seed to its control. | Decided 2026-10-18 |
| D29 | Anomalous anatomy in acceptance (Round 9 L3) | **Own stratum.** ImageALCAPA (30 volumes) and ImageCHD (83) are reported as their own stratum, outside the A10 aggregate. The 74 header-spacing-suspect volumes stay out of A10 until re-gridded. | Decided 2026-10-18 |
| D30 | Serving order for patients with many volumes (Round 9 L4) | **No change.** D23's serving order stands; one-volume-per-patient-first is not adopted. | Decided 2026-10-18 |
| D31 | Emails and requests to outside parties | **Never in the repository.** No email, letter, message or request to anyone outside the project (authors, data holders, institutions) is drafted, templated or stored anywhere in the repository (code, vault, docs, issues or PRs), under any circumstances. Access requests remain the lead's, outside the repository (D19). A plan may say that a source is gated; it may not contain the ask. | Decided 2026-10-18 |
| D32 | Pool-seal size after the A30 grouping QC (#87) | **150 real patients (option A).** Bridge's QC found the seal's name heuristic under-grouped six patients (four single-patient Mendeley-SDN records; Slicer 4D frames `_fNN`), so the 150 listed keys were 133 real patients and 60 of their volumes sat outside the file. Fix, in one explicit PR to `configs/segqueue14/sealed-pool-2026-10.json`: (1) seal every volume of every sealed patient, as the ingest code groups them (`tools/ccta/ingest_open.py`); (2) top up from the pre-registered extension order, skipping entries of already-sealed patients, to 150 real patients; (3) recompute the extension order on real patients. The salted ranking is kept, so this is not a redraw. The guard has refused by patient since #91. | Decided 2026-10-19 |
| D33 | RIDER-2522924559 and RIDER-2551730224 | **One patient.** Same age and sex, three studies within six weeks; merged as the cautious choice. The merged patient is sealed, and its extension-order entry (#79) is dropped. | Decided 2026-10-19 |
| D34 | Model naming | **The project's models are called Janus, numbered sequentially.** icx4 (the 4-class ImageCAS-X model trained on Fir, dataset 715, checkpoint of 2026-10-21; val-80 tF1 0.909, #43) is **Janus 0**. Each later model that is read as a candidate (fine-tunes, retrains) takes the next number, in the order it is read; the vault note of each model states its Janus number. Code identifiers, task ids and workdir names (icx4, Dataset715, task 716) are unchanged. | Decided 2026-10-25 |
| D35 | Where wave-1 fine-tune questions are decided (Round 10 opener; Atlas's option A on #43) | **A non-sealed pool decision set.** About 15 % of the non-sealed, non-ImageCHD pool patients (about 50 of about 347) are held out: drawn at patient level by salted hash within source, and frozen before any read of them is looked at or trained on. Their reads decide fine-tune and recipe questions (A17, A22) and are **never trained on**. The 150-patient pool seal (D27) keeps its single look for acceptance (A19), and val 80 stays the decision set for ImageCAS-X questions. Round 10 sets the exact size, salt and draw, and the power it buys. Not chosen: option B (score fine-tunes only on val 80 and the seal). | Decided 2026-10-25 |
| D36 | Girder consolidation on janus (supersedes DEPLOY.md's two-plugin layout) | **One queue, one group pair, one queue collection.** (1) **One queue:** the old 4-class SegQueue plugin (`girder_segqueue`, 1000 ImageCAS cases, test reads only) is turned off, after a database backup; SegQueue14 is the only queue. (2) **One group pair:** `segqueue14-annotators` and `segqueue14-reviewers`; the old `segqueue-*` groups are deleted. aaron is an annotator and a reviewer. (3) **One collection:** SegQueue14 writes into `SegQueue`; the old queue's folders (`gold`, `incoming`, `submissions`) are archived inside it; the empty `SegQueue14` collection is removed. **`CCTA-Pool` stays as D22's archive, untouched** (the lead, same day: structural organisation matters more than storage); `ImageCAS-X` stays as is. | Decided 2026-10-25; CCTA-Pool part withdrawn the same day |

## The restructure of 2026-10-11 (D8–D10)

> **Partly reversed (D25, 2026-10-17).** The 14-class part of this restructure (D9, and D10's
> 14-class prelabels) no longer holds: D25 restores four classes and D1/D1b's territory grouping.
> D8 (ImageCAS-X's lumen) still holds. This section is kept as the record of 2026-10-11.

The project lead found ImageCAS-X and restructured the project: one model is trained on
ImageCAS-X's 14 classes as drawn (`trillium/icx14`), it predicts all 1000 cases, and the
annotators correct those predictions in SegQueue. D0, D4 and the four-class grouping of
D1/D1b are superseded; the tournament's master plan below is kept as history. D2 (two
reads per case), D3, D6 and D7 are to be re-confirmed for the corrected-prelabel workflow.
SegQueue's 14-class setup and its validation are deferred by the project lead.

## What these change in the master plan

- **D0/D4:** the training target, the seed and the reference are
  all the original ImageCAS mask, split into four classes. This is the master
  plan's default (option B, the projected proxy). The A3 convention monitor runs
  in the direction that flags cases drawn *thin*. Crucible's randomised seed trial
  is withdrawn: no four-class seeds are shown, so there is nothing to randomise.
  The 0.19 tF1 mismatch cost ([[Crucible - A perfect segmentation in the wrong lumen convention loses 0.19 tree-F1]])
  applies only when comparing against ImageCAS-X, which becomes a secondary,
  cross-convention benchmark rather than the reference.
- **D1:** the proxy labels and the rule namer use the territory mapping
  (ImageCAS-X D1, D2, D-Other → LAD; OM, L-PDA, L-PLA, OM-Other → LCx; R-PDA,
  R-PLA → RCA). The trunk-mode comparison in A4 is no longer needed.
- **D2:** with every case read twice, the inter-rater ceiling is measured on all
  1000 cases, not on a 20–30-case subset, and every training case has two labels.
  How to use two reads per case in training (fusion, consensus, disagreement as
  `ignore`, soft labels, or both reads as separate samples) is now an open
  *technical* question for the tournament. See [[Fusing multiple annotations and learning from noisy labels]].
- **D1b:** the A8 ramus switch is set to LCx.
- **D3:** the tF1 tolerance is fixed at 1.5 mm; the one permitted change has been used to confirm it.
- **D5:** no relabelling cost under any option.
- **D6:** A10 is reinstated with a 0.05 per-class margin (A18 resolved). Bridge's power
  analysis (Round 6) is the basis: at 0.05 a model as good as a second reader passes most
  of the time on 100 sealed cases.
- **D7:** the reference stays the ImageCAS mask's extent, split into four classes; a read
  may depart from it only to correct a major error, and says so in its note. The A3
  convention monitor must not halt a wave for noted corrections, but still flags reads
  that redraw the outline without a note. Delta's proposed extent rule is therefore not
  adopted as a general rule.
