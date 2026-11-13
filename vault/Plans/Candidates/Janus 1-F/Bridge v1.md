---
tags: [plans/candidate, bridge, janus-1f, branches, partial-labels, fir, D44, D45, round1]
author: Bridge
track: Janus 1-F
round: 1
updated: 2026-11-11
issue: christianGRogers/Asclepius#303
---

# Bridge v1 (Janus 1-F): segment branch types, name them by position, and keep the untraced classes dormant until reads exist

## 0. Position in one paragraph

Janus 1-F should **not** be a network with 18 softmax classes trained on ImageCAS-X as drawn. Build it in two steps:

1. **Stage 1, a typed network.** Warm-start from Janus 0. It segments **13 branch types**: LM, LAD, LCx, RCA, DIAG,
   SEPT, OM, RAMUS, SN, CONUS, RMA, PDA, PLB.
   - Its loss is **marginal** (Shi et al. 2021) wherever a label is coarser than the types.
   - ImageCAS-X never traced septals, nodal arteries or acute marginals, so in ImageCAS-X cases background is the
     marginal over background, SEPT, SN, CONUS and RMA.
   - A 4-class pool read gives each parent as the marginal over the parent and its branch types.
2. **Stage 2, a deterministic namer.** The ordinals (D1–D3, S1–S3, OM1–OM2) come from **origin order along the
   parent**, and fourth or later branches go back to the parent (D44 lists no D4 or OM3). The namer also records
   **which vessel each PDA, PLB and SN arises from**, so whichever way the lead maps L-PDA/L-PLA, the trained network
   does not change.

Four findings drive this design, each with code and a note in this PR:

- **(a)** On the 620 training cases, ImageCAS-X's ordinals are a function of position: D1's origin is proximal to D2's in **356 of 356** cases with both (2 more lack a measurable origin), OM1's to OM2's in **228 of 228**, and re-deriving D1/D2/D3 and OM1/OM2/Other from origin order reproduces ImageCAS-X's own names for **99.8 %** of diagonal and **99.9 %** of marginal branches (99.93 % of their voxels).
- **(b)** The project's own 14-class run never predicted a single branch class in two 450-epoch attempts (about 46
  GPU-h). Its classes appeared in order of size.
- **(c)** ImageCAS-X states that septals, acute marginals and nodal arteries **were not traced**. They are background in
  its labels, so plain cross-entropy would teach 1-F to erase them.
- **(d)** "Other" holds a third LAD-side branch (a D3) in **48** (7.7 %; 2 more hold a D4) of the 620 cases.

The four vessels keep a guarantee. If 1-F's own vessels fail the locked-100 gate against Janus 0, the shipped output
is a **composite**: Janus 0's vessels, with 1-F's branch voxels relabelled inside them.

## 1. What this plan read

- `vault/Plans/README.md`, the Master plan, [[Round 10]], [[Human decisions]] (D1, D1b, D8, D9, D10, D22, D25, D27,
  D34, D35, D38–D40, D44, D45), the Janus 0 results ([[icx4 - Results]], #43), #280 and its collapse table, #302.
- This track has no previous round.
- Bridge's own earlier work that bears on naming:
  - [[Bridge - Trillium naming result on the master model]]: on four vessels, **the network's own names beat rule
    renaming**, R − D = −0.013 [−0.025, −0.002].
  - [[Bridge - A generic learned vertex labeller is worse than structured rules at 5-40 training cases]].
  - [[Bridge - At n = 100 the A10 rule rejects a human-level model, and most open-set tests cannot see their effect]]:
    the MDE table at n = 100.

The Round-5 result is why this plan keeps **typing** inside the network and gives the rule only the **ordinal**, which a
patch cannot see and which, on ImageCAS-X, is fixed by position (§2.1).

## 2. Evidence from this round (CPU, this PR)

Code: `experiments/Bridge/j1f_r1/`.
- `split620.py` rebuilds D45's split from `trillium/sealed_test.json` and ImageCAS-X's file lists, and asserts
  620/100, no overlap and no sealed case.
- `fetch620.py` downloads **only the 620 training cases'** labels; no locked-100, sealed or quality-0 label is
  fetched.
- `census.py` measures per-case geometry; `analyse.py` writes the summary (`census_summary.json`).
- `icx14_emergence.py` reads the returned icx14 logs.

### 2.1 Ordinals are position: D1/D2 and OM1/OM2 are ordered by origin along the parent

[[Bridge - On the 620 training cases ImageCAS-X's ordinal branch names follow origin order along the parent]]

| Pair (on the parent) | Cases with both | Ordered proximal-to-distal | Reversed | No origin measured |
|---|---|---|---|---|
| D1 before D2 (LAD) | 358 | **356** | **0** | 2 |
| OM1 before OM2 (LCx) | 229 | **228** | **0** | 1 |

| Re-derive ordinals from type + origin order | Branches | Branch agreement with ImageCAS-X | Voxel agreement |
|---|---|---|---|
| Diagonals (D1, D2, LAD-side "Other") | 1017 | 0.998 (D1 1.000, D2 0.997, Other 0.98) | 0.9993 |
| Marginals (OM1, OM2, LCx-side "Other") | 786 | 0.999 (OM1 1.000, OM2 1.000, Other 0.95) | 0.9993 |

The few disagreements are cases where a branch had no measurable origin (it does not touch its parent in the mask).

Consequence: a network only has to say "this is a diagonal". Whether it is the first or the second is counting along the
LAD, which a 128 mm patch at 0.5 mm often cannot see whole (Round 5's naming finding) and a graph step does exactly.
This also gives **D3 labels for free**: the third diagonal by origin is D3, whether ImageCAS-X called it "Other" or not.

### 2.2 The 14-class lesson (D9/D10, `trillium/icx14`, reversed by D25)

[[Bridge - In the cancelled 14-class run no branch class was ever predicted, and classes appeared in order of size]]

| Class | Cases (of 640) | First epoch with val pseudo-Dice > 0, job 1 / job 2 |
|---|---|---|
| LAD, LCx | 640 | 27 / 21; 34 / 21 |
| RCA | 640 | 61 / 58 |
| LM | 630 | 130 / 172 |
| R-PLA | 589 | never / 424 (32 of 456 epochs) |
| D1, D2, OM1, OM2, IM, R-PDA, L-PDA, L-PLA, Other | 38–631 | **never in 446 / 456 epochs** |

- The run was cancelled by D25 at about 45 % of its 1000-epoch schedule, so this does not show that branches *cannot*
  be learned.
- It does show that a from-scratch 18-way softmax spends **more than 23 GPU-h before the first branch appears**, and
  that order of emergence follows class size. D1 is in 631 cases and still never appeared, so frequency is not the
  limit; voxel share is.

Three things in this plan remove that delay:
- **warm-start** (the vessels are already learned);
- **head initialisation from the parent channel** (§4.3);
- **pooling the ordinals into types**, which multiplies each type's voxel share (DIAG = D1 + D2 + D3 voxels).

### 2.3 What ImageCAS-X traced and what it did not (Suppl. B of arXiv 2608.30404, read 2026-11-11)

- "Side branches were not traced where the connection to the parent vessel was unclear, … or where the diameter at the
  most distal point was <1 mm."
- "**Septal perforators, acute marginals and nodal arteries were not traced.**"
- D3/D4/OM3/OM4 were labelled "Other" "if they were at least as large as the first or second branches or >1.8 mm in
  diameter at the most proximal end".
- Where a side branch bifurcated, only the larger limb was traced (both if ≥ 1.8 mm).

Conus is not named. It is not in the 18-segment model, so it is treated as untraced.

So, against D44's 14 branch classes:

| D44 class | In ImageCAS-X | Training signal from ImageCAS-X | Label in this plan |
|---|---|---|---|
| D1, D2 | D1, D2 | exact | DIAG + ordinal |
| D3 | inside "Other" (LAD side), only when large | exact where traced; untraced small D3 is background | DIAG + ordinal |
| OM1, OM2 | OM1, OM2 | exact | OM + ordinal |
| Ramus | IM | exact | RAMUS |
| PDA, PLB | R-PDA, R-PLA (+ L-PDA, L-PLA) | exact | PDA, PLB (side recorded by the namer) |
| S1–S3, SN, RMA | **not traced** (background) | none, and background is wrong for them | SEPT, SN, RMA: **dormant** (marginal with background) |
| Conus | not traced | none | CONUS: dormant |

### 2.4 Census of the 620 (frequency, volume, calibre)

[[Bridge - Census of ImageCAS-X branch classes on the 620 Janus 1 training cases]]

| Class | Cases (of 620) | Median volume mm³ | Median length mm | Median lumen diameter mm (10th pct) |
|---|---|---|---|---|
| LM | 611 | 98.6 | 7.7 | 3.00 (2.64) |
| LAD | 620 | 428 | 111 | 1.68 (1.21) |
| LCx | 620 | 280 | 68.5 | 1.67 (1.19) |
| RCA | 620 | 598 | 87.5 | 2.25 (1.87) |
| D1 | 611 | 82.9 | 34.9 | 1.27 (1.00) |
| D2 | 359 | 68.2 | 28.0 | 1.27 (1.00) |
| OM1 | 540 | 82.5 | 35.1 | 1.35 (1.00) |
| OM2 | 229 | 91.8 | 35.9 | 1.35 (1.00) |
| IM (Ramus) | 149 | 68.4 | 36.3 | 1.21 (1.00) |
| R-PDA | 572 | 93.9 | 46.2 | 1.22 (1.00) |
| R-PLA | 565 | 114 | 47.7 | 1.35 (1.00) |
| L-PDA | 38 | 80.6 | 35.8 | 1.31 (1.00) |
| L-PLA | 54 | 34.2 | 16.1 | 1.21 (0.98) |
| Other | 73 | 65.1 | 29.6 | 1.25 (1.00) |

"Other" by the side it touches:
- 50 components on the LAD (D3/D4) and 20 on the LCx (OM3/OM4);
- 7 single stray voxels inside the RCA (label noise; trained as RCA);
- 1 detached component.

Other counts:
- **R-PDA comes in more than one piece in 63 cases** (the protocol traces two PDAs when both are ≥ 1.8 mm).
- The ramus touches the LCx and the LAD about equally (70 / 79): it leaves at the bifurcation.
- Grid: in-plane 0.29–0.45 mm, slices 0.5 mm.

**Calibre against the grid.** The thinnest traced branches have a median lumen diameter of 1.2–1.35 mm, about two to three
voxels at 0.5 mm. Janus 0 already segments such distal vessels.
- Septals, SN, conus and RMA are small branches of the same order. This round found no measured CT diameter
  that could be checked, so their calibre is an assumption to verify on the first extended reads.
- On that assumption, for those classes **the grid is not the obstacle; the absence of any traced example is.** At
  0.5 mm they would be 2–3 voxels across. The plan therefore keeps 0.5 mm (Janus 0's spacing) and does not
  propose a finer grid.

### 2.5 L-PDA, L-PLA and SN: the parent is an anatomical fact the namer can read

- **Dominance on the 620** (ImageCAS-X's definitions): right 556 (89.7 %), left 46 (7.4 %: 36 with an L-PDA, 10 with an L-PLA only), co-dominant 16 (2.6 %), none labelled 2; **38 cases have an L-PDA and 54 an L-PLA**, every attached one on the LCx. ImageCAS-X reports 91.1 % right, 5.1 % left and 3.8 %
  co-dominant on its 800.
- **SN origin:** Koşar et al. (700 patients) found the SN artery from the RCA in 79 %, the circumflex in 20 % and the LM
  in 0.4 %. A separate-ostium conus was found in 22 %, so 1 in 5 conus arteries is **not connected to the RCA in the
  mask at all**.
- D44 lists PDA, PLB and SN under the RCA, and #280's collapse sends them to the RCA always. For a left-dominant heart
  that **contradicts D25** (a left-sided PDA/PLA → LCx).

This plan trains PDA, PLB and SN as **anatomical types**: a posterior descending artery is PDA whichever vessel it
leaves. The namer writes the parent (`RCA` or `LCx`) per branch. The lead's choice (§10, Q1) is then a lookup at naming
and collapse time, not a retraining.

## 3. Data and the partial-label strategy

### 3.1 Data

- **Stage A** (now, no pool read needed): ImageCAS-X **620** (D45), labels converted to the 13 types with label codes
  (§3.2).
  - "Other" goes to DIAG or OM by the side it touches (50 and 20 components on the 620).
  - Its 7 stray voxels inside the RCA become RCA. A detached component becomes the marginal code {DIAG, OM}.
  - IM → RAMUS; R-/L-PDA → PDA; R-/L-PLA → PLB.
  - Validation fold = the **locked 100**, kept only for nnU-Net's monitoring. The **final checkpoint is used**, and no
    checkpoint is selected on it (as Janus 0 did with val 80).
- **Stage B** (when reads exist, §6): Stage A's model fine-tuned on ImageCAS-X 620 (replay) plus pool reads:
  - 4-class reads, with parents as marginals;
  - extended reads (#280), with child classes exact and parents as marginals unless the read is flagged complete.

  Stage B obeys every pool guard of the 1-L track:
  - D27 (seal), D35 and the reserve are refused by the #116 guard;
  - D40 handles overlaps, as amended in Q3;
  - the 74 spacing-suspect volumes are left out.

### 3.2 Partial labels: marginal codes, not ignore

The network has 14 output channels (background plus the 13 types). A training label voxel holds either a type (exact)
or a **code**: a set of types that the voxel belongs to without saying which. The loss for a coded voxel is the
**marginal**:
- cross-entropy: −log Σ_{k∈S} p_k;
- Dice: on the summed channel group.

Shi et al. (2021) introduced this for partially labelled multi-organ CT. In their partially labelled setting it was the
term that carried the gain (their abstract: the exclusion loss alone added little on kidney and pancreas).

| Code | Set S | Where it is used |
|---|---|---|
| `BG*` | {bg, SEPT, SN, CONUS, RMA} | every non-tree voxel of an ImageCAS-X case |
| `LAD*` | {LAD, DIAG, SEPT} | the LAD of a 4-class pool read, or of an extended read not flagged complete |
| `LCX*` | {LCx, OM, RAMUS, PDA, PLB, SN} | the LCx of such a read (D25: a left-sided PDA/PLA and the ramus are LCx) |
| `RCA*` | {RCA, SN, CONUS, RMA, PDA, PLB} | the RCA of such a read |
| `DOM*` | {DIAG, OM} | an "Other" component whose side is ambiguous |

Why not nnU-Net's ignore label?
- Ignore removes a voxel from the loss. The untraced septals cannot be located, so they cannot be ignored without
  ignoring all background.
- A marginal keeps the voxel's information: it is *not* LAD, LCx, RCA, DIAG, OM, RAMUS, PDA or PLB. That keeps the
  false-positive pressure Janus 0 learned (A15, FP 0.36 per case).
- Ignore stays where D40 puts it: two **unrelated** classes claiming one voxel.

**Why the dormant types never fire on ImageCAS-X alone.** SEPT, SN, CONUS and RMA have no positive voxel anywhere in
Stage A. The marginal lets their probability sit inside `BG*` without penalty, but nothing pushes it up. Under softmax
plus the background Dice term the channels stay near zero.

This is the background-shift problem of class-incremental segmentation, solved the same way (MiB: Cermelli et al.
2020, which models the background as "background or a class not yet labelled"). **Stage A therefore ships with the
dormant types empty**, and says so (§5.4).

### 3.3 Staged class addition

| Stage | Types trained | Trigger |
|---|---|---|
| A | LM, LAD, LCx, RCA, DIAG, OM, RAMUS, PDA, PLB (exact); SEPT, SN, CONUS, RMA dormant | now |
| B1 | + any dormant type with ≥ k* pool patients holding a positive extended read of it, from ≥ 3 sources | per type, §6 |
| B2 | 4-class pool reads as marginals, to adapt the vessels to the pool | the 1-L track's A39 conditions |

## 4. Architecture and recipe

### 4.1 Network

- Janus 0's network and plans (nnU-Net v2 ResEnc, `nnUNetResEncUNetPlans_60G_iso05`):
  - 0.5 mm isotropic, patch 256³, batch 2;
  - nnU-Net's own CT window;
  - **mirroring off** (left/right swaps would teach that an LAD can be an RCA, as in icx14/icx4).
- **14 output channels.** Dataset 7xx is declared with the 13 types plus the five codes as label values (values 14–18),
  so nnU-Net's resampling and deep-supervision downsampling carry the codes. The trainer maps codes to sets in the loss.

### 4.2 Warm start: Janus 0, not 1-L

- 1-L does not exist yet. D45 lets 1-L warm-start from Janus 0 without leakage because neither trains on the locked
  100; the same holds for 1-F.
- Re-warming from 1-L later would make 1-F wait on another track's verdict and confound its comparison. If 1-L is
  adopted before Stage B, Stage B's vessel adaptation (B2) is the place to borrow its pool knowledge.

### 4.3 Head initialisation

Every type channel's final 1×1×1 convolution (and each deep-supervision head) is copied from its parent's Janus 0
channel:

| Type | Parent channel |
|---|---|
| DIAG, SEPT | LAD |
| OM, RAMUS | LCx |
| PDA, PLB, SN, CONUS, RMA | RCA |

- The bias is set so that the parent and its new children split the parent's probability equally (bias − log(1 + n)).
- At step 0 the model is Janus 0 with each vessel shared among its types. Branch types start from "this is vessel" and
  only have to learn "which one". This is MiB's classifier initialisation, applied to children instead of the
  background.

### 4.4 Schedule

- **500 epochs, poly LR from 1e-2**, final checkpoint. Janus 0 ran at about 192 s/epoch on Fir; 500 epochs is about
  27 GPU-h, two chained 23:50 jobs.
- Rationale:
  - the branch types must leave their parents, which icx14 shows is slow from scratch;
  - the 250-epoch fine-tune of A36 only adapts existing classes.
- Seeds: one for Stage A. Its decision is a model decision, not a recipe claim (A22's distinction).
  [[Bridge - With A1 scoring the sealed test detects about 0.012 tF1, but seed noise doubles every training comparison]]
  bounds run-to-run SD at 0.012, below the n = 100 case noise.

### 4.5 Stage 2: the namer (CPU, deterministic, about 1 s per case)

1. Components of each predicted type.
2. Attach each component to the parent it touches most.
   - Branches not attached to any parent: CONUS with its own ostium; SN from the LM.
   - Each is kept with parent `aorta` or `LM` and named by type only.
3. Origin = geodesic distance along the parent from the parent's proximal end (`census.py`'s rule).
4. Order DIAG, SEPT and OM by origin:
   - first → D1/S1/OM1, second → D2/S2/OM2, third → D3/S3;
   - a fourth diagonal or septal, and a third OM, go to the parent's class (D44 lists no D4, S4 or OM3; D1 territory).
5. RAMUS → Ramus. PDA and PLB keep the type and the recorded parent; the D44 name follows Q1.
6. Output: the 18-class D44 map, plus `branches.json` per case (type, ordinal, parent, origin, length).

The ordinal rule is checked on the 620's reference labels in §2.1. On predictions, its errors are the stage-1 errors it
inherits: a missed D1 makes D2 into D1. §5 scores that as naming error, not as a namer bug.

## 5. Metrics and scoring

### 5.1 Four vessels (against Janus 0)

- 1-F's 18-class map is collapsed to four **under ImageCAS-X's protocol**:
  - D1–D3, Ramus, OM1–OM2 and PDA/PLB go to their parent by D25 (left-sided by the recorded parent);
  - **SEPT, SN, CONUS and RMA go to background**, because ImageCAS-X did not trace them and counting them as LAD or RCA
    would charge 1-F false positives that Janus 0 avoided by not seeing them.
- tF1 @ 1.5 mm at A1c, with the in-job aortas, as for Janus 0. Also the territory collapse (#280's), report only.

### 5.2 Traced branch classes against ImageCAS-X (D1, D2, D3, OM1, OM2, Ramus, PDA, PLB)

Per class:
- **Detection agreement:** the share of cases where model and reference both have the class or both lack it. This is
  ImageCAS-X's own "Agreement" (Table 1), so its inter-observer value is the ceiling.
- **Naming accuracy:** for each reference branch covered by any predicted branch type over ≥ 50 % of its centreline, is
  the majority predicted D44 name its own?
- **Dice** on cases where both have the class (the Table 1 convention).
- **Branch tF1:** A1's scorer with the root at the branch's origin on its parent and the 1.5 mm gap rule (D3).

| Class | ImageCAS-X inter-observer agreement | DSC (Table 1) |
|---|---|---|
| D1 | 96.9 | 79.9 ± 28.7 |
| D2 | 89.4 | 82.9 ± 24.3 |
| OM1 | 94.4 | 74.1 ± 32.3 |
| OM2 | 87.5 | 77.7 ± 29.1 |
| Ramus (IM) | 89.4 | 80.6 ± 24.5 |
| PDA (R-PDA) | 98.8 | 82.6 ± 21.9 |
| PLB (R-PLA) | 96.2 | 83.6 ± 18.6 |
| L-PDA / L-PLA | 100 / 96.9 (n = 8–9) | 75.1 / 70.9 |
| D3 (Other) | 88.8 | 81.3 ± 17.0 |

### 5.3 Classes with no ImageCAS-X label (S1–S3, SN, Conus, RMA)

- **Not scored on ImageCAS-X**, ever: its background is wrong for them.
- They are scored only on **pool extended reads**: model against read, beside read against read, on the same metrics as
  §5.2.
  - Scored on the D35 decision patients whose two reads both use the class.
  - Before that count reaches 20, report only (Wilson 95 % half-width at n = 20, p = 0.85: ±0.16).
- Until a type is trained (§6), 1-F outputs it **empty** and the release note says "not segmented".

### 5.4 What is never scored

No sealed case, no quality-0 case, no TotalSegmentator twin, and no D27-sealed or reserved pool patient (A34).

## 6. How many reads per class

Two thresholds, set separately.

### 6.1 To train a type (activate a dormant head)

- Provisional rule: **k\* = 30 pool patients with a positive extended read of that type, from ≥ 3 sources.**
- The source floor exists because site effects are learnable and inflate within-site estimates (Glocker et al. 2019).
- k\* is not a guess to keep. Job **B** (§8) measures it on ImageCAS-X itself:
  - two traced types of dormant-like calibre, **OM** (LCx side) and **PLB** (RCA side, median lumen diameter 1.35 mm, as thin as any traced branch), are kept exact in
    only k ∈ {20, 60} cases and turned into their parent's marginal everywhere else;
  - this is exactly the regime of a dormant type fed by a few extended reads among many 4-class reads;
  - it is scored on a 60-case hold-out of the 620 (hash-drawn, salt `asclepius-j1f-r1-budget:`), never on the locked 100.
- Reading:
  - **k\* = 20** if k = 20 reaches ≥ 90 % of the full-label run's detection agreement on that hold-out;
  - **k\* = 60** if only k = 60 does;
  - otherwise "more than 60", and the type stays dormant until then.

### 6.2 To report a class

- A detection rate is reported with its Wilson interval at any n.
- A class is **named in a release** only once ≥ 30 decision patients carry two reads of it (half-width ±0.13 at p = 0.85).
- Below that, the class ships as "provisional".

## 7. Pre-registered decision on the locked 100 (one look per stage)

The comparison is Stage A against **Janus 0**: Janus 0's existing predictions of the locked 100 against 1-F
Stage A's, collapsed as in §5.1.

### V, the four vessels (A38's G2/G3/A15 wording)

- **V1:** paired-bootstrap 95 % lower bound of Δ macro tF1 (1-F − Janus 0) > −0.02, and no class's Δ point estimate
  < −0.03.
- **V2:** no class's centreline recall falls by more than 0.02.
- **V3:** FP components ≤ 1 per case (A15).
- **Resolution:** at n = 100 a retrained network's paired SD is about 0.07 macro (Bridge's MDE table), so the lower
  bound sits about 0.014 under the point estimate. V1 in effect asks for a point estimate ≥ about −0.006.

### B, the traced branch classes (per class, D1, D2, OM1, OM2, Ramus, PDA, PLB)

- **B1:** detection agreement ≥ the inter-observer agreement − 0.10.
- **B2:** mean Dice on co-present cases ≥ the inter-observer DSC − 0.15.
- **B3:** naming accuracy ≥ 0.85.

D3, L-PDA and L-PLA have too few locked-100 cases. They are reported, not gated.

### Outcomes (fixed now)

| V | B for a class | 1-F ships |
|---|---|---|
| pass | pass | 1-F Stage A's own output for that class |
| pass | fail | that class merged into its parent (territory), named in the release as not segmented |
| fail | pass | the **composite**: Janus 0's four-vessel map, with voxels inside Janus 0's tree relabelled to 1-F's branch class where 1-F says so. The four-vessel collapse is then Janus 0's exactly, so V is met by construction; B is re-scored on the composite (same look family, pre-registered here) |
| fail | fail | nothing ships; §9 |

- Every read model takes the next Janus number in the order it is read (D34). Janus 1-F is a track name.
- Stage B decisions use D35 (pool) with the same V/B forms and the val-80 forgetting guard (A38 G2) on the locked 100.
  Their exact thresholds are next round's work, once Stage A's spread exists.

## 8. Fir jobs (the lead runs them; account `def-aso22`, 1 × H100 80 GB `h100:1`, 12 cores, 280 G, as icx4)

**Nothing below runs until the role:swe issue in §11 has merged.** The launcher refuses otherwise. Inputs already on
Fir from Janus 0:
- `$SCRATCH/asclepius/cases` (`fetch_cases.py`);
- ImageCAS-X labels in `$SCRATCH/icx4/icx`;
- Janus 0's checkpoint, predictions and aortas under `$SCRATCH/icx4`.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius && git -C repo pull --ff-only
test -d repo/trillium/janus1f || { echo "janus1f not merged: stop"; exit 1; }
mkdir -p experiments && rm -rf experiments/janus1f && cp -r repo/trillium/janus1f experiments/janus1f && cd experiments/janus1f
JANUS0=$SCRATCH/icx4/nnunet_results/Dataset715_ICX4/nnUNetTrainerICX4__nnUNetResEncUNetPlans_60G_iso05__3d_fullres/fold_0/checkpoint_final.pth
[ -f $JANUS0 ] || JANUS0=$(ls ~/projects/def-aso22/$USER/icx4/checkpoint_final.pth $HOME/icx4-keep/checkpoint_final.pth 2>/dev/null | head -1)

# Job A: Stage A, 500 epochs warm from Janus 0 (~27 GPU-h, CHAIN=2), then predict + aortas-reuse on the locked 100
ICX4_CLUSTER=fir ARM=A EPOCHS=500 CHAIN=2 INIT=$JANUS0 ICX=$SCRATCH/icx4/icx CASES=$SCRATCH/asclepius/cases \
  J1F_WORK=$SCRATCH/j1f_A ./janus1f
# Job B: label-budget curve, 200 epochs each, warm from Janus 0, 60-case hold-out of the 620 (~11 GPU-h each)
for K in 20 60 all; do
  ICX4_CLUSTER=fir ARM=B BUDGET=$K BUDGET_TYPES=OM,PLB HOLDOUT=60 EPOCHS=200 CHAIN=1 INIT=$JANUS0 \
    ICX=$SCRATCH/icx4/icx CASES=$SCRATCH/asclepius/cases J1F_WORK=$SCRATCH/j1f_B$K ./janus1f
done
grep SBATCH $SCRATCH/j1f_A/job.sh     # --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=280G --time=23:50:00
./janus1f status $SCRATCH/j1f_A       # after ~2 h: s/epoch, expect ~190-200 (Janus 0: 192)
```

**Check each launcher printout before leaving it:**
- `split: train 620, locked 100, sealed 0, quality-0 0` and the D45 hash line;
- `types: 13 + codes BG*, LAD*, LCX*, RCA*, DOM*`;
- `init: Janus 0, heads copied from parents (DIAG,SEPT←LAD; OM,RAMUS←LCx; PDA,PLB,SN,CONUS,RMA←RCA)`;
- `plans = Dataset715`;
- for B: `budget OM,PLB exact in K of 560 training cases; hold-out 60 (salt asclepius-j1f-r1-budget:)`.

**When each is `DONE`:** `./janus1f collect <work>` writes `results/`:
- for A: §7's V and B tables on the locked 100, with Janus 0's existing predictions paired, the namer's
  `branches.json` summary, and per-type predicted-volume counts for the dormant types (all should be 0);
- for B: OM and PLB detection agreement and Dice on the hold-out.

**Send back on #303:** the four `results/` folders (case ids and numbers only; no image leaves Fir).

| Job | GPU-h | Waits on |
|---|---|---|
| A | ≈ 27 + ≈ 1 (predict locked 100) | the swe issue |
| B (×3) | ≈ 3 × 11 = 33 (+ ≈ 0.5 predict) | the swe issue; runs beside A |
| **Total to the Stage A decision and k\*** | **≈ 61** | |

Stage B is costed when reads exist: a 250-epoch fine-tune is about 13.5 GPU-h per run.

## 9. What would change the plan

| Evidence | Change |
|---|---|
| A's dormant channels are not empty on the locked 100 (> 0 predicted voxels in > 5 cases) | Marginal leakage: add Shi's exclusion term or hard-zero the dormant logits until B1 |
| A passes V but a traced type fails B1/B2 by more than 0.10 | That type is learned poorly as a type. Compare a namer-only variant for it (Janus 0 tree + rules; Bridge's namer extended) before Stage B |
| A fails V by more than 0.03 macro | Warm-start splitting hurts the vessels. Ship the composite; next round tests a two-network design (frozen 1-L/Janus 0 vessels + a branch-type network on the vessel mask as a second input channel) |
| B's k = 20 run reaches the full run on OM and PLB | k\* = 20; the dormant types activate sooner |
| B's k = 60 run does not | Dormant types need > 60 reads each. Tell the lead what that costs in reads (D44's optional classes may never reach it) and propose a targeted extended-read campaign as the lead's call |
| The lead answers Q1 with "PDA and PLB are RCA only" | No retraining: the namer sends LCx-origin PDA/PLB to LCx (D25), and the D44 PDA/PLB classes mean right-sided only |
| Pool extended reads show annotators leave septals in the LAD | Extended reads are marginal for the LAD (`LAD*`) until the completeness flag (Q2) exists |

## 10. Questions for the lead

1. **L-PDA / L-PLA (and SN, conus).**
   - Bridge recommends **(a) anatomical PDA and PLB, with the parent recorded**: a PDA is a PDA whichever artery it
     comes from. This is SCCT's convention, which keeps L-PDA as a named segment (Leipsic et al. 2014, as used by
     ImageCAS-X), and ImageCAS-X's own dominance definition. The 4-class collapse then sends a left-sided PDA/PLB to the
     LCx (D25), which **changes #280's "always RCA" default** for left-dominant hearts.
   - **(b) RCA-only PDA/PLB:** L-PDA/L-PLA collapse to LCx and have no D44 name.
   - The same choice applies to SN (from the LCx in about 20 %).
   - The network trains the same either way. Only the namer's lookup and #280's collapse differ.
2. **A completeness flag in SegQueue14 (#280 follow-up, no D-number):** per read and per parent group ("I moved every
   septal / diagonal / RCA branch I could see"). Without it, an extended read's parent voxels can only be marginals,
   and absent classes carry no negative information.
3. **D40 for child-in-parent overlaps.** D44 extended classes start empty and the annotator moves a branch out of its
   parent. A branch painted but not erased from its parent is a child-parent overlap, which D40 would turn into ignore.
   Bridge proposes that **an overlap between a class and its own parent takes the child**, while unrelated overlaps
   stay ignore (D40). This amends D40 for extended reads, so it is the lead's.
4. **Septals, SN, conus and RMA may never reach k\*.** They are not in TotalSegmentator's seed in a form annotators
   are asked to split, and they are optional (D44). Does the lead want a minimum, for example a small set of D35 and
   training patients read with all branch groups complete, or are they "provisional" until reads accumulate?

## 11. role:swe issue (one, opened on the judge's ruling to avoid five duplicates)

"Janus 1-F Stage A launcher (`trillium/janus1f`)":
- **(a) Conversion:** ImageCAS-X 14 → 13 types + codes (§3.2); "Other" side by contact (`experiments/Bridge/j1f_r1/census.py`'s
  rule); D45 split from `split620.py`; refuses sealed, quality-0 and locked-100 cases as training.
- **(b) Trainer:** `nnUNetTrainerJ1F`, with marginal CE + marginal Dice over codes, head initialisation from parents
  (§4.3), mirroring off, icx4's chained-job logic.
- **(c) Job B:** budget and hold-out options.
- **(d) Namer:** §4.5, plus `branches.json`.
- **(e) Scorer:** §5.1–5.2 (branch tF1 rooted at the origin), §7's paired V/B tables against Janus 0's existing
  predictions.
- **(f) Tests:** a `--dry-run` of §8's commands; a synthetic tree on which the namer orders three diagonals correctly;
  and a marginal-loss unit test (a coded voxel's loss equals −log of the summed probabilities).

## 12. Risks

| Risk | Response |
|---|---|
| Marginal codes let a type absorb background near the tree | `BG*` excludes every traced type, so DIAG/OM/PDA/PLB keep full background pressure; only dormant types are marginal; §9's leakage check |
| The ordinal rule fails on predictions with a missed or split branch | Scored as naming accuracy (B3); split components of one type that touch the parent once are merged before ordering |
| The locked 100 has few D3, L-PDA, L-PLA | Reported, not gated |
| Head initialisation makes children copy the parent and never separate | The warm start already gives non-zero gradient to every child on its own labelled voxels; if a type is still 0 at epoch 100 (`status` prints per-type pseudo-Dice), the PM is told |
| Two tracks warm from Janus 0 diverge in vessel quality | V is against Janus 0 for both tracks; the composite caps 1-F's vessel risk at Janus 0 |

## 13. External evidence (checked 2026-11-11)

| Claim | Source | Used for |
|---|---|---|
| ImageCAS-X's protocol: septal perforators, acute marginals and nodal arteries not traced; branches < 1 mm distal not traced; "Other" only when ≥ 1.8 mm or as large as D1/D2; direction and course, not size, decides side branch vs continuation; class indices | Bransby et al., *ImageCAS-X*, arXiv 2608.30404, Suppl. B and Suppl. Table 4 | §2.3, §3 |
| Per-segment inter-observer agreement and DSC (160 test cases, second analyst blinded) | same, Table 1 | §5.2 gates |
| Dominance 91.1 % right, 5.1 % left, 3.8 % co-dominant; definitions | same, "Coronary Dominance" | §2.5 |
| ImageCAS-X benchmarks only binary lumen (Table 2: nnU-Net 89.8 DSC, inter-observer 92.8); no published per-branch model baseline | same, Table 2 | 1-F's branch numbers have no external comparator; the ceiling is Table 1 |
| SN artery from the RCA in 79 %, circumflex 20 %, LM 0.4 %; conus with a separate ostium 22 %; ramus 31 % (700 patients, 64-slice CTA) | Koşar et al., *Diagn Interv Radiol* 15:275 (2009), doi 10.4261/1305-3825.DIR.2550-09.1, Table 2 | §2.4–2.5, the SN/conus parent and the namer's unattached branches |
| Marginal loss for partially labelled multi-organ CT: an unlabelled class merged into background is a marginal probability | Shi, Xiao, Chen, Zhou, *Med Image Anal* (2021), arXiv 2007.03868 | §3.2 |
| Background shift in class-incremental segmentation; classifier initialisation for new classes | Cermelli et al., CVPR 2020, arXiv 2002.00718 | §3.2, §4.3 |
| One network over partially labelled datasets with conflicting class definitions (nnU-Net based, DKFZ) | Ulrich et al., *MultiTalent*, arXiv 2303.14444 | The alternative not chosen (sigmoid per class); §3.2 keeps softmax so the four-vessel collapse stays exclusive |
| Partial losses (loss only on annotated voxels) in nnU-Net | Gotkowski et al., arXiv 2403.12834 | Why ignore is not used for untraced classes (§3.2) |
| Graph-based anatomical labelling of coronary branches from a segmented tree (511 CCTA, mean F1 0.955) | Yang et al., *CPR-GCN*, CVPR 2020, arXiv 2003.08560 | A learned namer is viable; this plan needs only the ordinal part |
| Tree-structured LSTM labelling of coronary branches from position and direction (436 CCTA) | Wu et al., *IJCARS* 14:271–280 (2019), doi 10.1007/s11548-018-1884-6 | Same |
| SCCT 18-segment model, used by ImageCAS-X | Leipsic et al., *J Cardiovasc Comput Tomogr* 8:342–358 (2014), doi 10.1016/j.jcct.2014.07.003 (cited as ImageCAS-X's ref. 1) | Q1 |
| Site effects are learnable and inflate within-site estimates | Glocker et al., arXiv 1910.04597 (2019) | §6.1's source floor |
| nnU-Net | Isensee et al., *Nat Methods* 18:203–211 (2021), doi 10.1038/s41592-020-01008-z | §4 |

## 14. Cost

- **CPU here:** done (split, census of 620, ordinals, Other, dominance, icx14 logs).
- **Fir:** ≈ 61 GPU-h to the Stage A decision and k\*.
- **SWE:** one issue (§11).
- **Reads:** none needed for Stage A. Stage B needs the extended reads D44 already allows.
