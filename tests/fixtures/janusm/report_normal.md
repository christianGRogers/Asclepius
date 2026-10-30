# Janus-M table: Synthetic__normal

- **Phase:** phase unrecorded; every thickness is phase-uncertain
- **Spacing:** 0.70 × 0.70 × 0.70 mm
- **Endocardial 10–90 % edge:** 1.20 mm
- **Half-maximum offsets:** endocardium 0.10 mm, epicardium -0.05 mm (+ = the region bounded by the border extends beyond the image half-maximum (JA44))
- **AHA orientation:** pass; septal arc 115.7°
- **Territory source:** ImageCAS-X reference tree
- **Territory map:** patient-specific
- **Shared segments:** majority share < 0.6
- **Layers per segment:** 0 in thirds, 17 in halves
- **Versions:** harness 1.2.0, geometry 1.0.0, features 1.1.0, report 1.1.0, guard 2
- **Reference config sha256:** 0152311983ef2b5a72fa2daede2acc1967f2102202b0ef8d3c81f573dbce9c35

## Table A: segments (numbers, never flags)

| Segment | Layers | Thickness mm | Rel. thickness | Rel. subendo HU | Core fat mm³ | Rest TPR z | Territory (share) | AHA default | Septal arc: thickness mm; rel. subendo HU |
|---|---|---|---|---|---|---|---|---|---|
| 1 basal anterior | halves | 7.53 (p55) | 0.99 | 1.00 (p43) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD | — |
| 2 basal anteroseptal | halves | 7.53 (p54) | 0.99 | 1.00 (p47) | 0.0 | not shown: rest TPR gate fail | RCA (0.53) shared | LAD | 7.52 (p52); 1.00 (p50) |
| 3 basal inferoseptal | halves | 7.55 (p54) | 1.00 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | RCA (1.00) | RCA | 7.60 (p52); 1.00 (p48) |
| 4 basal inferior | halves | 7.57 (p54) | 1.00 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA | — |
| 5 basal inferolateral | halves | 7.52 (p53) | 0.99 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LCx (1.00) | LCx | — |
| 6 basal anterolateral | halves | 7.69 (p54) | 1.01 | 1.00 (p51) | 0.0 | not shown: rest TPR gate fail | LAD (0.54) shared | LCx | — |
| 7 mid anterior | halves | 7.67 (p50) | 1.01 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD | — |
| 8 mid anteroseptal | halves | 7.69 (p54) | 1.01 | 1.00 (p46) | 0.0 | not shown: rest TPR gate fail | RCA (0.53) shared | LAD | 7.69 (p49); 1.00 (p53) |
| 9 mid inferoseptal | halves | 7.69 (p53) | 1.02 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | RCA (1.00) | RCA | 7.70 (p48); 1.00 (p49) |
| 10 mid inferior | halves | 7.70 (p54) | 1.02 | 1.00 (p52) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA | — |
| 11 mid inferolateral | halves | 7.60 (p54) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LCx (1.00) | LCx | — |
| 12 mid anterolateral | halves | 7.74 (p52) | 1.02 | 1.00 (p53) | 0.0 | not shown: rest TPR gate fail | LAD (0.54) shared | LCx | — |
| 13 apical anterior | halves | 7.56 (p53) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LAD (1.00) | LAD | — |
| 14 apical septal | halves | 7.58 (p52) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | RCA (0.85) | LAD | — |
| 15 apical inferior | halves | 7.57 (p56) | 1.00 | 1.00 (p50) | 0.0 | not shown: rest TPR gate fail | LCx (0.52) shared | RCA | — |
| 16 apical lateral | halves | 7.56 (p52) | 1.00 | 1.00 (p45) | 0.0 | not shown: rest TPR gate fail | LCx (0.81) | LCx | — |
| 17 apex | halves | 7.58 (p99) | — | — | 0.0 | not shown: rest TPR gate fail | RCA (0.37) shared | LAD | — |

## Table B: territories

| Territory | Reader grade (CAD-RADS 2.0) | Mass g (share) | AHA default mass g | Segments | Shared segments | Thinning | Hypoattenuation | Fat | Composite | Mass distal to marked lesion (unvalidated) | Concordance |
|---|---|---|---|---|---|---|---|---|---|---|---|
| LAD | 1 | 13.0 (0.333) | 17.5 | 1, 7, 13 | 6, 12 | -0.01 mm | 0.00 rel. | 0.0 mm³ | no | — | No geometric sign in territory |
| LCx | 0 | 12.9 (0.329) | 10.8 | 5, 11, 16 | 4, 10, 15 | 0.01 mm | 0.00 rel. | 0.0 mm³ | no | — | No geometric sign in territory |
| RCA | 2 | 13.2 (0.338) | 10.8 | 3, 9, 14 | 2, 8 | -0.01 mm | 0.00 rel. | 0.0 mm³ | no | — | No geometric sign in territory |

---

Research output, not validated: no scar or perfusion reference.  
Thinning: a territory is flagged only when its wall is thinner than the patient's other walls by more than this population's normal variation allows. In simulation, a territory thinned by ≥ 20 % is flagged in ≥ 80 % of cases. Thinner changes are usually not flagged. This is not a sensitivity for scar, which this table cannot measure.  
Hypoattenuation: a territory is flagged only when its subendocardial attenuation is lower than the patient's other walls by more than this population's normal variation allows. In simulation, a territory with a relative subendocardial deficit of ≥ 15 % is flagged in ≥ 80 % of cases. Smaller changes are usually not flagged. This is not a sensitivity for scar, which this table cannot measure.  
Population: this population, phase-uncertain.
