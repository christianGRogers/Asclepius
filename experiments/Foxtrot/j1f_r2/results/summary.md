# Foxtrot j1f round 2: summary (620 of the 620 in pass 1; 27 in the band pass)

## 1. Stage-1 labels (D47 Q1 = A, F-A3) and the origin collapse vs territory.to_four

```
{
 "d3": 47,
 "d4_to_lad": 2,
 "other_lcx": 20,
 "other_nearest": 1,
 "other_ignore": 8,
 "cases_with_D3": 47,
 "collapse_mismatch_voxels": 4919,
 "collapse_mismatch_cases": 5,
 "collapse_mismatch_left_pda_voxels": 4879,
 "ignore_voxels": 467,
 "ignore_share_of_tree": 2.23917839126684e-05,
 "recheck_with_grouped_posterior": {
  "n_rechecked": 61,
  "mismatch": 40,
  "mismatch_other_voxels": 40,
  "mismatch_left_posterior": 0,
  "cases_with_mismatch": 2
 }
}
```

## 2. Branch scorer self-tests

Identity (reference scored against itself, 620 cases; branch tF1 on the 20 fit-check cases):

| class | ref cases (>= 5 mm) | pieces | recall | naming | presence agr. | tF1 |
|---|---|---|---|---|---|---|
| D1 | 610 | 621 | 1.0 | 1.0 | 1.0 | 1.0 |
| D2 | 358 | 359 | 1.0 | 1.0 | 1.0 | 1.0 |
| D3 | 47 | 47 | 1.0 | 1.0 | 1.0 | 1.0 |
| OM1 | 539 | 541 | 1.0 | 1.0 | 1.0 | 1.0 |
| OM2 | 227 | 230 | 1.0 | 1.0 | 1.0 | 1.0 |
| Ramus | 149 | 154 | 1.0 | 1.0 | 1.0 | 1.0 |
| PDA | 606 | 676 | 1.0 | 1.0 | 1.0 | 1.0 |
| PLB | 601 | 620 | 1.0 | 1.0 | 1.0 | 1.0 |

Perturbations (the 20 fit-check cases): recall / naming / presence agreement / tF1

| perturbation | D1 | D2 | D3 | OM1 | OM2 | Ramus | PDA | PLB |
|---|---|---|---|---|---|---|---|---|
| swap_D1_D2 | 1.0 / 0.0 / 0.5 / 0.0 | 1.0 / 0.0 / 0.5 / 0.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 |
| drop_OM2 | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 0.0 / - / 0.3 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - |
| types_to_parent | 1.0 / 0.0 / 0.0 / - | 1.0 / 0.0 / 0.5 / - | 1.0 / 0.0 / 0.95 / - | 1.0 / 0.0 / 0.0 / - | 1.0 / 0.0 / 0.3 / - | 1.0 / 0.0 / 0.95 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - |
| erode_branches | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - |

## 3. Census used by the gate simulation (620)

| class | cases with any voxel | cl >= 5 mm | cl >= 3 mm | pieces / case | cases >= 2 pieces | median cl mm |
|---|---|---|---|---|---|---|
| D1 | 611 | 610 | 611 | 1.016 | 8 | 35.4 |
| D2 | 359 | 358 | 358 | 1.0 | 0 | 28.1 |
| D3 | 47 | 47 | 47 | 1.0 | 0 | 28.4 |
| OM1 | 540 | 540 | 540 | 1.002 | 1 | 35.9 |
| OM2 | 229 | 227 | 228 | 1.004 | 1 | 35.6 |
| Ramus | 149 | 149 | 149 | 1.034 | 5 | 36.7 |
| PDA | 608 | 606 | 608 | 1.112 | 65 | 46.3 |
| PLB | 610 | 601 | 610 | 1.016 | 10 | 47.05 |

## 4. Unnamed trunk twigs, three round-1 methods on the same cases

| method | vessel | cases >= 3 mm | cases >= 5 mm | cases >= 10 mm | twigs >= 5 mm |
|---|---|---|---|---|---|
| delta | LAD | 7 | 5 | 3 | 5 |
| delta | LCx | 1 | 1 | 0 | 1 |
| delta | RCA | 3 | 2 | 0 | 2 |
| foxtrot | LAD | 6 | 4 | 3 | 4 |
| foxtrot | LCx | 1 | 1 | 0 | 1 |
| foxtrot | RCA | 3 | 2 | 0 | 2 |
| crucible | LAD | 15 | 13 | 11 | 13 |
| crucible | LCx | 10 | 9 | 7 | 9 |
| crucible | RCA | 3 | 3 | 2 | 3 |

## 5. Dominance from labels

```
{
 "by_PDA": {
  "right": 570,
  "left": 36,
  "no PDA: left PLA": 10,
  "co (both PDAs)": 2,
  "no PDA: both/none": 2
 },
 "cases_with_left_PDA_or_PLA": 59,
 "cases_with_any_left_and_any_right_posterior": 13
}
```


## 6. Stage-2 background band (27 cases, ids divisible by 20 among the 620)

| w (mm) | S band cm3 | N band cm3 | R band cm3 | union cm3 | union / 256^3 patch | union / bg within 25 mm | S prox/mid/dist | traced branch vol within w of LAD |
|---|---|---|---|---|---|---|---|---|
| 4 | 11.1 | 4.6 | 6.3 | 20.0 | 0.009 | 0.019 | [0.367, 0.309, 0.324] | 0.064 |
| 8 | 38.8 | 18.2 | 22.6 | 69.1 | 0.033 | 0.065 | [0.365, 0.3, 0.335] | 0.129 |
| 15 | 129.7 | 72.1 | 78.6 | 231.3 | 0.110 | 0.213 | [0.369, 0.284, 0.347] | 0.243 |
| 25 | 362.1 | 238.0 | 232.7 | 634.6 | 0.303 | 0.586 | [0.375, 0.268, 0.357] | 0.299 |

Medians over cases. Traced tree volume, median 1.96 cm3.

Synthetic septals (81 tubes): mean share of the centreline inside the band (unpenalised by CE)

| length mm | w=4 | w=8 | w=15 | w=25 | hits a traced vessel |
|---|---|---|---|---|---|
| 10 | 0.474 | 0.881 | 1.0 | 1.0 | 0.008 |
| 20 | 0.24 | 0.453 | 0.831 | 1.0 | 0.003 |
| 30 | 0.16 | 0.303 | 0.559 | 0.917 | 0.002 |
| 40 | 0.121 | 0.228 | 0.42 | 0.698 | 0.002 |
| 60 | 0.081 | 0.152 | 0.281 | 0.466 | 0.002 |
