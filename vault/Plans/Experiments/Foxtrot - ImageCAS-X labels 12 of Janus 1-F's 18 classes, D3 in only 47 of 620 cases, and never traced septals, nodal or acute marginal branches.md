---
aliases: [Foxtrot j1f census]
tags: [plans, experiment, track-1-F, janus1-f, D44, D45, census, partial-labels, imagecas-x]
author: Foxtrot
track: 1-F
round: 1
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
---

# ImageCAS-X labels 12 of Janus 1-F's 18 classes, D3 in only 47 of 620 cases, and never traced septals, nodal or acute marginal branches

## Question

What does ImageCAS-X give each of D44/D45's 18 Janus 1-F classes on D45's 620 training cases? Specifically:
- how often each class is present, and how big and thin it is against a 0.5 mm voxel;
- how often a D3 can be recovered from "Other";
- whether the vessels with no ImageCAS-X class (septals S1–S3, SN, conus, RMA) are inside the LAD and RCA labels
  (unlabelled children) or outside the lumen altogether (background);
- how often the posterior branches are left-sided, which sets the size of the L-PDA/L-PLA mapping question.

## Setup

**Cases.**
- D45's 620 training cases: train 560 + dev 44 + 16 of open-36.
- `experiments/Foxtrot/j1f/split620.py` computes the 620 from ImageCAS-X's released file lists and
  `trillium/icx4/sealed_test.json`. The lists match track 1-L's pins of record (L-A1): train 620 `1350cb1f…1152`,
  locked 100 `bbd9c687…5895`.
- **Only the 620 labels were downloaded** (`fetch_620.py`, by range requests on the Zenodo zip, record
  10.5281/zenodo.21887809). No locked-100, sealed or other test label was fetched or opened.
- **One caution, now moot.** D45's salt can be read with the project id (`c0068`) or with ImageCAS-X's own file number
  (`69`). The two readings pick different locked 20; they share only 13 of 20 cases. Until track 1-L's L-A1 fixed the
  `c%04d` reading, I ran on the 613 cases that are training under both readings. The 7 others (c0340, c0416, c0430,
  c0435, c0617, c0624, c0877) were then added. Every number below is on all 620.

**Code** (`experiments/Foxtrot/j1f/`):
- `census14.py`: per case and class, it measures:
  - volume;
  - skeleton length;
  - median lumen diameter along the skeleton (2 × the EDT on the native grid);
  - component count.
- `census14.py` also classes each "Other" component by the labels it touches:
  - diagonal side = LAD/D1/D2;
  - marginal side = LCx/OM1/OM2/IM.
- `census14.py` also skeletonises the LAD-only and RCA-only masks, takes the longest path as the trunk, and counts
  twigs of 3 mm or more hanging off it.
- `census7.py` merges the 7 cases in.
- `summarise14.py` writes the summary.
- `make_labels_1f.py` converts the 14 classes to 1-F's round-1 label map (Foxtrot v1 §3) and counts what each 1-F
  value receives.

Outputs are in `results/`: `census14_per_case.json`, `summary.json`, `summary.md`, `labels_1f_stats.json`,
`labels_1f_summary.txt`.

## Result

### 1. Per class (620 cases)

| ImageCAS-X class | 1-F class | Cases | % | Median mm³ | Median length (mm) | Median diameter mm (p10) |
|---|---|---|---|---|---|---|
| LM | LM | 611 | 98.5 | 98.6 | 8.0 | 3.00 (2.08) |
| LAD | LAD | 620 | 100 | 428.0 | 149.9 | 1.68 (1.42) |
| LCx | LCx | 620 | 100 | 279.8 | 93.9 | 1.67 (1.37) |
| RCA | RCA | 620 | 100 | 597.5 | 116.2 | 2.25 (1.68) |
| D1 | D1 | 611 | 98.5 | 82.9 | 44.7 | 1.27 (1.00) |
| D2 | D2 | 359 | 57.9 | 68.2 | 37.7 | 1.27 (1.00) |
| OM1 | OM1 | 540 | 87.1 | 82.5 | 43.9 | 1.35 (1.00) |
| OM2 | OM2 | 229 | 36.9 | 91.8 | 48.5 | 1.35 (1.09) |
| IM | Ramus | 149 | 24.0 | 68.4 | 40.3 | 1.21 (1.00) |
| R-PDA | PDA | 572 | 92.3 | 93.9 | 52.5 | 1.22 (1.00) |
| R-PLA | PLB | 565 | 91.1 | 114.0 | 59.1 | 1.35 (1.00) |
| L-PDA | PDA or LCx (lead's question) | 38 | 6.1 | 80.6 | 47.2 | 1.31 (1.00) |
| L-PLA | PLB or LCx (lead's question) | 54 | 8.7 | 34.2 | 22.3 | 1.21 (1.00) |
| Other | D3 / LAD (D4) / LCx (OM3–4) | 73 | 11.8 | 65.1 | 39.5 | 1.25 (1.00) |

- **Calibre.** Every labelled side branch has a median diameter of 1.2–1.35 mm and a 10th percentile of about 1.0 mm.
  At D45's 0.5 mm training grid that is 2–2.7 voxels across, with the thin end at 2 voxels. ImageCAS-X does not trace
  a branch whose distal diameter is under 1 mm (its Appendix B), so this floor is partly the protocol's.
- R-PDA has more than one component in 63 cases. This is consistent with a split or doubled PDA; I did not inspect it.

### 2. "Other", and how often a D3 exists

- There are 78 "Other" components in 73 cases:
  - **50 on the diagonal side**, in 48 cases;
  - **20 on the marginal side**, in 20 cases;
  - **8 ambiguous**. 7 of these touch **only the RCA** and 1 touches nothing. A third diagonal or marginal should
    not touch the RCA. These 8 are unexplained, so the conversion ignores them.
- **A D3 can be recovered in 47 of 620 cases (7.6 %).** In those cases the diagonal-side component attached nearest
  the LM/LAD join is the D3, and the case also has D1 and D2.
  - 1 more case has a diagonal-side Other without a D2 (set {LAD, D3}).
  - 2 cases have a second diagonal-side component (a D4 → LAD).
- This is a floor on true D3 prevalence, not an estimate of it. ImageCAS-X traces a third diagonal only if it is
  "at least as large as the first or second branches" or ">1.8 mm in diameter at the most proximal end" (Appendix B).
  Smaller D3s are untraced and sit in background.

### 3. Are the unlabelled branches inside the parent labels?

**No.** Skeletonising the LAD-only mask finds a twig of 3 mm or more off the trunk in **6 of 620** cases, and of
10 mm or more in 3. The RCA-only mask gives 3 and 0. If septals, conus, SN or RMA had been drawn as LAD or RCA, almost
every case would carry several such twigs.

This agrees with ImageCAS-X's protocol: "Septal perforators, acute marginals and nodal arteries were not traced"
(Bransby et al., arXiv:2608.30404, Appendix B). The paper does not mention the conus branch.

**So for S1–S3, SN, RMA, and for the conus as far as can be measured, ImageCAS-X's background holds the vessel.** It
is not a missing child label inside the parent. A network trained on ImageCAS-X as drawn learns to call those vessels
background. Janus 0 has already learned this.

### 4. Posterior branches and dominance

From the labels:

| Dominance | Cases |
|---|---|
| Right | 559 |
| Left (L-PDA or L-PLA only) | 46 |
| Co (both sides) | 13 |
| None | 2 |

- L-PDA is in 38 cases and L-PLA in 54. Only 2 cases have both L-PDA and R-PDA.
- 21 cases have an L-PLA with no L-PDA: a right PDA with a left posterolateral.
- The paper's own count on all 800 is 91.1 % right, 5.1 % left and 3.8 % co-dominant (arXiv:2608.30404).
- **The L-PDA/L-PLA question touches 0.5 % of foreground volume and about 1 case in 8.**

### 5. What the 1-F round-1 label map receives (`make_labels_1f.py`, 620 cases)

| 1-F value | Cases | Share of foreground volume |
|---|---|---|
| LM / LAD / LCx / RCA | 611 / 620 / 620 / 620 | 5.2 / 22.1 / 15.0 / 31.6 % |
| D1 / D2 / **D3** | 611 / 359 / **47** | 4.8 / 2.2 / **0.26** % |
| OM1 / OM2 / Ramus | 540 / 229 / 149 | 4.5 / 1.8 / 1.1 % |
| PDA / PLB | 572 / 565 | 4.6 / 6.2 % |
| set {PDA, LCx} / set {PLB, LCx} (L-PDA, L-PLA) | 38 / 54 | 0.27 / 0.25 % |
| set {LAD, D3} | 1 | < 0.01 % |
| ignore (ambiguous Other) | 8 | < 0.01 % |

### 6. How many present cases a class needs before it can be reported

These are sizes for a 95 % CI half-width h, by the normal approximation:
- **Dice:** the SD is ImageCAS-X's per-segment inter-observer SD (Table 1). They give a scale only; a model's spread
  may differ.
- **Detection:** p = 0.85.

| | h = 0.05 | h = 0.10 | h = 0.15 |
|---|---|---|---|
| Dice, D1 (SD 28.7) | 127 | 32 | 15 |
| Dice, OM1 (SD 32.3, the widest) | 161 | 41 | 18 |
| Dice, R-PLA (SD 18.6, the narrowest) | 54 | 14 | 6 |
| Detection rate, p = 0.85 | 196 | 49 | 22 |

Scaled from the 620, the locked 100 should hold about the following present cases. These are estimates; no locked
label was opened.

| Class | Expected present cases in the locked 100 |
|---|---|
| D1 | 98 |
| PDA | 92 |
| PLB | 91 |
| OM1 | 87 |
| D2 | 58 |
| OM2 | 37 |
| Ramus | 24 |
| D3 | 8 |

## What it changes (for Foxtrot v1)

1. **The 18 classes split into four tiers by evidence, not one partial-label problem:**
   - **Tier A,** labelled and common enough to decide on the locked 100 (about 49 or more present): D1, D2, OM1, PDA,
     PLB.
   - **Tier B,** labelled but only reportable at about ±0.10–0.15: OM2, Ramus.
   - **Tier C,** labelled too rarely to report: D3, at about 8 locked cases.
   - **Tier D,** never traced: S1–S3, SN, RMA and probably the conus.
2. **Tier D cannot be handled as an "unlabelled child of the parent".** On ImageCAS-X those vessels are background,
   so they cannot be learned from ImageCAS-X at all. They need pool reads that draw the lumen as well as the name.
   Their heads should not exist until those reads do.
3. **D3 from ImageCAS-X is a large-D3 class.** It follows the 1.8 mm / "as large as D1–D2" rule, so a pool read's D3
   and ImageCAS-X's D3 differ in convention. Scoring D3 against pool reads must expect lower recall on small D3s.
4. **The L-PDA/L-PLA mapping is small but must be explicit.** Until the lead answers, a set-valued target ({PDA, LCx},
   {PLB, LCx}) lets training proceed without presupposing the answer.
5. **#280's default collapse (PDA, PLB and SN always to RCA) contradicts D25 for left-sided branches**, which go to
   the LCx. In the 620 that affects 46 left-dominant and 13 co-dominant cases.
