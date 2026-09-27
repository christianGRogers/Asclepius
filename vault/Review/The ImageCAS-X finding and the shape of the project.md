---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Proposals §0, §1.1, §1.4, §1.5, §2.2, §3.7
---

# Review 1 — §0: the ImageCAS-X finding, and whether the project's shape should change

Slice: `vault/Proposed changes to the training plan.md` §0 (L34–83), §1.1, §1.4, §1.5, §2.2, §3.7;
`vault/Training method/Training plan.md`; `vault/Research/Verification log.md`.
Primary sources fetched 2026-09-26: arXiv:2608.30404 (abs + HTML v1), Zenodo 21887809,
`github.com/kitbransby/ImageCAS-X`, `kitbransby.github.io/ImageCAS-X`,
`github.com/XiaoweiXu/ImageCAS-...`, PMC10006074 (ASOCA), `gfahrni/open-cardiovasc-imaging-datasets`.

---

## 1. Verdict

1. **The §0 factual claim holds in full.** Paper, Zenodo record, 800 scans, CC BY 4.0, 14 classes, centerlines + meshes + descriptors, six pretrained baselines — every element confirmed from a primary record. No fabricated citation anywhere in this slice.
2. **Every quantitative figure §0–§2.2 leans on is correct**, including 41.8 DSC, the 14-row inter-observer table (LM 91.9 ± 13.7 checked independently and matched), 89.8/91.2/92.8 on 160 cases, and 729/41/30 + 388/412 as two independent partitions of the same 800.
3. **But §0's strategic framing is wrong in one specific and expensive way**: option 1's "redirect annotators to the 200 cases ImageCAS-X excluded" (L51) points the team at 200 scans that four trained analysts rejected as **non-diagnostic** — 114 motion artefact, 76 step artefact, 7 poor contrast mixing. The vault's own `Research/` layer says those must stay out of every split (D12). §0 contradicts it.
4. **The consolidation dropped the single most decision-relevant fact it had already verified**: on ImageCAS-X's own table nnU-Net is the *topological worst* of the six trained methods (Betti 5.6 ± 3.5, HD95 7.08 ± 12.65) against CAS-Net's 1.9 / 2.99 at 6.8 M parameters vs nnU-Net's 153.9 M. §1.4 quotes only the Dice column. The plan's architecture choice has a published counter-example on this exact cohort and §0 does not mention it.
5. **§3.7 is the weakest section in the slice**: the ASOCA row is wrong (data is UK Data Service registered-access, not CC BY 4.0), the ImageCAS row rests on an unsourced distinction between images and masks, and the licensing chain from unlicensed ImageCAS masks → binary model → presegmentation seeds → this project's own CC BY 4.0 label release is unexamined.

**Bottom line: keep §0's finding, rewrite §0's three options, and answer the contribution question — which the plan does not.** The contribution is available and it is *not* the labels.

---

## 2. Errors found, ranked by what they change

### E1. Option 1 sends annotators at the 200 worst scans in the cohort — and the vault knows why they were excluded

- **Vault (L50–52):** "Train the multiclass model on ImageCAS-X now, and redirect annotators to **the 200 cases ImageCAS-X excluded**, to independent verification of a sample, or to a second opinion on the classes where agreement is weakest."
- **Actually true:** arXiv:2608.30404 states the exclusions verbatim: *"200 scans were excluded owing to motion artefacts (n = 114), step artefacts (n = 76), poor contrast mixing (n = 7), static noise (n = 1), incorrect field of view (n = 1), and file corruption (n = 1)."* Sums to 200. The stated criterion is that artefacts *"caused anatomically implausible vessel boundaries"* — i.e. no reliable reference is obtainable, not that nobody got round to them.
- **Evidence:** paper, dataset-construction section. Already in the vault at `Research/Datasets and benchmarks/Fold schemes and split ratios.md:69–70` and `Research/Class schema/Handover/Fold scheme and splits.md:66–67`. `Research/Datasets and benchmarks/Proposed changes.md:35` (D12) says: *"The 200 ImageCAS scans ImageCAS-X excluded for image quality stay out of every split unless reported as a separate 'non-diagnostic' set."* §0 L51 is a direct contradiction of the vault's own proposal.
- **Fix:** delete "the 200 cases ImageCAS-X excluded" from option 1's list of redirections. If the 200 are used at all, they are a **separate artefact-stratified hard test set**, annotated last, reported separately, with the explicit caveat that per-branch inter-observer agreement on them is unknown and will be far below 92.8. Never in a training fold, never in a CV split, never as the first work a new annotator sees.
- **Second-order consequence §0 does not state:** ImageCAS-X's 800 is a **quality-filtered** cohort. A multiclass model trained on it will report performance on the diagnostic 80% of ImageCAS and be silently untested on the 20% that is degraded — which is the fraction that matters clinically. §3.3's external validation (ASOCA) does not cover this, because ASOCA is also curated. Add an artefact-robustness statement to the manuscript plan, or accept it as a named limitation.

### E2. §1.4 quotes one column of a six-row table and drops the column that contradicts the plan

- **Vault (L139–141):** "Replace the calibration target with ImageCAS-X's table: nnU-Net 89.8 ± 3.2, CAS-Net 91.2 ± 2.8, inter-observer 92.8 ± 3.1, all binary lumen on their 160-case test set."
- **Actually true** (benchmark table, confirmed verbatim from `kitbransby.github.io/ImageCAS-X` and paper Table 2):

| Method | DSC | HD95 (mm) | Betti err | clDice | ASSD (mm) |
|---|---|---|---|---|---|
| TotalSegmentator | 70.5 ± 6.2 | 19.59 ± 6.45 | 4.6 ± 2.9 | 76.0 ± 5.3 | 2.73 ± 0.90 |
| 3D-FFR-UNet | 84.9 ± 5.5 | 15.93 ± 20.42 | 4.8 ± 3.5 | 89.8 ± 5.0 | 1.71 ± 1.56 |
| ADE-HTL | 87.7 ± 2.8 | **2.97 ± 3.74** | **1.5 ± 1.5** | 93.2 ± 3.2 | 0.74 ± 0.39 |
| Swin-UNETR | 87.9 ± 2.7 | 3.18 ± 3.68 | 3.8 ± 2.3 | 92.5 ± 3.0 | 0.78 ± 0.36 |
| ImageCAS | 87.9 ± 2.9 | 4.45 ± 4.90 | 4.7 ± 3.1 | 91.7 ± 3.5 | 0.90 ± 0.46 |
| **nnU-Net** | **89.8 ± 3.2** | **7.08 ± 12.65** | **5.6 ± 3.5** | 92.3 ± 3.6 | 1.02 ± 0.75 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 ± 15.36 | **8.0 ± 4.4** | 91.7 ± 3.9 | 1.20 ± 0.99 |
| **CAS-Net** | **91.2 ± 2.8** | **2.99 ± 3.47** | **1.9 ± 1.5** | **93.3 ± 3.2** | **0.73 ± 0.36** |
| Inter-observer | 92.8 ± 3.1 | 2.46 ± 3.62 | 0.4 ± 0.4 | 95.4 ± 3.6 | 0.53 ± 0.33 |
| *ImageCAS labels* | *41.8 ± 6.7* | *16.15 ± 8.25* | *7.0 ± 6.7* | *78.2 ± 6.9* | *2.23 ± 0.94* |

  nnU-Net has the **second-worst Betti error and the second-worst HD95 of the six trained methods**, beaten on topology by every method except 3D-FFR-UNet and TotalSegmentator. CAS-Net dominates it on *every* metric with 6.8 M parameters against nnU-Net's 153.9 M (5-fold ensemble).
- **Evidence:** the vault verified this itself and then dropped it. `Research/Datasets and benchmarks/State of the art on ImageCAS.md:109–111` says: *"CAS-Net beats nnU-Net by 1.4 DSC points (p < 0.001 vs the next best, ADE-HTL) … and much better topology (β err 1.9 vs 5.6). So a plain nnU-Net is a strong but not winning baseline on this data."* `Research/Class schema/Handover/Loss function evidence.md:60` says the same. None of it reaches §0, §1.4, §3.4 or §3.5.
- **Fix:** §1.4 must carry the whole table, and §0 must state plainly that **the plan's chosen architecture is not the best published method on this cohort, and is specifically weak on the metrics the plan says it cares most about** (`Training plan.md:64–69` demotes Dice and promotes clDice, branch detection, component count). That does not mean abandoning nnU-Net — it means the plan's §3.5 "ruled out" list ("nnU-Net still beats transformer and Mamba architectures") is stated too broadly, ADE-HTL and CAS-Net belong in the comparator set, and the Skeleton-Recall experiment (§2.3, priority 3) has a stronger prior than the vault gives it.
- **Also confirmed here:** `Verification log` entry 13 (L140–144, status *unfinished*) claimed nnU-Net+clDice moves clDice 92.3 → 91.7 and Betti 5.6 → 8.0. **Both exactly right** — close entry 13 as RESOLVED. That makes §2.3's "clDice ruled out" the best-evidenced item in the loss section, and it is currently marked `[reported]`.

### E3. §3.7's ASOCA row is wrong: the data is not CC BY 4.0

- **Vault (L393):** "ASOCA (40 cases) | CC BY 4.0 | External-validation results publishable." `Research/Datasets and benchmarks/Data licensing...md:70` says the descriptor "explicitly state[s] CC BY 4.0"; line 12 calls it "CC BY 4.0 with a registration-required access gate, same permissive license."
- **Actually true:** the *article* (Gharleghi et al., Sci Data 2023, PMC10006074) is CC BY 4.0. The **data** is hosted at UK Data Service ReShare 855916 under registered access: applicants must *"provide evidence of ethics review and approval, or waiver regarding their project."* That is a data use agreement, not a CC licence. The vault has conflated the article licence with the data licence — the same category error §1.1 was written to fix.
- **Fix:** change the row to "Registered access (UK Data Service ReShare 855916); ethics approval or waiver required; research and commercial use permitted under the agreement." And move it out of §3.7 into the schedule: **§3.3's external validation has a lead time**, because an ethics waiver has to be obtained and an application approved before the 40 cases can be downloaded. Nothing in §3.3 (L332–342) budgets for that. If no waiver is obtainable, §3.3 does not happen and §3.3's closing paragraph ("state plainly that no external per-branch benchmark exists") becomes the whole of §3.3.
- **Secondary:** the claim that ASOCA-trained weights "can be released under CC BY 4.0" is not supported by any record I could reach.

### E4. §3.7's ImageCAS row asserts a distinction between images and masks that no source states

- **Vault (L391):** "ImageCAS (1000 merged masks) | None stated; **Kaggle distribution carries Apache 2.0 but the masks do not** | Author permission needed before releasing weights trained on them." Marked **[verified]** (L387).
- **What the sources say.** (a) arXiv:2608.30404 Data Availability — the vault's own cited authority — says the ImageCAS volumes are *"publicly available here (kaggle.com/datasets/xiaoxiumedicalai/imagecas) under the Apache 2.0 license."* No image/mask split. (b) `gfahrni/open-cardiovasc-imaging-datasets` lists ImageCAS as "Apache 2.0", 1000 CCTA, voxel-level segmentation. (c) The Kaggle dataset is one dataset with one dataset-level licence field and it ships `<id>/img.nii.gz` **and** `<id>/label.nii.gz` in the same archive. (d) The GitHub repo has no LICENSE file and says *"send emails to me … for the link and the password"* — confirmed by fetch.
- So the **sourced** position is: the Kaggle distribution, which contains the masks, is stated to be Apache 2.0; the GitHub route is unlicensed and gated. Nothing supports "the masks do not". **I could not reach the Kaggle licence field directly** (reCAPTCHA) — so this is "unreachable on the primary record, contradicted by the secondary records", not "confirmed either way".
- **Why it matters:** if the masks are Apache 2.0, the consequence column is wrong. Apache 2.0 permits derivative works and redistribution with NOTICE retention; **no author permission is needed to release weights**. §3.7 currently imposes a blocking dependency on one email to Guangdong that may not exist, and it is the stated reason for considering retraining the binary model on ImageCAS-X instead.
- **Fix:** (1) open the Kaggle page in a browser and screenshot the licence field — 2 minutes, and it is the load-bearing fact. (2) Downgrade the marker from **[verified]** to **[unverified]** until then. (3) Drop the unsourced images/masks distinction. (4) Also fix `Research/.../Data licensing...md:25`, which asserts *"Use in a derivative work … is permitted for research purposes under the doctrine of fair use"* — **fair use is US doctrine; SciNet/Trillium and UofT are Canadian, where the doctrine is fair dealing and is narrower.** A vault note should not be giving jurisdictionally wrong legal advice with no authority cited.

### E5. §1.1's replacement table drops the LM row and every standard deviation

- **Vault (L102–105):** "Replace with ImageCAS-X's per-branch figures: **92.8 merged, ~95 RCA, ~92 LAD, ~85 LCx, 74–84 named branches, 71–81 for the dominance-dependent branches.**" `Verification log` entry 10 (L118–122) transcribes 13 segments + merged.
- **Actually true:** paper Table 1 has **an LM row and an "All segments" row**, i.e. 14 segments + merged. LM = **91.9 ± 13.7 DSC / 95.6 ± 17.6 clDice** (fetched independently; matches `Research/Annotation and label efficiency/How well two annotators agree...md:35` exactly, which is good evidence that transcription is accurate). The consolidated §1.1 and verification-log entry 10 both omit the left main — the one class whose failure is unambiguously clinically consequential.
- **The bigger problem is the SDs.** §1.1 renders OM1 as "74" when the table says **74.1 ± 32.3**, D1 as "79.9 ± 28.7", L-PLA as "70.9 ± 27.2". An SD of 32 on a 0–100 bounded metric is not noise around a mean; it is a bimodal distribution — the vault's own Research note says so (`How well two annotators agree...:2`: *"that distribution is bimodal in practice"*). **You cannot use 74.1 as a "ceiling" for OM1.** The honest statement is: in a substantial minority of cases two trained analysts do not agree that OM1 is there at all. That changes §2.4's acceptance thresholds from a per-class Dice table into a per-class *presence-agreement* gate plus a conditional Dice.
- **Fix:** paste the whole 15-row table with SDs and the `nn` column into §1.1. Never quote a mean from it without its SD.

### E6. §1.1's headline replaces a binary-lumen ceiling with another binary-lumen ceiling

- **Vault (L102):** "Replace with ImageCAS-X's per-branch figures **[verified]**: 92.8 merged, …"
- The error §1.1 identifies is that 85.6 (ASOCA) is *binary lumen* being used as a per-branch ceiling. **92.8 is also binary lumen** — it is the "All segments merged" row and the Table 2 Inter-observer row, the same number. Leading the replacement with 92.8 puts a binary number in exactly the slot the section just condemned, and `Training plan.md:141` is where it will land.
- Also: 85.6 and 92.8 measure *the same quantity* and differ by **7.2 points**. That is a protocol-and-cohort effect on binary inter-observer agreement, which means "the inter-observer ceiling" is not a property of the task. 92.8 was achieved by four analysts on one protocol with **100% lead-analyst review** on a quality-filtered cohort. This project's own annotators should be expected to land *between* 85.6 and 92.8, and §2.4's Betti gate anchored on ImageCAS-X's 0.4 ± 0.4 inter-observer error inherits the same optimism.
- **Fix:** §1.1 leads with the per-segment rows. 92.8 is labelled "binary lumen, ImageCAS-X protocol, quality-filtered cohort, 100% lead review" and used only as §1.4's binary calibration target, never as the multiclass ceiling.

### E7. §2.2's fold scheme breaks comparability with the six free baselines

- **Vault (L210–211):** "Multiclass runs: seal ImageCAS-X's 160-case test set, **5-fold CV over the remaining 640**."
- **Actually true:** the published split is *"training (70%, 560 cases), validation (10%, 80 cases), and test (20%, 160 cases)"*, released as `train/val/test/exclude.txt` (confirmed in `github.com/kitbransby/ImageCAS-X` README). 5-fold CV over 640 gives each fold **512 train / 128 val** — a *different* training budget from the 560 that produced nnU-Net 89.8 and CAS-Net 91.2. A 5-fold ensemble then effectively uses 640. Either way, any number compared to 89.8/91.2 is confounded by the split.
- **Fix:** run **one model on their exact 560/80 split** for the headline comparison to the six baselines, and keep the 5-fold CV over 640 for internal ablations. Say which is which in the manuscript. This is free and §2.2 does not say it.
- **§2.2's leakage trap (L213–218) is correct and the right call**, and the check is cheap: `imageCAS_data_split.xlsx` (ImageCAS Split-1, 700/50/250) against ImageCAS-X's `test.txt` (160). Both are public files. Compute the intersection before the binary model trains, not after.

### E8. Verification-log entry 15 is closable, and the number it was chasing is the cost of option 2

- Entry 15 (L152–158, *unfinished*) asks whether CoronaryExplorer takes ~35 min/case.
- **Confirmed from the paper:** *"Centerline correction required 200 hours total; lumen segmentation correction took 270 hours total across 800 cases"*, **four trained analysts**, using **CoronaryExplorer v0.1, a 3D Slicer v5.10 extension**, with presegmentation from *"a 3D U-Net trained on 100 manually annotated cMPR vessels"* and an automated centerline tracer. 470 h / 800 = **35.3 min/case**. Entry 15 → RESOLVED.
- **This is the price tag §0 option 2 omits.** 470 analyst-hours is the *floor*, achieved with a purpose-built tool, a validated auto-centerline method, and a trained lumen presegmenter. A team without CoronaryExplorer will be slower. §0 L53–56 calls option 2 "defensible if you want labels whose protocol you control end to end" and says it "costs a term of annotator time" — it costs at minimum 470 hours to reproduce something that already exists under CC BY 4.0, plus the tool-build time SegQueue is absorbing.

---

## 3. Weak reasoning and unsupported leaps

### W1. The strategic question §0 asks is the wrong one, and the plan's contribution claim is now false as written

`Training plan.md:96` — *"Beating it is a sanity check, not the contribution. **The contribution is the per-branch labelling.**"* On the evidence, that sentence no longer survives: per-branch labels exist for 800/1000 under CC BY 4.0, produced by four trained analysts with lead review, with a published per-segment inter-observer table. §0 presents three options and says "this is a decision only you can make" (L48) — which is true of the resourcing question and false of the contribution question. **The contribution question has an answer, and it is better than the plan's current one.**

What I verified: **ImageCAS-X does not train or evaluate any automated model on its 14-class labels.** All eight benchmarked methods are binary lumen; Table 1's per-segment numbers are *human-vs-human only*. The project website's per-segment stratification is inter-observer, not model performance. Segment labels are released as data.

So the contribution is available, and it is this, in order of strength:

1. **The first automated per-branch coronary segmentation model on ImageCAS-X, evaluated against the published per-segment inter-observer ceiling.** Nobody has done it. It needs **zero annotation hours** and the reference standard, the test split and six binary comparators are already on Zenodo. This is publishable on its own and is the strongest claim in reach.
2. **One-stage voxel multiclass vs. binary-segmenter-plus-graph-relabelling, measured.** §5 (L237–240) already records that binary-to-multiclass transfer is unmeasured anywhere for coronaries, and §3.6 has Hampe's 0.95→0.74 F1 gap as the motivating number. This is the experiment the field is missing and the plan already has both halves of it.
3. **A third independent protocol on the same scans.** The field's only datapoint on protocol dependence in coronary labels is ImageCAS vs ImageCAS-X at DSC 41.8. *One* datapoint. An independent 100–150-case re-annotation under a written protocol, scored against both ImageCAS-X and the original masks, gives the second — and it is the thing this project's annotation platform is uniquely positioned to produce. It costs ~90 hours at ImageCAS-X's rate, not a term.
4. **The 200 non-diagnostic scans, artefact-stratified.** Genuinely new data on the cases ImageCAS-X explicitly declined. Expensive, low and unknown ceiling, last in the queue.

**Option 2 as written is not defensible and a reviewer will say so.** Redrawing 800 cases of CC BY 4.0 labels is not a contribution; "we wanted to control the protocol" is not an answer to "why did you not use the published labels". **Option 3 (seed and correct) is the right operational choice, but its justification has to be item 3 above — measuring protocol dependence — not "labels you have checked yourself."** And option 1's training-now path should start immediately and in parallel, because it is free and it de-risks everything else.

**§0 should name the contribution. As it stands the plan's stated contribution is refuted by §0's own finding and nothing replaces it.** That is the single largest gap in the slice.

### W2. The 41.8 figure is being read as a one-sided quality judgement, and its magnitude is not explained

§1.5 (L145–148) and `Verification log` entry 17 both read 41.8 as "ImageCAS masks are weak". DSC is **symmetric**: it establishes that two label sets disagree severely, not which is right. The vault's Research layer is properly careful about this (`Can non-experts label vessels as well as experts.md:145–148`: *"This is not proof that non-physicians beat radiologists: the comparison is against ImageCAS-X's own labels (so it is not neutral)"*) — the consolidated §1.5 drops the caveat and asserts the direction.

There is a **genuinely asymmetric** argument available and the vault has it but did not promote it: `ImageCAS annotation protocol and quality control.md:64` — the ImageCAS *method* scores **87.9** against ImageCAS-X labels but **82.96** against its own. A model fits the ImageCAS-X labels better than the labels they were designed for. That is evidence about *self-consistency*, and it is directional. Put it in §1.5.

**The magnitude is also unexplained, and the explanation is actionable.** The paper (supplementary Fig. 7, per the vault) attributes the gap to inclusion of atherosclerotic plaque i.e. outer wall rather than lumen, plus false-positive pulmonary vessels and coronary veins. Run the arithmetic: DSC 41.8 with **clDice 78.2** means the two masks largely follow the *same centerline tree* while disagreeing enormously on *volume*. For a tube, volume ∝ r², so if the narrower mask were nested inside the wider, DSC = 2/(k²+1) → 0.418 gives **k ≈ 1.94× radius**. Some disagreement is non-nested (clDice < 100, Betti err 7.0 = extra components), so the true figure is lower — call it **≈1.5–1.9× radius**, with ASSD 2.23 mm (≈6 voxels at 0.35 mm) consistent. *This is my inference from the published numbers, not the paper's statement.*

If roughly right, it changes three things §1.5 gets partly wrong:

- **§1.5's UI conclusion is the wrong tool.** "The annotation UI must make deleting a seed voxel as cheap as drawing one" (L153) addresses stray components. The dominant correction is *shrinking every vessel by half a radius along its whole length*. That needs a **centerline-anchored radius/boundary adjustment** (level-set or radius spinner on the centerline), not a voxel eraser. Voxel-erasing a 1.9× dilation across a whole coronary tree by hand is the most expensive possible way to do it. This is a concrete SegQueue/Slicer requirement §0 and §1.5 both miss.
- **The plan's sequence rationale inverts.** `Training plan.md:40–44` trains the binary model on all 1000 original masks *specifically because its predictions become the presegmentation seeds*. A model trained on 1.5–1.9×-dilated labels emits 1.5–1.9×-dilated seeds. The seed generator is the one component that must **not** be trained on the weak labels. Train the seeding binary model on ImageCAS-X's 800 lumen labels; keep a separate model on the 1000 original masks only if the 82.96 comparison is wanted, and label it a compatibility run.
- **§1.4 understates itself.** "Beating [82.96] is not evidence of much" (L138) — it is worse than that. Beating 82.96 is evidence of having successfully learned a systematically over-wide lumen. It is not a neutral sanity check; it is a target that rewards the wrong behaviour. `Research/.../State of the art:100–103` already quotes the authors saying ImageCAS *"lacks sufficient segmentation accuracy for reliable benchmarking."* Say that in §1.4.

### W3. "Six pretrained baselines arrive for free — the comparators for a paired experiment"

§0 L75–76. True for the **binary** model, false for the multiclass one, and §0 does not separate them. All six are binary lumen. For the 14-class task **there are no comparators at all**, because no automated method has ever been benchmarked on those labels. That is simultaneously the weakness in this sentence and the reason W1's contribution #1 exists. Also worth naming: **TotalSegmentator (70.5 DSC)** is a free, licence-clean, zero-training coronary baseline that the vault never mentions anywhere.

### W4. Adopting the 14-class schema when 5 of the 14 classes are not evaluable on the sealed test set

§2.1 (L181–187) adopts the 14 classes; §2.2 seals the 160-case test set. Per Table 1's `nn` column (transcribed in `How well two annotators agree...:35–49`, LM row verified against the paper): **L-PDA n = 8, L-PLA n = 9, Other n = 14, IM n = 43, OM2 n = 46** out of 160. A per-class Dice from 8 cases has a 95% CI of roughly ±20 points. **Five of fourteen classes cannot be measured on this test set**, and "Other" (D3/D4/OM3/OM4) is a heterogeneous grab-bag present in 8.75% of cases.

§3.2 (L306) says "some classes will have single-digit case counts" — correct, but nobody put the numbers in and nothing downstream reflects them. §2.1's three-granularity reporting (L189–193) is the right instinct but the specific merge that fixes this is missing: **report PDA and PLA dominance-agnostically** (one PDA class, one PLA class, with dominance as a case-level covariate) alongside the 14-class output. That takes L-PDA+R-PDA to n = 158 and L-PLA+R-PLA to n = 156, both measurable, and loses nothing the 14-class output cannot recover. Adopt the 14 classes for *training and label compatibility*; do not promise 14 evaluable classes.

### W5. Building on a six-week-old unreviewed preprint without saying so

arXiv:2608.30404 comments field reads **"Pre-print (under review)"**, submitted 31 Aug 2026 (v1 only). Zenodo is **v1**, published 11 Aug 2026. §0 (L36–41) and §3.7 (L387) mark all of this **[verified]** without noting that peer review has not happened and that a v2 could revise labels, the split files, or Table 1. §0's caveat (L78–82) is about the *record's* silence on the schema, not about the *paper's* status.

Two concrete fixes: (a) mark every ImageCAS-X-derived number **[verified — preprint, not peer reviewed]**; (b) **pin the Zenodo version DOI, not the concept DOI.** `10.5281/zenodo.21887809` resolves to the record; record which of the two it is and pin the version, or a v2 silently changes the data under a reproducibility statement that cites a floating DOI.

### W6. Nobody has downloaded the dataset

§0 L79–82 says to download it and spot-check 20 cases, and §0 L60–61 says everything in §2 depends on this question. 1.4 GB. **A sub-one-hour download gates a decision about a term of a team's labour**, and the whole of §1.1, §1.4, §2.1, §2.2 and §2.4 is now conditioned on label content nobody has opened. This is the first action, ahead of every other item in the slice.

---

## 4. What's missing — extensions that would change a decision

Ranked by decision impact.

1. **A licensing chain nobody has traced end to end.** §1.5 (L152) says the ImageCAS masks seed the presegmentations annotators are handed. §3.7 (L395–396) says "pick a licence for the labels this project creates — CC BY 4.0." Those two are in tension and §3.7 does not notice. If this project's labels are produced by correcting seeds from a model trained on masks whose licence §3.7 itself calls absent, **the project cannot unilaterally grant CC BY 4.0 on its own label set** — it would be licensing a derivative of an unlicensed work. Under option 3 the labels are also Adapted Material of ImageCAS-X, so they carry a mandatory attribution and modification notice. Resolving E4 (is Kaggle Apache 2.0, and does it cover the masks) resolves this too, which is why E4 is worth two minutes.
2. **A CC BY 4.0 term the vault gets backwards.** `Research/.../Data licensing...md:56` and `:85–86`: *"Models trained on ImageCAS-X data can be released under CC BY 4.0 **or a more restrictive license (e.g., CC BY-SA, CC BY-NC)**."* CC BY 4.0 §3(a) and §2(a)(5)(B) forbid applying terms that restrict recipients from doing what the licence permits on the licensed material. **Releasing weights that embed CC BY 4.0 labels under CC BY-NC is the textbook "no additional restrictions" violation**, and CC BY-SA imports a copyleft the source does not have. If weights are Adapted Material, the permissive-licence options are CC BY 4.0 or CC0-on-your-own-contribution-with-BY-attribution-retained — not NC, not SA. (Whether weights *are* Adapted Material is legally unsettled; the vault asserts it either way without saying so.) Fix the note and the §3.7 consequence column.
3. **Apache 2.0 + CC BY 4.0 mixing.** Both are permissive attribution licences with no copyleft, so a model trained on both can ship under one licence — **provided both attribution obligations are satisfied.** Apache 2.0 §4(d) requires retaining the contents of any NOTICE file in derivative works. Nobody has checked whether the ImageCAS Kaggle distribution carries a NOTICE. Check it while checking the licence field.
4. **The comparability run, and the split-file intersection.** E7 and §2.2's leakage trap. Both are file operations on public `.txt`/`.xlsx`, both are prerequisites for numbers that go in a manuscript, both take minutes. Do them before any GPU time, alongside §3.1's pre-submission gates.
5. **Artefact robustness as a named limitation or a named experiment.** E1's second-order consequence. ImageCAS-X's exclusions give you, for free, a **quality-stratified holdout structure**: 800 diagnostic + 200 non-diagnostic, with the non-diagnostic set already sub-typed (motion 114 / step 76 / other 10). Even without annotating the 200, you can run the trained binary model over them and report *failure modes* — component counts, implausible trees, prediction volume distribution — with no reference standard needed. That is a cheap, novel robustness result on the exact cases the field has excluded. The vault does not consider reference-free evaluation anywhere.
6. **ImageCAS-X's own stratifications, which the project can inherit instead of re-deriving.** The paper stratifies by *disease, image quality, coronary dominance, coronary segment, vessel diameter, and lumen attenuation*, and the scan-level descriptors ship on Zenodo. §3.2's subgroup breakdowns (L328–329) propose dominance, disease and motion-exposed segments. **Adopt their six strata verbatim** — your subgroup tables become directly comparable to a published benchmark, at zero cost. §3.3's "report contrast enhancement and edge sharpness alongside" is partly redundant with their image-quality and lumen-attenuation descriptors.
7. **Other per-branch coronary datasets: none.** Searched; nothing in CCTA since ImageCAS-X carries per-branch voxel labels. Confirmed against `gfahrni/open-cardiovasc-imaging-datasets` (ImageCAS, ImageALCAPA, COCA, 3D CAS Images, MultiD4CAD — none per-branch; ImageCAS-X and ASOCA not yet listed) and against the paper's own related-work framing. PCCTA120 is two classes (`Verification log` L215–216). ARCADE is 2D X-ray. **§0 should record this explicitly as a positive finding**: ImageCAS-X is not one option among several, it is the only one, which is exactly why compatibility with its schema (§2.1) is the right basis for the decision and why "we made our own incompatible schema" would be the worst outcome.
8. **No leaderboard, and no submission mechanism.** `kitbransby.github.io/ImageCAS-X` is a static benchmark table, not an evaluation server; no submission process is described anywhere. So the project **will not** be ranked against a live leaderboard — but it will be compared to that static table, and only its binary model is comparable to it. Record that as the reason contribution #1 (multiclass) and the binary comparability run (E7) are separate deliverables.
9. **Method reuse from the release.** The ImageCAS-X code is **MIT** (`github.com/kitbransby/ImageCAS-X`, confirmed) and its dataloader handles the 14-class masks with an option to binarize. `CoronaryExplorer v0.1` is a 3D Slicer v5.10 extension. Commit 27b2b13 in this repo removed the Slicer monitor; §2.1 L195–196 says adopting the schema means adopting centerline-nearest-point label construction, "which has direct consequences for the Slicer tool." **Check whether CoronaryExplorer is released before building a replacement.** The paper names it with a version number; if it is public, that is the single largest tool-build saving available, and 35 min/case becomes an achievable target rather than an aspiration. I could not confirm its release status from the sources I reached.

---

## 5. Confidence, and what I could not check

**High confidence (primary record, fetched this session):** paper exists with the title, authors and abstract the vault gives; Zenodo record ImageCAS-X v1, 11 Aug 2026, CC BY 4.0, 800 scans, `ImageCAS-X_dataset.zip` 1.4 GB + `pretrained_weights.zip` 1.6 GB, six methods, centerlines + meshes + scan-level descriptors (dominance, image quality, CHD); 14-class schema with the exact class list and IDs (from **paper and GitHub README**, two artefacts, *not* from the Zenodo record — §0's caveat at L78–82 is correct and can now be tightened to "confirmed from the paper and the code repository"); 41.8 ± 6.7 DSC / 16.15 HD95 / 7.0 Betti / 78.2 clDice / 2.23 ASSD; the full 10-row benchmark table; split 560/80/160 with released split files; the 200 exclusion reasons summing to 200; 729/41/30 dominance and 388/412 disease **both stated for the same 800** (no conflation — they are two independent partitions, the reviewer's suspicion is resolved); 200 h + 270 h across four analysts = 35.3 min/case; CoronaryExplorer v0.1 on Slicer v5.10; centerline-nearest-point label propagation; all 160 test cases dual-annotated blind; arXiv comments "Pre-print (under review)", v1 only, submitted 31 Aug 2026; repo licence MIT; ImageCAS GitHub has no LICENSE and gates download by email; ASOCA data on UK Data Service ReShare 855916 requiring ethics evidence.

**Medium confidence:** LM 91.9 ± 13.7 / 95.6 ± 17.6 and the "All segments" row 92.8 ± 3.1 / 95.4 ± 3.6 — retrieved from paper Table 1 and matching the vault's transcription exactly, which cross-validates both. The other 13 rows I did **not** independently retrieve; one fetch declined to reproduce the table on copyright grounds. Given LM matched to the decimal, I judge the vault's transcription reliable, but the 13 rows are strictly **vault-sourced, cross-checked on one row**.

**Could not check:**
- **The Kaggle licence field for ImageCAS** — reCAPTCHA-gated. This is the one fact E4 turns on and it is the highest-value unresolved item in the slice. Two secondary sources (the ImageCAS-X paper's Data Availability, and the open-cardiovasc catalog) say Apache 2.0; the vault says the masks are excluded from it, with no source. **Unreachable, not confirmed.**
- **Whether `10.5281/zenodo.21887809` is the concept or the version DOI**, and therefore whether the vault's citation pins a version.
- **Whether CoronaryExplorer v0.1 is publicly released.**
- **The ImageCAS Split-1 ↔ ImageCAS-X test-160 intersection** — needs both split files downloaded. Computable locally in minutes; §2.2 L217–218 already asks for it.
- **The actual label content of the Zenodo archive** — nobody in this project has downloaded it, including me. Every claim about label granularity, taper behaviour, bifurcation ownership and voxel counts remains paper-sourced.
- **Springer/ScienceDirect items outside this slice** (the vault's second pass resolved several through a UofT proxy I do not have).

**One thing I looked for and did not find: any sign of fabrication.** Every citation in this slice resolves to a real artefact, and every number I could reach was right. The failures here are all failures of *consolidation* — the `Research/` layer is materially stronger than the file that summarises it, and the specific things it lost (nnU-Net's topology ranking, the SDs and `nn` counts on Table 1, the exclusion reasons, the 87.9-vs-82.96 self-consistency argument, the non-neutrality caveat on 41.8) are the things that change decisions.
