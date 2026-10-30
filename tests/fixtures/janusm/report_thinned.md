# Janus-M table: Synthetic__thinned

- **Phase:** phase unrecorded; every thickness is phase-uncertain
- **Spacing:** 0.70 × 0.70 × 0.70 mm
- **Endocardial 10–90 % edge:** 1.20 mm
- **Half-maximum offsets:** endocardium 0.10 mm, epicardium -0.05 mm (+ = the region bounded by the border extends beyond the image half-maximum (JA44))
- **AHA orientation:** pass; septal arc 115.7°
- **Territory source:** ImageCAS-X reference tree
- **Layers per segment:** 0 in thirds, 17 in halves
- **Versions:** harness 1.0.0, geometry 1.0.0, features 1.0.0, report 1.0.0, guard 2
- **Reference config sha256:** 38e7fe562a779603bd5e7fc87bac9ff8e6323791cc29cb73356ec18725a3b6d2

## Table A: segments (numbers, never flags)

| Segment | Layers | Thickness mm | Rel. thickness | Rel. subendo HU | Core fat mm³ | Rest TPR z | Territory (share) | AHA default |
|---|---|---|---|---|---|---|---|---|
| 1 basal anterior | halves | 4.53 (p0) | 0.60 | 1.00 (p43) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD |
| 2 basal anteroseptal | halves | 7.50 (p53) | 0.99 | 1.00 (p47) | 0.0 | not shown: rest TPR gate fail | RCA (0.53) shared | LAD |
| 3 basal inferoseptal | halves | 7.55 (p54) | 1.00 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | RCA (1.00) | RCA |
| 4 basal inferior | halves | 7.57 (p54) | 1.00 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA |
| 5 basal inferolateral | halves | 7.52 (p53) | 0.99 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LCx (1.00) | LCx |
| 6 basal anterolateral | halves | 7.57 (p48) | 1.00 | 1.00 (p51) | 0.0 | not shown: rest TPR gate fail | LAD (0.54) shared | LCx |
| 7 mid anterior | halves | 4.62 (p0) | 0.61 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD |
| 8 mid anteroseptal | halves | 7.52 (p47) | 0.99 | 1.00 (p46) | 0.0 | not shown: rest TPR gate fail | RCA (0.53) shared | LAD |
| 9 mid inferoseptal | halves | 7.69 (p53) | 1.02 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | RCA (1.00) | RCA |
| 10 mid inferior | halves | 7.70 (p54) | 1.02 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA |
| 11 mid inferolateral | halves | 7.60 (p54) | 1.01 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LCx (1.00) | LCx |
| 12 mid anterolateral | halves | 7.70 (p52) | 1.02 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | LAD (0.54) shared | LCx |
| 13 apical anterior | halves | 4.48 (p0) | 0.59 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD |
| 14 apical septal | halves | 7.56 (p51) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | RCA (0.85) | LAD |
| 15 apical inferior | halves | 7.57 (p56) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA |
| 16 apical lateral | halves | 7.55 (p52) | 1.00 | 1.00 (p45) | 0.0 | not shown: rest TPR gate fail | LCx (0.81) | LCx |
| 17 apex | halves | 7.57 (p99) | — | — | 0.0 | not shown: rest TPR gate fail | RCA (0.37) shared | LAD |

## Table B: territories

| Territory | Reader grade (CAD-RADS 2.0) | Mass g (share) | AHA default mass g | Segments | Shared segments | Thinning | Hypoattenuation | Fat | Composite | Mass distal to marked lesion (unvalidated) | Concordance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LAD | 3 | 9.8 (0.274) | 14.3 | 1, 7, 13 | 6, 12 | FLAG (1.85 mm) | 0.00 rel. | 0.0 mm³ | no | — | Isolated measurements outside range |
| LCx | 0 | 12.9 (0.358) | 10.8 | 5, 11, 16 | 4, 10, 15 | -0.07 mm | 0.00 rel. | 0.0 mm³ | no | — | No geometric sign in territory |
| RCA | not graded | 13.2 (0.368) | 10.8 | 3, 9, 14 | 2, 8 | 0.02 mm | 0.00 rel. | 0.0 mm³ | no | — | No geometric sign in territory |

---

Research output, not validated: no scar or perfusion reference.  
Thinning: a territory is flagged only when its wall is thinner than the patient's other walls by more than this population's normal variation allows. In simulation, a territory thinned by ≥ 15 % is flagged in ≥ 80 % of cases. Thinner changes are usually not flagged. This is not a sensitivity for scar, which this table cannot measure.  
Hypoattenuation: a territory is flagged only when its subendocardial attenuation is lower than the patient's other walls by more than this population's normal variation allows. In simulation, a territory with a relative subendocardial deficit of ≥ 15 % is flagged in ≥ 80 % of cases. Smaller changes are usually not flagged. This is not a sensitivity for scar, which this table cannot measure.  
Population: this population, phase-uncertain.
