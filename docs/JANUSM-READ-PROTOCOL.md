# Janus-M border read protocol (JA7)

**Status:** Round 1 protocol. Sections marked **[Round 2]** are placeholders that
Janus-M Round 2 settles (Round 1 ruling §6, item 4) before any seal case is read.
Source: `vault/JanusM/Judgements/Round 1.md`, amendments JA1, JA6, JA7, JA12.
Code: `src/janusm_reads/`. Issue: #141.

This protocol is for reading the **Janus-M reference borders** on rest CCTA. It is
not the coronary (SegQueue14) protocol: other labels, another queue, other groups.
A SegQueue14 module cannot open a Janus-M case, and a Janus-M read is never stored
with coronary reads.

---

## 1. What is read

| | |
|---|---|
| Cases | the frozen Janus-M **decision set (40)** and **seal (60)**, ImageCAS-X *train* cases only (JA5, JA6). Nothing else is ever served. |
| Reads per case | **two, independent** (JA7). |
| Starting point | a **seed** (§5) on 90 cases; **no seed** on 10 seal cases (§5.2). |
| Order | the decision set first; seal cases only after the seal is re-powered on the first 20 double-read decision cases (JA6) and an admin opens it. |

Thirds, AHA segments and territories have **no read of their own**: code computes
them from the borders (JA2–JA4).

## 2. Labels (JA1)

| Value | Class | Includes | Excludes |
|---|---|---|---|
| 0 | background | everything else, including RA, aorta, pulmonary artery, pericardium, fat | |
| 1 | **LV myocardium** | the compact LV wall, **septum included** | papillary muscles, trabeculae, RV free wall |
| 2 | **LV blood pool** | the LV cavity **with papillary muscles and trabeculae**; basal limit at the mitral and aortic valve planes | LV outflow above the aortic valve plane |
| 3 | **RV blood pool** | the RV cavity | RV wall |
| 4 | **LA blood pool** | the LA cavity, to the mitral annulus | pulmonary veins beyond the ostia **[Round 2]** |

Conventions the automatic check enforces (§4):

- every class is present;
- the LV and RV pools never touch: the septum between them is myocardium (1);
- the LV pool has no enclosed holes: papillary muscles and trabeculae are pool (2);
- the myocardium is one shell, not loose pieces.

**[Round 2] Basal limits.** The exact mitral and aortic valve planes (which slice,
how the plane is drawn through an oblique annulus, what happens at the
aorto-mitral continuity) and the apex cap. Until then: close the LV pool with a
flat plane through the hinge points of each valve as best seen.

## 3. The half-maximum rule (Hotel)

**A border lies halfway between the plateaus on either side of it.** A plateau is
the typical HU of a tissue away from any edge.

| Border | Between | Threshold |
|---|---|---|
| endocardial (LV) | LV blood pool and myocardium | (LV blood + myocardium) / 2 |
| epicardial (free wall) | myocardium and epicardial fat | (myocardium + fat) / 2 |
| septal, RV side | myocardium and RV blood pool | (RV blood + myocardium) / 2 |

How to apply it while reading:

1. Measure the plateaus once per case: the mean HU of a region well inside the LV
   pool, of the mid-wall myocardium, and of epicardial fat (inside −180 to 0 HU).
   Slicer's *Segment Statistics* or a small ROI gives them.
2. For a border, set the window **level to that border's threshold** and the width
   narrow (about 50 HU). The border is where the image turns from white to black.
3. Draw on that transition, not on the visually "sharp" edge: partial volume
   makes the eye place a bright-blood edge outward and a fat edge inward.

Trabeculae and papillary muscles sit inside the pool by convention (JA1): the
endocardial border is drawn at the compact wall, around them.

## 4. The automatic read check

Every submitted read is checked by `janusm_reads.checker.check_read`, before it
counts as a reference read. A failed read goes back to its reader with the
reasons; a passed read is accepted.

1. **Label values and conventions** (§2).
2. **Half-maximum offsets.** From the read's own labels the check measures the
   plateaus (LV blood ≥ 2 mm deep in the pool; myocardium ≥ 1 mm from any other
   class; fat 1–4 mm outside the myocardium in −180..0 HU). Across each border it
   takes the median CT value as a function of signed distance to the read's border
   (bins of 0.25 mm, ±3 mm), and finds where that profile crosses the threshold.
   The crossing's distance from the read's border is the border's **offset**:
   positive when the read is drawn inside the image border, negative when it spills
   past it.
3. The offset is measured over the whole border **and in eight sectors** (octants
   about the LV pool's centre), so a local error is caught as well as a bias.
4. A read **fails** if any border's offset, whole or in one sector, exceeds the
   tolerance.

| Setting (`CheckConfig`) | Round 1 value | |
|---|---|---|
| `tolerance_mm` | **1.0 mm** | **[Round 2]** JA8's bias guard on the model is 0.5 mm |
| `band_mm` / `bin_mm` | 3.0 / 0.25 mm | |
| `fat_window_hu` | −180 .. 0 HU | JA11, verified |
| `fat_shell_mm` | 1–4 mm | **[Round 2]** |

The epicardial check is skipped, with a warning, where no fat plateau can be
measured (too little fat in the shell).

## 5. Seeds and blank reads

### 5.1 Seeds

A seed is TotalSegmentator `heartchambers_highres` (licence: JA9 / LQ3), mapped to
§2's values, **coarsened to 2 mm and smoothed** (Golf), and resampled to the CT
grid (`janusm_reads.seeds`). It is a rough start on purpose. Mapping:
`heart_myocardium` → 1, `heart_ventricle_left` → 2, `heart_ventricle_right` → 3,
`heart_atrium_left` → 4; the rest → 0. **[Round 2]** the smoothing (σ = 1 mm on
the 2 mm grid).

### 5.2 Blank reads

**10 of the 60 seal cases are read from blank** (JA7): both reads of each start
from no seed. Which 10 is fixed by code before any read: the 10 seal cases (of
the 60 first drawn) with the lowest `sha256("asclepius-janusm-blank-r1:" + case)`
(`janusm_reads.readset.blank_cases`). A seal grown from JA6's extension never
changes them. Seeds are still computed for blank cases, for the anchoring
report (§7); they are never served.

### 5.3 The seed job on Fir (the lead runs it; JA10)

Waits on the JA6 freeze (`configs/janusm/sealed-r1.json`, #140) being merged.
About 2 GPU-h (JA10). Nobody but the lead runs it.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git pull --ff-only      # a dev commit that has configs/janusm/sealed-r1.json
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg     # Job S's folder, where the licence is set
# only if TotalSegmentator asks for a licence:
# totalseg_set_license -l "<the project's TotalSegmentator licence key>"   # typed by the lead; never committed or posted
mkdir -p $SCRATCH/janusm/hc $SCRATCH/janusm/seeds

# 1. Check first (no GPU, writes nothing). Expect: cases 100, decision 40, seal 60,
#    blank_cases 10, holdouts 0. Anything else, or a REFUSED line: stop and send it back.
python tools/janusm/make_seeds.py --freeze configs/janusm/sealed-r1.json \
    --layout $SCRATCH/icx4/layout.json --totalseg-dir $SCRATCH/janusm/hc \
    --out $SCRATCH/janusm/seeds --dry-run

# 2. The job.
cat > $SCRATCH/janusm/seeds.sh <<'EOF'
#!/bin/bash
#SBATCH --job-name=janusm-seeds --account=def-aso22 --gpus-per-node=h100:1 --cpus-per-task=12 --mem=64G --time=03:00:00
module load StdEnv/2023 python/3.11.5
source $HOME/icx4-tseg-venv/bin/activate
export TOTALSEG_HOME_DIR=$SCRATCH/seedcal/totalseg
cd $SCRATCH/asclepius/repo
python tools/janusm/make_seeds.py --freeze configs/janusm/sealed-r1.json \
    --layout $SCRATCH/icx4/layout.json --totalseg-dir $SCRATCH/janusm/hc \
    --out $SCRATCH/janusm/seeds --run-totalseg
EOF
sbatch $SCRATCH/janusm/seeds.sh
```

Send back **only the one JSON line** the job prints (counts and failed case ids).
The seeds stay on Fir until the queue is deployed; uploading them is part of the
queue's deploy notes.

## 6. Independence

- Each case's two reads are by two different readers. A reader never gets both.
- A reader never sees the other read, the read set (seal or decision), or whether
  the case is scored. A reader is told only whether the case has a seed.
- Readers do not discuss cases with each other while a wave is open.
- A reader's released case is never handed back to them.

## 7. The anchoring report, per wave

`python -m janusm_reads.anchoring <manifest.json>` gives, per border (endocardial =
surface of class 2; epicardial = surface of classes 1 + 2):

- **seed-vs-read ASSD** (each read, against the case's seed);
- **inter-read ASSD** (the two reads of a case);
- the **share of voxels changed** from the seed (voxels whose class differs, over
  voxels labelled in either).

Each is reported for seeded and blank cases separately. JA7: if blank reads differ
from seeded reads by more than the inter-read difference, seeded reads cannot
accept a model. The report reads this as

    anchored  if  mean seed-vs-read ASSD (blank) − mean seed-vs-read ASSD (seeded)
                  >  mean inter-read ASSD (seeded)

per border, and sets `seededReadsMayAcceptModel` to false when either border is
anchored. **[Round 2] Anchoring thresholds**: this reading of JA7 and its threshold.

## 8. Hold-outs (JA12)

Every Janus-M step that names cases (the queue, the seed job, the anchoring
report) calls `janusm_reads.holdout.refuse` first and stops the whole step on any
hit. Until the JA12 guard (#138) merges, that is an interim check: the A14 sealed
100 and the ImageCAS-X test split (`trillium/icx4/sealed_test.json`), anything
outside the ImageCAS-X train list (so val 80 and test 160), and the coronary pool
seal by patient (`segtrain.pool_seal`). When JA12 merges, the adapter calls it.

## 9. Placeholders for Round 2

| Item | Where | Round 1 value |
|---|---|---|
| Basal limits: mitral and aortic valve planes, apex cap | §2 | flat plane through the valve hinge points |
| LA limit at the pulmonary veins | §2 | ostia |
| Check tolerance | §4, `CheckConfig.tolerance_mm` | 1.0 mm |
| Fat shell | §4, `CheckConfig.fat_shell_mm` | 1–4 mm |
| Seed smoothing | §5.1, `seeds.SMOOTH_MM` | 1 mm |
| Anchoring rule and threshold | §7 | gap > mean seeded inter-read ASSD |
