# Janus-M border read protocol: protocol v1 (JA21, JA46)

**Status:** **border protocol v1** (`border_protocol: 1`), final. It replaces the
Round 1 placeholders. Sources: `vault/JanusM/Judgements/Round 1.md` (JA1, JA6, JA7,
JA12); Round 2 (JA21, adopting Hotel v2 §5.4); Round 3 on `jm/rest-ccta` (JA44,
JA46, JA47, and the S5 change list, which supersedes Hotel v3 §5.2 and India v3 §7).
The reading text is Hotel v3 §5.1, as JA46 amends it.
Code: `src/janusm_reads/`, `server/girder_janusm/`, `slicer/JanusMRead/`. Issues: #141,
#195.

This protocol is for reading the **Janus-M reference borders** on rest CCTA. It is
not the coronary (SegQueue14) protocol: other labels, another queue, other groups.
A SegQueue14 module cannot open a Janus-M case, and a Janus-M read is never stored
with coronary reads.

**Two version numbers.** The *wire* protocol (`janusm-read` 1,
`janusm_reads.PROTOCOL_VERSION`) is how a client talks to the queue. The *border*
protocol (`janusm_reads.BORDER_PROTOCOL`, 1) is this text: the rules a read is drawn
and checked under. Every read record, check report and export carries
`border_protocol`, so a later change to the text is visible in the data even if the
wire protocol stays the same.

---

## 1. What is read

| | |
|---|---|
| Cases | the frozen Janus-M **decision set (40)** and **seal (60)**, ImageCAS-X *train* cases only (JA5, JA6). Nothing else is ever served. |
| Reads per case | **two, independent** (JA7), plus a **third read from blank** on 5 seeded cases of a flagged wave (§7, rule 2). |
| Starting point | a **seed** (§5) on 90 cases; **no seed** on 10 seal cases (§5.2). |
| Order | the decision set first; seal cases only after the seal is re-powered on the first 20 double-read decision cases (JA6) and an admin opens it. |
| Read form | per vessel, the CAD-RADS 2.0 grade of the worst lesion, and an optional lesion point (§4.4). |

Thirds, AHA segments and territories have **no read of their own**: code computes
them from the borders (JA2–JA4).

## 2. Labels (JA1, as protocol v1 states them)

Only these four classes are drawn; everything else is 0.

| Value | Class | Includes | Excludes |
|---|---|---|---|
| 0 | background | everything else, including RA, aorta, pulmonary artery, pericardium, fat, and the mitral gap where it is not myocardium | |
| 1 | **LV myocardium** | the compact LV wall, **septum included** | papillary muscles, trabeculae, RV free wall; **myocardium above the mitral annulus is not labelled** |
| 2 | **LV blood pool** | the LV cavity **with papillary muscles and trabeculae**; ends at the **mitral annulus plane** and the **aortic valve plane** | the LV outflow above the aortic valve plane |
| 3 | **RV blood pool** | the RV cavity from the **tricuspid annulus to the pulmonary valve**, trabeculae included | the RV wall; the pulmonary artery beyond the pulmonary valve |
| 4 | **LA blood pool** | the LA cavity, to the mitral annulus | the **LA appendage** and the **pulmonary veins beyond their ostia** |

The rules a reader follows:

1. **Papillary muscles and trabeculae are LV blood pool (2).** The endocardium is the
   compact-wall surface. Where trabeculae merge with the compact wall, the border
   goes at the **outer edge of the blood-filled recesses**.
2. **Basal limits.** The LV pool ends at the mitral annulus plane and the aortic
   valve plane, each a flat plane through the valve's hinge points as best seen.
   Myocardium above the mitral annulus is not labelled. The LA runs to the mitral
   annulus; the LA appendage and the pulmonary veins are excluded beyond their
   ostia. The RV pool runs from the tricuspid annulus to the pulmonary valve.
3. **The mitral gap.** Labels 2 and 4 **never share a face**: between the LV pool and
   the LA there is always a gap of background (0) or myocardium (1), and the LV pool
   reaches at most 3 mm above the mitral plane (§4.1).
4. **The septum is myocardium (1)**, so the LV and RV pools do not touch, except over
   the membranous septum (fibrous, not labelled myocardium), where they may meet over
   at most 0.5 % of the LV pool's surface (JA46 (b)).
5. The myocardium is **one shell**, not loose pieces. The LV pool has no enclosed
   holes.

`janusm_reads.labels.CONVENTIONS` carries the same text, and the reader module shows
it on each class.

## 3. The half-maximum rule (Hotel; JA21)

**A border lies halfway between the plateaus on either side of it.** A plateau is
the typical HU of a tissue away from any edge.

| Border | Between | Threshold |
|---|---|---|
| endocardial (LV) | LV blood pool and core myocardium | (LV blood + myocardium) / 2 |
| epicardial (free wall) | core myocardium and epicardial fat | (myocardium + fat) / 2 |
| septal, RV side | core myocardium and RV blood pool | (RV blood + myocardium) / 2 |

How to apply it while reading:

1. **Plateaus.** On a seeded case they are measured from the seed when the case
   opens, and shown. On a blank case the reader places a small ROI in each tissue:
   inside the LV pool, mid-wall myocardium, epicardial fat (−180 to 0 HU).
2. **The border window is the default.** For the border being drawn the module sets
   **level = (p₁ + p₂) / 2** and **width = 1.5 × |p₁ − p₂|** (Hotel v2 §5.4). A case
   opens on the endocardial border; the reader may switch borders. A fixed
   **800 / 300** window is available, but is not the default (a blank case shows it
   until its plateaus are measured).
3. Draw on the half-way transition, not on the visually "sharp" edge: partial
   volume makes the eye place a bright-blood edge outward and a fat edge inward.

**The canonical sign (JA44).** Every half-maximum offset this project reports (the
read checker, the queue's export, the anchoring report, the tables) uses one sign:
**+ = the region bounded by the border extends beyond the image half-maximum**. That
region is the LV pool for the endocardium and pool + myocardium for the epicardium
(and the septal RV side). So + means the read spills past the edge, − that it stops
short of it.

## 4. The automatic read check, and what happens to a read

Every submitted read is checked by `janusm_reads.checker.check_read` (on the server,
by `janusm-check`) before it counts as a reference read.

### 4.1 Checks at submission

| Check | Rule | Kind |
|---|---|---|
| Label values | only 0–4; all four classes present | hard |
| Half-maximum, per border | **median offset over the border ≤ 0.5 mm** (canonical sign, reported) | hard: return once (§4.2) |
| Half-maximum, per octant | octant offset > 1.0 mm | **warning only** (JA46 (c)) |
| LV pool ↔ LA pool | labels 2 and 4 never share a face | hard |
| Mitral plane | label 2 extends ≤ 3 mm above the mitral plane (JA46 (a), below) | hard |
| LV pool ↔ RV pool | contact ≤ 0.5 % of the LV pool's surface (JA46 (b)) | hard |
| LV pool holes | none enclosed (> 0.2 % of its volume) | hard |
| Myocardium connectivity | > 2 % outside the largest piece | hard; 0–2 % a warning |
| LV pool facing background | > 25 % of its surface | warning |

**The half-maximum offsets.** From the read's own labels the check measures the
plateaus (LV and RV blood ≥ 2 mm deep in their pools; myocardium ≥ 1 mm from any
other class; fat 1–4 mm outside the myocardium in −180..0 HU). Across each border it
takes the median CT value as a function of signed distance to the read's border
(bins of 0.25 mm, ±3 mm) and finds where that profile crosses the threshold. The
crossing's distance from the read's border, in the canonical sign, is the border's
offset. It is measured over the whole border, which decides, and in eight octants
about the LV pool's centre, which only warn. The epicardial check is skipped, with a
warning, where no fat plateau can be measured.

**The mitral plane (JA46 (a)).** Fitted by least squares:

1. on a seeded case, to the **seed's** 2–4 interface (or, if the seed has a mitral
   gap, to its label-2 voxels within 3 mm of label 4);
2. on a blank case, to the **read's** label-2 voxels within 3 mm of label 4 (the
   mitral gap);
3. if neither exists, to the annular hinge points.

The plane's normal points into the LA. The check measures how far the LV pool
reaches above it over the plane's own footprint (the extent of the points it was
fitted to), so the outflow tract under the aortic valve is not measured against the
mitral plane. Where no plane can be fitted, the check warns that the basal limit was
not checked.

| Setting (`CheckConfig`) | v1 value | |
|---|---|---|
| `tolerance_mm` | **0.5 mm** | whole-border median (JA21) |
| `octant_warning_mm` | 1.0 mm | warning only (JA46 (c)) |
| `max_pool_contact_share` | 0.5 % | LV–RV (JA46 (b)) |
| `mitral_gap_mm` / `max_pool_above_mitral_mm` | 3 mm / 3 mm | JA46 (a) |
| `band_mm` / `bin_mm` | 3.0 / 0.25 mm | |
| `fat_window_hu` | −180 .. 0 HU | JA11, verified |
| `fat_shell_mm` | 1–4 mm | |

### 4.2 Return once, then accept and flag

- **A passed read** is accepted.
- **First failure** of any hard or half-maximum check: the read is **returned** with
  the failing checks and, for the half-maximum check, the **profile plot** (HU
  against signed distance from the read's border, with both plateaus and the half
  level marked; the failing border named). The reader module plots it.
- **Second failure:** the read is **accepted and flagged** (`flagged: true`, with the
  reasons). A flagged read counts in every analysis, and the flag is reported.
- A read the checker cannot run on at all goes back unflagged: that is not a failed
  check.

The count is the read's `attempts`; `protocol.MAX_RETURNS` is 1.

### 4.3 What is stored with every read

Reader, seeded or blank, third read or not, seconds, attempts, the check report,
flagged and its reasons, the read form, and `border_protocol: 1`.

### 4.4 The read form (JA46 (d))

On every case (seal and decision), the reader gives, for each of **LM, LAD, LCx and
RCA** (with their branches), the **CAD-RADS 2.0** grade of its worst lesion: **0, 1,
2, 3, 4A, 4B, 5 or N** (non-diagnostic). Optionally they mark the worst lesion's point
(world mm, RAS) on any vessel graded 1–5. A read is not submitted until every vessel
is graded. The form is stored with the read for the export, and **never shown to the
other reader** (LQ10 (a)).

## 5. Seeds and blank reads

### 5.1 Seeds

A seed is TotalSegmentator `heartchambers_highres` (licence: JA9 / LQ3), mapped to
§2's values, **coarsened to 2 mm and smoothed (σ = 1 mm, confirmed)** (Golf), and
resampled to the CT grid (`janusm_reads.seeds`). It is a rough start on purpose.
Mapping: `heart_myocardium` → 1, `heart_ventricle_left` → 2, `heart_ventricle_right` →
3, `heart_atrium_left` → 4; the rest → 0. The reader sees no model output other than
the seed.

### 5.2 Blank reads

**10 of the 60 seal cases are read from blank** (JA7): both reads of each start
from no seed. Which 10 is fixed by code before any read: the 10 seal cases (of
the 60 first drawn) with the lowest `sha256("asclepius-janusm-blank-r1:" + case)`
(`janusm_reads.readset.blank_cases`). A seal grown from JA6's extension never
changes them. Seeds are still computed for blank cases, for the anchoring
report (§7); they are never served.

### 5.3 The seed job on Fir (the lead runs it; JA10)

The JA6 freeze (`configs/janusm/sealed-r1.json`, #140) is on `dev` and is
sha256-checked on every load. About 2 GPU-h (JA10). Nobody but the lead runs it.

```sh
module load StdEnv/2023 python/3.11.5
cd $SCRATCH/asclepius/repo && git fetch origin && git checkout dev && git pull --ff-only   # dev has configs/janusm/sealed-r1.json
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

- Each case's reads are by different readers. A reader never gets a case twice.
- A reader never sees the other read, the other read form, the read set (seal or
  decision), whether the case is scored, or whether theirs is a third read. A reader
  is told only whether the case has a seed.
- Readers do not discuss cases with each other while a wave is open.
- A reader's released case is never handed back to them.

## 7. Anchoring, per wave (JA21, JA47)

`janusm-export` writes a wave's accepted double reads and a manifest;
`python -m janusm_reads.anchoring <manifest.json>` gives, per border (endocardial =
surface of class 2; epicardial = surface of classes 1 + 2):

- **seed-vs-read ASSD** (each read, against the case's seed; voxel ASSD, JA39);
- **inter-read ASSD** (the two reads of a case);
- the **share of seed voxels changed** per read (voxels whose class differs, over
  voxels labelled in either);
- the **half-maximum offsets of the seeds and the reads** (canonical sign).

Each is reported for seeded and blank cases separately.

**Rule 1.** gap = mean seed-vs-read ASSD on blank-case reads − the same on
seeded-case reads. **Seeded reads cannot accept a model** if the upper 95 % bound of
(gap − mean seeded inter-read ASSD) exceeds **0.2 mm** on either border. The bound
comes from a **two-sample** bootstrap: blank and seeded cases are resampled
independently (no case has both a blank and a seeded read), 2 000 draws, fixed seed.

**Rule 2.** If more than half of a wave's seeded reads change **< 5 %** of seed
voxels, the wave is **flagged**. Then **5** of its seeded cases, drawn by salted hash
(`janusm_reads.anchoring.third_read_cases`), get a **third read from blank by a reader
who has not read them** (an admin opens them: `POST /janusm/admin/third-reads`), and
Rule 1 is evaluated on them: the third reads take the blank side and the same
cases' seeded reads the seeded side. **Third reads never enter the reference
standard**: they are exported apart and never counted as a case's reads.

`seededReadsMayAcceptModel` is false when Rule 1 fails (on the wave, or on a flagged
wave's third reads), true when both pass, and empty while a sample is missing or a
flagged wave's third reads are not all in.

## 8. Hold-outs (JA12)

Every Janus-M read step that names cases (the queue, the seed job, the anchoring
report) calls the JA12 guard (`janusm.guard.refuse`, through
`janusm_reads.holdout`) first and stops the whole step on any hit. Seal cases are
checked under the guard's `seal_scoring` purpose and decision cases under
`decision_scoring`. Reading the reference is part of scoring, and any other use of
a seal or decision case is refused. A case outside the frozen seal and decision
lists is refused before the guard is asked. If the guard cannot be imported or
loaded, the step is refused (it fails closed).

## 9. Protocol v1: what was settled, and where

Every Round 1 placeholder is settled. The values below are border protocol 1
(`border_protocol: 1` in every read record, check report and export).

| Item | Where | v1 | Source |
|---|---|---|---|
| Basal limits | §2 | mitral annulus plane and aortic valve plane; no myocardium above the annulus | Hotel v3 §5.1, JA21 |
| Mitral gap | §2, §4.1 | labels 2 and 4 never share a face; LV pool ≤ 3 mm above the fitted mitral plane | JA46 (a) |
| LA limits | §2 | to the mitral annulus; appendage and pulmonary veins excluded beyond their ostia | Hotel v3 §5.1 |
| RV extent | §2 | tricuspid annulus to pulmonary valve, trabeculae included | Hotel v3 §5.1 |
| Trabeculae | §2 | LV pool; border at the outer edge of the blood-filled recesses | Hotel v3 §5.1 |
| Window | §3 | border window: level (p₁ + p₂) / 2, width 1.5 × \|p₁ − p₂\|; 800 / 300 on request | Hotel v2 §5.4, JA21 |
| Offset sign | §3 | + = the region extends beyond the half-maximum | JA44 |
| Check tolerance | §4.1, `CheckConfig.tolerance_mm` | 0.5 mm, whole-border median | JA21 |
| Octants | §4.1, `CheckConfig.octant_warning_mm` | > 1.0 mm is a warning only | JA46 (c) |
| LV–RV contact | §4.1 | ≤ 0.5 % of the LV pool's surface | JA46 (b) |
| Failed reads | §4.2 | returned once, then accepted and flagged | Hotel v3 §5.1 |
| Read form | §4.4 | per-vessel CAD-RADS 2.0 and an optional lesion point | JA46 (d) |
| Fat shell | §4.1, `CheckConfig.fat_shell_mm` | 1–4 mm (unchanged) | Round 1 |
| Seed smoothing | §5.1, `seeds.SMOOTH_MM` | σ = 1 mm, confirmed | Hotel v3 §5.1 |
| Anchoring rules | §7 | rule 1 (two-sample bootstrap, 0.2 mm) and rule 2 (wave flag, 5 third reads) | JA47 |
| Versioning | everywhere | `border_protocol: 1`, apart from the wire `PROTOCOL_VERSION` (1) | S5 |
