---
tags: [review, verification, decision-record]
status: complete
updated: 2026-09-26
slice: Research/Verification log, every citation in the vault
---

# Review 09 — Citation integrity and the verification log's own reliability

## 1. Verdict (5 lines)

The evidence base is broadly real and, where it carries a number the plan acts on, usually right: every one of the load-bearing [verified] citations resolves and says what the vault claims, including the two the whole §0 pivot rests on.
But the log's sentence **"No invented citation has been found" is now false** — `Centerline extraction metrics from CAT08 and voxel segmentation.md:56` attributes clDice to a paper that does not exist, built from a real author-year, a near-miss title and the wrong journal.
The [reported] tier — the unaudited half — carries a **measured hard-error rate of 3 in 14 (21 %)**, all three being scope/count/attribution errors rather than invented numbers; none inverts a decision, but one ("five of six datasets") is simply miscounted from a table the vault itself reproduces correctly.
The log is internally unreliable as a ledger: its second pass is **off by one** in its entry numbering, it asserts a three-way duplicate that is really two-way, one of its twelve "resolved" entries is not resolved anywhere, and a stale paragraph tells readers that two claims the same file resolves in full are unevidenced.
Net: trust the numbers, distrust the bookkeeping, and stop asserting the absence of fabrication from a 22-claim sample of an 84-note vault.

---

## 2. Resolution table

Outcomes: **A** = exists and says what the vault claims · **B** = exists but the vault misstates it · **C** = exists but unreachable (paywall), claim unverified · **D** = cannot be found to exist (possible fabrication).

| Citation | Claimed source | Outcome | Evidence |
|---|---|---|---|
| Moccia et al. 2018, *"Towards Automatic Coronary Calcium Scoring in a Screening Study with Low-Dose Chest CT"*, IEEE TMI — cited as the origin of clDice | `Research/Metrics and clinical validation/Centerline extraction metrics from CAT08 and voxel segmentation.md:56` | **D — invented (composite)** | No paper with that title exists (exact-phrase search returns only near-neighbours). Real components: *Moccia S, De Momi E, El Hadji S, Mattos LS*, "Blood vessel segmentation algorithms — Review of methods, datasets and evaluation metrics", **Comput Methods Programs Biomed** 2018;158:71–91 (PMID 29544791) — a review, not calcium scoring, not IEEE TMI; and *Lessmann et al.*, "Automatic Calcium Scoring in Low-Dose Chest CT Using Deep Neural Networks With Dilated Convolutions", **IEEE TMI 2018**;37(2):615–625 (PMID 29408789) — right journal and year, different title, different authors. clDice is **Shit, Paetzold, Sekuboyina, Ezhov, Unger, Zhylka, Pluim, Bauer, Menze, CVPR 2021, arXiv:2003.07311** (confirmed via arXiv API). Three independent errors in one citation. |
| arXiv:2608.30404 | Bransby et al., ImageCAS-X, Aug 2026 preprint | **A** | arXiv API: v1 submitted 2026-08-31, 10 authors incl. Bransby, Øksnebjerg, Kjær, de Knegt, Kofoed, Paulsen; cs.CV; "Pre-print (under review)". PDF downloaded and read with `pdftotext`, independent of the HTML render. |
| 10.5281/zenodo.21887809 | ImageCAS-X dataset, 800 scans, CC BY 4.0 | **A** | Zenodo record "ImageCAS-X", Bransby + Paulsen (DTU), published 2026-08-11, **Creative Commons Attribution 4.0 International**, 2 files (dataset + pretrained weights for six methods), **800** CCTA scans. Independently matches §0's description including the two-file contents. |
| ImageCAS-X 14-class schema | §0 / §2.1 | **A** | Supplementary Table 4 + §Centerline labelling: LM, LAD, LCx, D1, D2, OM1, OM2, IM, RCA, R-PDA, R-PLA, L-PDA, L-PLA, Other = **14**. Paper explicitly drops proximal/mid/distal splits for LAD/LCx and treats RCA as one segment — exactly §2.1's rationale. |
| ImageCAS-X Table 1 per-branch inter-observer DSC | §1.1 replacement ceiling; log entry 10 | **A** | Table 1 read verbatim: all-segments 92.8±3.1; RCA 95.3±5.0, LAD 92.3±6.7, LCx 84.8±19.8, D1 79.9±28.7, D2 82.9±24.3, OM1 74.1±32.3, OM2 77.7±29.1, IM 80.6±24.5, R-PDA 82.6±21.9, R-PLA 83.6±18.6, L-PDA 75.1±29.0, L-PLA 70.9±27.2, Other 81.3±17.0. Every vault value matches. Vault omits LM (91.9±13.7). n for L-PDA = 8 and L-PLA = 9 — worth quoting alongside, it is why §2.5's conclusion holds. |
| ImageCAS-X 41.8 % Dice vs original ImageCAS | §1.5; log entry 17 | **A** | Table 2 bottom row: "ImageCAS (labels) 41.8±6.7, HD95 16.15±8.25, βerr 7.0±6.7"; body text identical. |
| ImageCAS-X benchmark table | §1.4 replacement calibration | **A** | Table 2: nnU-Net 89.8±3.2, CAS-Net 91.2±2.8, inter-observer 92.8±3.1. Exact. |
| ImageCAS-X clDice ablation | log entry 13, filed "unfinished" | **A — now resolved** | Table 2: nnU-Net clDice metric 92.3±3.6 → +clDice 91.7±3.9; Betti err 5.6±3.5 → 8.0±4.4. Vault claim exact. Caveat the vault omits: **DSC rose** 89.8 → 90.0. |
| ImageCAS-X 35 min/case with presegmentation | log entry 15, filed "unfinished" | **A — now resolved** | p.11 verbatim: "...in < 2 minutes which is significantly faster than the analysts who averaged **35 minutes** per [case]". Also 200 h centerline + 270 h lumen ÷ 800 = 35.25 min/case; tool named **CoronaryExplorer (v0.1)** at p.4. |
| ImageCAS-X dominance / disease counts | §2.2 fold stratification | **A** | 729 right / 41 left / 30 co-dominant; 388 diseased / 412 not. |
| ImageCAS-X inter-observer Betti error | §2.4 Betti-0 gate anchored on "0.2–0.4" | **A** | Body text reports 0.2; Table 2 row reports 0.4±0.4. Both figures are in the paper, so the range is defensible. |
| 10.1007/s11548-025-03536-5 · PMID 41145776 | Mask SAM 3D, Int J CARS **2026;21:399–410** | **A (bibliography exact); C for the numbers** | Crossref: Tu, Tian, Wang, Deng, Chen, Si, Wang; Int J CARS **vol 21, issue 2, pp 399–410**, online 2025-10-27. PubMed esummary: same, Feb 2026, PMID 41145776. **Volume, page range, year and PMID all correct — this is not the fabrication pattern it superficially resembles.** Full text still paywalled to me; the log's second pass read it via UTORid. |
| 10.1007/s10278-025-01683-4 · PMID 41028564 | "**Song et al.**" TW-MoCoNet, J Imaging Inform Med 2025 | **B — first author wrong** | Crossref author list in order: **Dan Yao, Chengxi Yan, Wang Du, Jingchao Zhang, Zhenzhen Wang, Sha Zhang, Minglei Yang, Shuangfeng Dai.** No "Song" anywhere. Title, DOI and PMID correct. Also J Imaging Inform Med **39(3):2706–2718**, online 2025-09-30 — the log's "2025" with no volume is incomplete. |
| arXiv:2407.01517 · 10.1007/978-3-031-72111-3_5 | cbDice, MICCAI 2024; TopCoW Dice(S) **0** → 38.46 → 43.38 → 48.43 | **A** | I parsed Table 3 out of the arXiv HTML row by row. nnU-Net rows: CE-only (α=0,β=0) Dice(S)=7.012; **CE+Dice default (α=1,β=0) Dice(S)=0**; +clDice 38.46; +cbDice β=2 **43.38**; NexToU+cbDice β=3 **48.43**. The vault is right that the *default* baseline is exactly 0 — a naive read of the table gives 7.012 and would have called the vault wrong. Crossref confirms MICCAI 2024 LNCS pp 46–56. One imprecision: TopCoW is "90 cases, 72 train, **18 for validation and testing**"; the vault calls this "18 test cases". |
| arXiv:2504.01597 (CorSegRec / DPC-Walk) | §3.6: 88.53 Dice vs best baseline 86.08 / 5.25 mm → 1.07 mm; 92.22 % rec. acc. | **A** | Tables parsed from arXiv HTML: ResUNet 82.03±1.39 / 7.51; **ADE-HTL Net 86.08±1.21 / 5.25**±0.43; **CorSegRec 88.53±1.81 / 1.07**±0.60. DPC ablation: RecAcc **92.22**, RecSen **98.20**, RecSpe **82.79**. PDSCA 85.07 / 1.63. The stage-1-only ablation is **87.13 / 5.06** — that, not ResUNet, is where the original vault note's "baseline ResUNet 87.13 %, 5.06 mm" came from; the note mislabelled an ablation row as a baseline and **the log's second pass caught it correctly**. |
| PMID 40239457 / 10.1016/j.media.2025.103578 | (in vault) Qiu et al. three-stage framework | **A** | PubMed: Qiu Y, Shan D, Wang Y et al., **Med Image Anal 103:103578, Jul 2025**. This is the peer-reviewed version of arXiv:2504.01597. §3.6 cites only "DPC-Walk" with no identifier; the journal version exists and should be the citation. |
| arXiv:2211.01607 (ImageCAS, Zeng et al.) | §1.7: −7.38 % at 256²×128, −12.32 % at 128³, p<0.0001; 82.96 % | **A** | PDF §5 verbatim: "the input size of 512×512×256 significantly improves the Dice score by **7.38% (p<0.0001)** and **12.32% (p<0.0001)** compared to that of 256×256×128 and 128×128×128". 82.96 % headline and the +2.13 % channel effect confirmed. Split: 750 train (50 val) / 250 test, 4-fold — consistent with §2.2's "700/50 … 250 test". |
| arXiv:2404.09556 (nnU-Net Revisited) | §3.4: ResEnc L +2.13 (KiTS), +0.77 (AMOS), 3.9× runtime | **A** | Main table: nnU-Net (org.) KiTS 86.04 / AMOS 88.64 / RT 9 h; ResEnc L 88.17 / 89.41 / 35 h. 88.17−86.04 = **2.13**; 89.41−88.64 = **0.77**; 35 ÷ 9 = **3.9×**. All three exact. |
| arXiv:2404.09556, "No-Mamba Base" | §3.5: matched or beat both U-Mamba variants on **five of six** datasets | **B — count wrong** | Same table. No-Mamba (83.69 / 91.89 / 80.57 / 91.26 / 85.98 / 89.04) wins or ties both U-Mamba variants on BTCV, ACDC, LiTS and BraTS (tie with Bot) = **four of six**. It **loses** KiTS (85.98 vs 86.22 / 86.34) and AMOS (89.04 vs 89.13). Lower VRAM is right (12.0 vs 12.4 / 24.9). Conclusion survives — the paper states "the mamba layers actually have no effect on performance" — but the count does not. Error originates in `nnU-Net still beats transformer and Mamba architectures…md` (~line 58) and propagates verbatim to §3.5. |
| arXiv:2307.04472 (Zhang et al., PVA) | §3.4 #5 / §5: "24.29 % of **branches** labelled **reached parity with full annotation**"; §5 says "abstract only, PDF exceeded fetch limits" | **B — scope overstated, and it is reachable** | I downloaded and read the PDF. Abstract and contributions verbatim: "outperforms the competing methods under PVA (24.29% **vessels**) and achieves comparable performance **in trunk continuity** with the baseline model using full annotation (100% vessels)." Parity is on trunk continuity only; the unit is vessels, not branches. §5's stated reason is a **tooling failure, not an access failure**. |
| arXiv:2411.17386 (vesselFM) | §3.5: 29.69 Dice zero-shot on its only CT vascular benchmark | **A** | PDF Table 1: vesselFM zero-shot OCTA 46.94, BvEM 67.49, SMILE-UHURA 74.66, **MSD8 (hepatic vessel, CT) 29.69** (clDice 36.14). MSD8 is the only CT vascular dataset in the evaluation. Minor: the vault's author string "Wittmann, Glandorf, Paetzold, et al." does not match the arXiv byline (Wittmann, Wattenberg, Amiranashvili, Shit, Menze) — likely a different version's author list; flag, do not rely on it. |
| 10.1117/1.JMI.12.1.016002 / PMC11831809 (Kim et al.) | §3.4 #1: in-domain SSL measured **+4.8 Dice** internal (+4.1 external) | **A** | UNETR random-init 0.739 → SSL 0.787 (Site I) = **+4.8**; 0.716 → 0.757 (Site II) = **+4.1**. Backbone is UNETR; nnU-Net appears only as a non-SSL comparison, which is what log entry 5 says. |
| Same paper, external-validation use | `External validation…md:104`: "**nnU-Net trained with self-supervised pretraining**, internally 0.794, externally 0.741, a 5.3-point drop" | **B — attribution wrong** | Numbers correct (nnU-Net 0.794 Site I / 0.741 Site II = 5.3 points). But **SSL was applied only to UNETR**; nnU-Net was the plain CNN baseline. §3.3's "expect a 5–8 Dice-point drop" survives intact; the inference that SSL narrows the generalisation gap must be attributed to the UNETR rows (0.787 → 0.757, 3.0 points), not to nnU-Net. |
| 10.1117/1.JMI.11.3.034001 / PMC11095121 (Hampe et al.) | §3.6: labelling F1 0.95 on reference trees vs 0.74 on extracted trees | **A** | PMC full text: overall F1 **0.95** on reference trees, **0.74** on automatically extracted trees; per-segment RCA 0.90, LAD 0.86, AM 0.84, LCX 0.74, OM 0.74, D 0.73, LM 0.70, R-PLB 0.69, R-PDA 0.69, S 0.54 — matches `Class schema options.md:257–258` exactly. |
| 10.1038/s41597-023-02016-2 / PMC10006074 (ASOCA) | §1.1: 85.6±7.7 is **binary lumen**, not per-branch | **A — the vault's correction is right** | PMC verbatim: "The average Dice Score among the three annotators was 85.6% ± 7.7%", voxel-wise binary lumen vs background over the whole tree; normal 87.4 % vs diseased 83.9 %, p = 0.01. Log entry 1's "WRONG" ruling is sound. |
| PMID 37404087 / 10.2214/AJR.23.29857 | AJR stent editorial, "struts and lumens under ~3 mm" | **C** | esummary: Bowman AW, "Editorial Comment: When Will Coronary Artery Stent Imaging Be Ready for Prime Time?", **AJR 221(5):610**, Nov 2023 — a one-page editorial. Bibliography correct; the 3 mm claim not checkable without access. |
| arXiv:2003.07311 · 2003.08560 · 2607.28327 · 2604.24276 · 2407.01517 · 2504.01597 · 2211.01607 · 2404.09556 · 2307.04472 · 2411.17386 · 2608.30404 | Spot-check of 2025–2026-dated arXiv ids for implausible numbering | **All A (exist, titles match what the vault says they are)** | arXiv API batch. Including the three most suspicious-looking 2026 ids: 2607.28327 = "Same Branches, Different Trees: A Bifurcation Connectedness Metric…" (2026-07-30); 2604.24276 = "Instance Awareness of Multi-class Semantic Segmentation Loss Functions" (2026-04-27); 2608.30404 = ImageCAS-X (2026-08-31). **No arXiv id in the checked set is fabricated or date-implausible.** |
| 10.1007/978-3-032-17734-6_2 | Topology-aware coronary benchmark, Springer LNCS 2026 | **C** | Not opened. The vault's own note says "do not cite it until someone opens it" — correct handling. |
| 10.1186/s13244-024-01827-0 (Föllmer) · PMC11298507 (Interpolation-Split) | log entries 21 and 19, both filed "unreachable" | **C, but wrongly filed** | Both are **open access** — Insights into Imaging is a fully OA journal and PMC11298507 is a PMC record. Neither needs institutional access. Not checked by me for numbers; see worklist. |

---

## 3. Fabrications and misattributions, ranked by damage

1. **The clDice → "Moccia et al. 2018, IEEE TMI" citation is invented.** `Research/Metrics and clinical validation/Centerline extraction metrics from CAT08 and voxel segmentation.md:56`. The title exists nowhere; the author-year belongs to an unrelated CMPB review; the journal-year pair belongs to Lessmann et al.'s calcium-scoring paper; and clDice was introduced by Shit et al. at CVPR 2021. **Damage: reputational and procedural, not technical.** The vault cites clDice *correctly*, with the full nine-author list and doi:10.1109/CVPR46437.2021.01629, in two other notes (`Loss function evidence.md:28`, `Topology-aware losses on thin tubular structures.md:24`), so no decision rests on the bad line. But it falsifies the log's headline reassurance, and if it reached a manuscript it would be a referee-visible fabricated reference. Fix: replace the line with the Shit et al. citation already used elsewhere.
2. **"Song et al." for TW-MoCoNet** (log entry 7 and the source note). The first author is Yao, and the citation is otherwise complete and correct. Damage: a wrong author on a claim the log calls one of its two big verification successes. Trivial to fix, embarrassing to leave.
3. **"No-Mamba beat both U-Mamba variants on five of six datasets"** → four of six. Damage: none to the recommendation, but it is a miscount from a table the vault reproduces correctly in the same file, which is the signature of a summary written without re-reading its own data.
4. **"24.29 % of branches reached parity with full annotation"** → 24.29 % of *vessels*, parity on *trunk continuity only*. Damage: this is ranked experiment 5 and would cost "a term of annotator time"; the corrected claim is materially weaker, because trunk continuity is not this project's acceptance criterion — distal per-branch classes are.
5. **"nnU-Net trained with self-supervised pretraining"** in the external-validation note. Damage: the 5–8-point expectation survives; the SSL-narrows-the-gap inference does not transfer to a CNN and should not be used to argue for experiment 1.
6. **§1.1's "71–81 for the dominance-dependent branches"** — actual range 70.9–83.6 (R-PLA is 83.6). Marked **[verified]**. Damage: small, but it is the one place a [verified] marker sits on a number that does not match the source.
7. **§3.6 cites DPC-Walk with no identifier at all** while a peer-reviewed version exists (Med Image Anal 103:103578, PMID 40239457). Not an error, a completeness gap.

**Not fabricated, contrary to the brief's hypothesis:** both recent-dated Springer citations check out exactly, including page ranges. 10.1007/s11548-025-03536-5 → Int J CARS 21(2):399–410, PMID 41145776. 10.1007/s10278-025-01683-4 → J Imaging Inform Med 39(3):2706–2718, PMID 41028564. And **arXiv:2608.30404 + zenodo.21887809 both resolve to exactly what §0 claims** — 800 scans, 14-class, CC BY 4.0. The strategic pivot is safe.

---

## 4. Marker-integrity failures

**No [verified] marker in the consolidated proposals sits on a factually wrong number.** That is the important result: the marker system did its job on substance. It fails on traceability, in five distinct ways:

| # | Failure | Where |
|---|---|---|
| 1 | **[verified] with no corresponding log entry.** §1.4's replacement calibration table (nnU-Net 89.8 / CAS-Net 91.2 / inter-observer 92.8) and the "~21 k vs ~250 k iterations" claim are marked [verified] but appear nowhere among the log's 22 entries. Correct anyway — I checked. | §1.4 |
| 2 | Same, for §2.1's "[verified] for the schema's existence". No log entry covers the schema. Correct anyway. | §2.1 |
| 3 | **One [verified] spread over a four-part bundle.** §3.5's foundation-model bullet carries a single [verified] covering MedSAM's branching weakness, vesselFM's 29.69, VISTA3D's 128³ patches *and* the Mask SAM 3D quote. Only the last is in the log (entries 4/9). vesselFM I verified; the other two were never audited by anyone. | §3.5 |
| 4 | **Three [verified] markers whose log *body* entry still reads unresolved.** §2.3 (cbDice) → log entry 12 body: `[Searching arXiv for full paper verification...]`. §3.6 (DPC-Walk) → entry 16 body: `[Searching for CorSegRec paper details...]`. §2.5 (Sim & Wright) → entry 22 body: "**Still unreachable**". Only the un-renumbered second pass supports them. A reader auditing the log body would conclude all three markers are unbacked. I confirmed 12 and 16 independently; 22 remains paywalled to me. | §2.3, §2.5, §3.6 |
| 5 | **The log contradicts the proposals outright.** The log's "What the unfinished entries still hold up" paragraph says of entries 12 and 16: "Neither is verified. Treat the proposals resting on them as unevidenced until someone opens those papers." The proposals mark both [verified]. **The proposals are right and the log paragraph is stale** — the same file resolves both in its second pass, and I independently confirmed both. | Log lines 38–42 |
| 6 | One substantive [verified] imprecision: §1.1's "71–81" range (see §3 item 6). | §1.1 |

**Count: 6 marker-integrity failures, 0 of which put a [verified] label on a false claim.** Conversely, the **[reported]** tier under-claims in at least two places: §1.6's test-time-mirroring gap is checkable and true (and live in this repo — `src/segtrain/evaluate.py:56` sets `use_mirroring=True`), and §2.4's Betti anchor is verifiable from the paper.

### The log's arithmetic and narrative claims

- **Arithmetic holds as written:** 12 + 1 + 7 + 2 = 22. ✔
- **But one classification is wrong.** Entry **21** (Föllmer et al., weighted κ 0.808) is listed among the 12 resolved. Its body outcome reads "**Still unreachable**", and no second-pass section covers Föllmer — the second pass's `### 21. Sim & Wright` heading is actually entry **22**. Corrected counts: **resolved 11 · wrong 1 · unreachable 8 · unfinished 2**.
- **After this review the live counts are: resolved 13 · wrong 1 · unreachable 8 · unfinished 0**, because entries 13 and 15 both resolve from the ImageCAS-X PDF and both claims are correct. The log undercounts its own resolvable material.
- **"Entries 4, 9 and 22 turned out to be the same paper" is FALSE.** Entries 4 and 9 are the same paper (Mask SAM 3D). Entry 22 is Sim & Wright 2005, *Physical Therapy* — an unrelated kappa-methods paper. The second pass is **off by one** through that whole region: `### 21. Sim & Wright` should be 22, and `### 4, 9 and 22. Mask SAM 3D` should be 4 and 9.
- **"Open-access success rate — 8/22, 13/22, 1/22"** is stale first-pass arithmetic that contradicts the header's 12/1/7/2 twenty lines above it.
- **"12 of 22 claims have no open-access full text"** matches neither the header (7 unreachable + 2 unfinished) nor reality (two of the eight "unreachable" are in fully open-access venues).
- **"Every failure here is a paywall … Access, not honesty"** is false in three ways: entries 13 and 15 were effort failures against an open PDF; §5's PVA item is a fetch-tool failure against an open PDF; entries 19 and 21 are open access. And "No invented citation has been found" is false as of this review — though note it was only ever an inference from a 22-claim sample of an 84-note vault, which is the structural problem, not the individual sentence.

---

## 5. Measured error rate in the [reported] / [unverified] tier

Sample: **14 claims that carry a number the plan acts on**, drawn from the [reported] and [unverified] tiers, each resolved against the primary source.

| # | Claim | Result |
|---|---|---|
| 1 | ImageCAS −7.38 % at 256²×128 / −12.32 % at 128³, p<0.0001 | correct |
| 2 | ImageCAS 82.96 % headline; 700/50 + 250 test | correct |
| 3 | ResEnc L +2.13 (KiTS) / +0.77 (AMOS) | correct |
| 4 | ResEnc L 3.9× training time | correct |
| 5 | No-Mamba matched/beat U-Mamba on five of six datasets | **WRONG** (four of six) |
| 6 | vesselFM 29.69 Dice zero-shot, only CT vascular benchmark | correct |
| 7 | In-domain SSL +4.8 internal / +4.1 external on ImageCAS | correct |
| 8 | Hampe F1 0.95 reference vs 0.74 extracted | correct |
| 9 | ImageCAS-X 729/41/30 dominance, 388/412 diseased | correct |
| 10 | ImageCAS-X inter-observer Betti error 0.2–0.4 | correct |
| 11 | clDice on coronary CCTA: 92.3→91.7 clDice, 5.6→8.0 Betti | correct (but "no-op or regression" glosses DSC 89.8→90.0) |
| 12 | Partial annotation at 24.29 % reaches parity with full annotation | **WRONG** (vessels, and trunk continuity only) |
| 13 | External validation: 5.3-point drop, "nnU-Net trained with SSL" | **WRONG on attribution** (numbers right; nnU-Net had no SSL) |
| 14 | nnU-Net applies mirroring at test time too | correct — and `src/segtrain/evaluate.py:56` confirms it is live here |

**Hard error rate: 3 / 14 = 21 %** (95 % CI roughly 8–48 % on n = 14 — treat as "about one in five", not as a precise figure). Including item 11's glossed caveat: 4 / 14 = 29 % with some defect.

**Character of the errors matters as much as the rate.** Zero of the three is an invented number. All three are *summary* failures — a miscount, a dropped scope qualifier, an attribution slipped one row across a table — introduced when a note was compressed into a proposal. That is a very different risk profile from fabrication: it means the primary sources were genuinely read, and it means the errors are cheap to catch by re-reading the note's own table, which is exactly what nobody did.

**Practical reading for the user: of the numbers in §§1.6–3.6 that you have not personally opened a paper for, expect roughly one in five to be wrong in scope, count or attribution, and near-zero to be invented. Do not quote any of them in a manuscript without re-reading the source table.**

---

## 6. Ranked verification worklist

**Tier 0 — free, do before spending any library access (minutes each, no login).**

| Rank | Item | Why | Decision it changes |
|---|---|---|---|
| 0a | Fix the **Moccia/clDice** line to Shit et al., CVPR 2021 | Removes the only fabricated citation in the vault | None technically; prevents a fabricated reference reaching a manuscript |
| 0b | **10.1186/s13244-024-01827-0** (Föllmer, κ 0.808) — Insights into Imaging is **open access** | Log files this as "unreachable" and the summary miscounts it as resolved. It is neither. | Finalises §2.5's weighted-κ reporting design |
| 0c | **PMC11298507** (Interpolation-Split, airway) — PMC, **open access** | Filed unreachable; it is not | Whether per-class weighting earns an experiment slot. Low impact either way |
| 0d | Re-mark **arXiv:2307.04472** from [unverified] to [reported] with the corrected scope | Already read; §5's stated reason was a tool failure | Downgrades ranked experiment 5 — see "drop" below |
| 0e | Add **PMID 40239457 / 10.1016/j.media.2025.103578** as the citation for DPC-Walk | Peer-reviewed version of the arXiv preprint §3.6 cites without an id | None; citation hygiene |

**Tier 1 — worth UTORid access, in this order.**

| Rank | Item | Why it is worth a login | Decision it changes |
|---|---|---|---|
| 1 | **10.1007/978-3-032-17734-6_2** — topology-aware coronary benchmark on ASOCA (Springer login wall) | The only work that benchmarks topology-aware losses *on coronary data*. If it really finds them equivalent on primary segments with differences dominated by annotation inconsistency, it settles §2.3 by itself | Could cancel **ranked experiment 3 (Skeleton Recall)** and the **cbDice conditional** outright. Highest decision leverage of anything still closed |
| 2 | **Re-read 10.1007/s11548-025-03536-5** body figures | The log flags two internal inconsistencies (84.5/55.2 in the abstract vs 84.3/55.7 in the body; 8.33 % vs 5.00 % LCX). Only matters if the paper is cited in a manuscript | Which number to quote; nothing structural |
| 3 | **10.1093/ptj/85.3.257** (Sim & Wright) — already read once via the proxy | Re-open only to paste the Table 8 rows verbatim into the log, because §2.5's whole sizing table rests on them and the log body still says "unreachable" | None new; converts a [verified] marker from "trust the second pass" to "traceable" |

**Tier 2 — drop rather than chase.**

| Item | Why drop |
|---|---|
| **10.2214/AJR.23.29857** (AJR stent editorial) | A one-page editorial (221(5):610) supporting one narrative sentence about blooming below 3 mm. Zero decision impact. Either delete the claim or cite the primary stent-imaging literature instead of an editorial |
| **10.1145/3458380.3458383** (JLNet, ACM paywall) | 2021 conference paper on **2D X-ray angiography**, wrong modality, and the closest CCTA analogue (Zhang et al., bspc) resolved at **+0.19 Dice**. Nothing here can justify a scheduled experiment |
| **TubeLoss / vesselFM-CT** (entry 20) | The log's own finding is that the comparison to cbDice/Focal **does not exist in the paper**. There is nothing to fetch. State it as an absence and move on |
| **Entries 5 and 14** (SSL+nnU-Net; persistent-homology losses) | These are literature gaps, not documents. No amount of access resolves them. Record as unmeasured experiments, which §5 already does correctly |
| **Ranked experiment 5 (partial annotation at 24.29 %)** | Now that the claim is corrected to "parity on trunk continuity only", it no longer supports "the largest available lever on annotator hours". Drop or re-scope before committing a term of annotator time |
| **Multi-task centerline head** | Already resolved at +0.19 Dice in 2D X-ray. The log's own conclusion — "a cheap experiment, not a scheduled part of the plan" — is the right call; nothing further to fetch |

**Tier 3 — the cheap workflow that closes the real gap.**

The gap is not access. It is that nobody machine-checks identifiers, and that the log is a narrative document pretending to be a ledger. Two fixes, both hours not weeks:

1. **A ~40-line identifier checker, run over the whole vault, needing no login.** Harvest as I did (`10\.[0-9]{4,}/\S+`, `arXiv:\d{4}\.\d{4,5}`, `PMID \d+`, `PMC\d+`), then hit `api.crossref.org/works/{doi}`, `export.arxiv.org/api/query?id_list=`, `eutils.ncbi.nlm.nih.gov/entrez/eutils/esummary.fcgi?db=pubmed&id=`, `zenodo.org/api/records/{id}`. Emit a CSV of: identifier, resolved title, resolved first author, resolved venue/volume/pages/year, and the vault's *claimed* strings alongside. **Every error class I found except the count miscount would fall out of a diff of those two columns** — the fabricated Moccia title (no record matches), "Song" vs Yao, the missing journal version of DPC-Walk, the incomplete J Imaging Inform Med reference. Cost: one afternoon, then minutes per re-run in CI.
2. **Turn the log into a table with one row per citation** and columns: identifier · vault file:line · marker · outcome · date · who checked · **verbatim quoted passage**. Rules: a marker of [verified] requires a non-empty quote cell; the summary counts are computed from the rows, not typed. Every one of the log's bookkeeping defects — the off-by-one second pass, the stale "entries 12 and 16 are unfinished" paragraph, the two contradictory count blocks, the false three-way-duplicate claim, entry 21 filed as resolved — is a defect that a generated table makes impossible.

Two habits worth adopting alongside: **prefer `arxiv.org/html/<id>v1` over the PDF for any table you are going to quote** (the PDF's column streams scramble — that is precisely how "ResUNet 87.13" and a misread "Dice(S) 7.012" happen), and **cross-check any quoted table row against a second extraction path before writing [verified]**. And replace the sentence "No invented citation has been found" with the honest form: "N of M citations machine-resolved; K checked against their claimed metadata; one fabrication found and corrected."

---

## 7. Coverage

**Harvest (systematic grep over `vault/`, 84 notes):**

- DOIs matching `10.NNNN/…`: **58 unique** (60 raw strings, 2 duplicates with trailing punctuation)
- arXiv ids: **51 unique** (61 raw strings, collapsing 9 base/`vN` pairs)
- PMIDs: **4** — 41145776, 41028564, 40239457, 37404087
- PMCIDs: **24**
- Dataset DOIs: **1** (`10.5281/zenodo.21887809`, counted in the DOI total)
- **Total: 137 identifier strings**, corresponding to roughly 115–120 distinct works after cross-format duplicates (a paper often appears as DOI *and* arXiv *and* PMC).
- Plus an unknown number of **author-year references carrying no identifier at all** — §3.6's "DPC-Walk", §3.5's "MedSAM", and the fabricated Moccia line all live in this class. **This is the highest-risk population in the vault and I could not enumerate it mechanically**; the one fabrication I found is in it, which is not a coincidence.

**Checked: 27 identifiers covering 20 distinct works, plus one negative existence check.** Composition:

- **All 11 [verified]-marked citations** in the consolidated proposals (§0, §1.1 ×2, §1.4, §1.5, §2.1, §2.3, §2.5, §3.5, §3.6, §3.7) — the highest-priority tier, complete.
- **14 numeric [reported]/[unverified] claims** (§5 above).
- **11 arXiv ids spot-checked for fabrication signatures**, deliberately weighted to 2025–2026 dates. None fabricated.
- **4 PMIDs**, all resolved via E-utilities; all four match their claimed titles.
- **One negative check**: the exact title "Towards Automatic Coronary Calcium Scoring in a Screening Study with Low-Dose Chest CT" returns no record.

**Not reached:**

- ~31 of the 58 DOIs, concentrated in `Research/Metrics and clinical validation/` and `Research/Class schema/` — the two largest folders (12 notes each) and the two least represented in the log's 22 entries. **The one fabrication I found is in `Metrics and clinical validation/`. I would not assume it is the only one there.**
- ~40 arXiv ids and 20 PMCIDs, unchecked. Low fabrication risk (a PMCID either resolves or does not) but unchecked for *whether the record matches the claim*.
- Paywalled full texts: entries **3, 6, 11, 19, 20, 21** — of which 19 and 21 are in open-access venues and were mis-filed.
- **Sim & Wright Table 8 (§2.5)** — I could not independently open it. §2.5's sizing table (13 / 126 / 503) rests entirely on the log's second-pass read, which is unquoted. It is the one [verified] claim in the proposals that nobody outside the original session has confirmed.
- Author-year references with no identifier: not enumerated.

**Honest bottom line on coverage: 27 of 137 identifiers (20 %), but 11 of 11 of the [verified] tier (100 %) and 14 numeric [reported] claims. The unaudited remainder is ~80 % of identifiers, weighted toward the two folders least touched by the existing log — and that is where the second fabrication, if there is one, will be.**
