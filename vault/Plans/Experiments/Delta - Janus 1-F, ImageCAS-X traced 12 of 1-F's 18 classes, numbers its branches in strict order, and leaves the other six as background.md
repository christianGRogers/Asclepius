---
aliases: [Delta J1F R1 census]
tags: [plans, experiment, janus1-f, track-1-F, round1, D44, D45, imagecas-x, partial-labels, labels]
author: Delta
round: 1
track: 1-F
status: done
updated: 2026-11-12
issue: christianGRogers/Asclepius#303
code: experiments/Delta/j1f_r1/
---

# Janus 1-F: ImageCAS-X traced 12 of 1-F's 18 classes, numbers its branches in strict order, and leaves the other six as background

**Question.** Janus 1-F must segment the four vessels plus D44's 14 branch classes, but its only labels today are
ImageCAS-X's 14 classes. Before choosing a partial-label strategy, three things must be known from the labels
themselves:
1. Where are the voxels of the six classes ImageCAS-X does not name (S1–S3, SN, Conus, RMA)? Inside their parent's
   class (then ImageCAS-X's "LAD" means "LAD or a septal"), or not drawn at all (then its background means
   "background or an untraced branch")? The two need different losses.
2. Can D3 be taken out of "Other" (D3/D4, OM3/OM4)? Only if ImageCAS-X numbers branches in order along the parent.
3. How many cases, and how thick, is each class on the 620 training and locked 100 cases (D45)?

**Method.** Labels only, no CT. ImageCAS-X segmentations from Zenodo (10.5281/zenodo.21887809) fetched by
`fetch_allowed.py`, which **skips every sealed case before downloading it** (80 sealed test + 20 quality-0,
`trillium/sealed_test.json`): 720 files, 0 sealed. The D45 split is recomputed from ids by `split_d45.py`; its
locked-100 and train-620 lists match the pins of record in [[Janus 1-L Round 1]] L-A1 (`bbd9c687…5895`,
`1350cb1f…1152`) exactly.

- `census.py`: per class, presence, volume, 26-connected pieces, centreline length and median lumen radius (Euclidean
  distance transform sampled on the 3-D skeleton). Per case: which side "Other" touches (LAD/D1/D2 vs LCx/OM/IM/L-PDA/
  L-PLA, by a 2-voxel ring), and the **unnamed side branches inside the LAD, LCx and RCA classes**: skeleton branches
  ≥ 5 mm that leave the class's longest path.
- `ordinal.py`: geodesic distance inside the left tree from the LM (or the LAD–LCx junction when there is no LM) to
  each branch's attachment point; D1 vs D2, OM1 vs OM2, and every "Other" piece vs D2 / OM2.
- `j1f_labels.py`: the ImageCAS-X → 1-F stage-1 map (13 values), and a check that its four-class collapse equals
  `trillium/icx4/lib/territory.py` (D25) on every case.
- `parent_copy.py`: the output-layer initialisation used by Delta v1 §5, with a self-test.
- Tables: `summary.py census.json ordinal.json`. Outputs: `census.json`, `ordinal.json`, `j1f_labels.json`.

## Results

### 1. The six untraced classes are background in ImageCAS-X, not hidden in a parent

| Parent class (620 training cases) | unnamed side branches ≥ 5 mm | cases | ≥ 10 mm |
|---|---|---|---|
| LAD (where S1–S3 would be) | 4 | 4 of 620 | 3 |
| LCx | 1 | 1 of 620 | — |
| RCA (where SN, Conus, RMA would be) | 2 | 2 of 620 | 0 |

The locked 100: none in any class. ImageCAS-X's own protocol says why (arXiv:2608.30404, Supplementary B): "Septal
perforators, acute marginals and nodal arteries were not traced", and side branches were not traced where the distal
diameter was < 1 mm. The conus branch is not named there, but the RCA class has no side branch ≥ 10 mm in any case,
so it was not traced either.

**So ImageCAS-X's background is a merged label** {background, S1, S2, S3, SN, Conus, RMA} (Shi et al. 2021's term),
and its LAD and RCA are clean singletons. Training 1-F's six new classes against ImageCAS-X's background as true
negatives would teach the model that septals are background. Ignoring ImageCAS-X's background instead would discard
the vessel/background signal for every other class.

### 2. Branch numbering is strictly ordinal, so D3 comes out of "Other" deterministically

| Check (geodesic attachment distance from the LM) | Train 620 | Locked 100 |
|---|---|---|
| D1 attaches before D2 | **359 of 359** | 64 of 64 |
| OM1 attaches before OM2 | **228 of 228** | 40 of 40 |
| LAD-side "Other": first piece attaches after D2 | **47 of 47** | 7 of 7 |
| LCx-side "Other": first piece attaches after OM2 | 18 of 18 | 5 of 5 |
| LAD-side "Other" pieces per case | 1 piece: 45; 2 pieces: 2 | 1 piece: 7 |
| LCx-side "Other" | 20 cases | 5 cases |

"Other" is in 73 of 620 cases; 47 have a LAD-side piece, 20 a LCx-side piece, 1 piece touches neither side more.
**Rule:** the first LAD-side "Other" piece is **D3**; a second is D4, which D44 lacks, so it goes to LAD by territory
(D1); LCx-side pieces (OM3/OM4) go to LCx. The rule never contradicts the order, because there were no exceptions to
contradict.

Caveat: ImageCAS-X traced D3/D4/OM3/OM4 only if "at least as large as the first or second branches or > 1.8 mm in
diameter at the most proximal end" (Suppl. B). So a **missing D3 is untraced, not absent**: D3 is a partial label even
after this rule. The 47 cases with a D3 are the large ones.

### 3. Classes, counts and calibre on the D45 split

| Class (ImageCAS-X) | 1-F class | train 620: cases (%) | locked 100: cases | median centreline mm | median radius mm |
|---|---|---|---|---|---|
| LM | LM | 611 (98.5) | 98 | 8 | 1.50 |
| LAD | LAD | 620 (100) | 100 | 111 | 0.84 |
| LCx | LCx | 620 (100) | 100 | 68 | 0.83 |
| RCA | RCA | 620 (100) | 100 | 88 | 1.12 |
| D1 | D1 | 611 (98.5) | 98 | 35 | 0.64 |
| D2 | D2 | 359 (57.9) | 64 | 28 | 0.64 |
| Other, LAD side, 1st | D3 | 47 (7.6) | 7 | — | — |
| OM1 | OM1 | 540 (87.1) | 84 | 35 | 0.67 |
| OM2 | OM2 | 229 (36.9) | 40 | 36 | 0.67 |
| IM | Ramus | 149 (24.0) | 24 | 36 | 0.61 |
| R-PDA | PDA | 572 (92.3) | 96 | 46 | 0.61 |
| R-PLA | PLB | 565 (91.1) | 96 | 48 | 0.67 |
| L-PDA | LCx or PDA (Q1) | 38 (6.1) | 4 | 36 | 0.65 |
| L-PLA | LCx or PLB (Q1) | 54 (8.7) | 12 | 16 | 0.61 |
| — | S1–S3, SN, Conus, RMA | **0** | **0** | — | — |

- **Dominance:** a left PDA or PLA with no R-PDA in 46 of 620 (7.4 %) and 4 of 100; both R- and L-PDA in 2 and 1.
  ImageCAS-X reports 5.1 % left-dominant and 3.8 % co-dominant over its 800 (§Coronary Dominance).
- **The R-PDA is in more than one piece in 63 of 620 cases** (10 %); no other branch class exceeds 8. Probably two
  PDAs or a PDA split by the crux; it matters for branch tF1's rooting (one root per piece) and is flagged for round 2.
- **Calibre.** Every traced branch has a median lumen radius of 0.61–0.67 mm (diameter about 1.2–1.3 mm, i.e. 2.4–2.7
  voxels at Janus 0's 0.5 mm), and the 10th percentile sits at 0.50 mm, the distance transform's floor on the
  0.5 mm slice grid. ImageCAS-X's 1 mm tracing floor (Suppl. B) is visible in the labels. The voxel size is 0.29–0.45 mm
  in-plane, 0.5 mm through-plane, in every case. Septals, SN and conus branches, which ImageCAS-X did not trace, are
  usually thinner than the traced diagonals; at 0.5 mm many will be two voxels across or less. **That cannot be
  measured here** (there is no label); the first extended pool reads can measure it (Delta v1 §12).
- **Locked-100 classes with ≥ 30 cases** (Delta v1 §7's gating line): D1, D2, OM1, OM2, PDA, PLB. Ramus (24), D3 (7)
  and the left PDA/PLB (4, 12) are below it.

### 4. The 1-F stage-1 labels collapse exactly to Janus 0's

`j1f_labels.py` over all 720 cases (`--left-pda lcx`; summary in `j1f_labels_summary.txt`):

| | Train 620 | Locked 100 |
|---|---|---|
| Voxels whose four-class collapse differs from `territory.py` (D25) | **40** of 20,855,864 tree voxels, in 2 cases, all of them "Other" | **0** of 3,481,905 |
| "Other" pieces → D3 / → LAD (D4) / → LCx / → nearest (small or two-sided) | 47 / 2 / 20 / 9 | 7 / 0 / 5 / 0 |
| Cases per stage-1 class | LM 611, D1 611, PDA 572, PLB 565, OM1 540, D2 359, OM2 229, Ramus 149, D3 47 | LM 98, D1 98, PDA 96, PLB 96, OM1 84, D2 64, OM2 40, Ramus 24, D3 7 |

The 40 voxels are where the side-by-contact rule and D25's nearest-voxel rule send an "Other" voxel to different
parents. Every non-"Other" voxel maps exactly. **The stage-1 labels are Janus 0's labels, subdivided.**

### 5. Parent-copy initialisation: the 13-class model starts as Janus 0

`parent_copy.py` self-test (numpy, random 32-feature head, 10,000 voxels): after copying each parent's output row to
its children and lowering each territory's biases by log(territory size) (MiB, arXiv:2002.00718, Eq. 8–9), the
13-class softmax collapsed to four classes equals Janus 0's softmax to 1.6e-15, the four-class argmax agrees on
100 % of voxels, and inside a territory the children are exactly tied with the parent. Adding stage 2's six classes the
same way keeps both identities (1.9e-15). **PASS** (`parent_copy_selftest.log`).

## What it changes (Delta v1, track 1-F)

- **Partial labels:** ImageCAS-X's background must become the set {bg, S1–S3, SN, Conus, RMA} once those classes are
  trained (stage 2), and stays plain background while they are not (stage 1). Its LAD and RCA need no change.
- **D3 is trainable now**, on 47 training cases, by the ordinal rule; it is a partial label (large D3s only).
- **Six classes have no ImageCAS-X positive at all**, so they cannot be trained or scored on ImageCAS-X; they wait for
  extended pool reads.
- **Branch gates on the locked 100** can only be set for six classes; the rest are report-only in round 1.
- **The vessel guarantee:** a 1-F model born from Janus 0 by parent copy is Janus 0 at step 0.
