# Foxtrot j1f round 2: summary (75 of the 620 in pass 1; 0 in the band pass)

## 1. Stage-1 labels (D47 Q1 = A, F-A3) and the origin collapse vs territory.to_four

```
{
 "d3": 4,
 "d4_to_lad": 0,
 "other_lcx": 3,
 "other_nearest": 0,
 "other_ignore": 0,
 "cases_with_D3": 4,
 "collapse_mismatch_voxels": 2540,
 "collapse_mismatch_cases": 2,
 "collapse_mismatch_left_pda_voxels": 2540,
 "ignore_voxels": 0,
 "ignore_share_of_tree": 0.0
}
```

## 2. Branch scorer self-tests

Identity (reference scored against itself, 75 cases; tF1 on the 7 cases with id % 10 == 0):

| class | ref cases (>= 5 mm) | pieces | recall | naming | presence agr. | tF1 |
|---|---|---|---|---|---|---|
| D1 | 74 | 75 | 1.0 | 1.0 | 1.0 | 1.0 |
| D2 | 49 | 49 | 1.0 | 1.0 | 1.0 | 1.0 |
| D3 | 4 | 4 | 1.0 | 1.0 | 1.0 | 1.0 |
| OM1 | 71 | 71 | 1.0 | 1.0 | 1.0 | 1.0 |
| OM2 | 31 | 32 | 1.0 | 1.0 | 1.0 | 1.0 |
| Ramus | 12 | 15 | 1.0 | 1.0 | 1.0 | None |
| PDA | 74 | 79 | 1.0 | 1.0 | 1.0 | 1.0 |
| PLB | 74 | 76 | 1.0 | 1.0 | 1.0 | 1.0 |

Perturbations (7 cases): recall / naming / presence agreement / tF1

| perturbation | D1 | D2 | D3 | OM1 | OM2 | Ramus | PDA | PLB |
|---|---|---|---|---|---|---|---|---|
| swap_D1_D2 | 1.0 / 0.0 / 0.857 / 0.0 | 1.0 / 0.0 / 0.857 / 0.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 | - / - / 1.0 / - | 1.0 / 1.0 / 1.0 / 1.0 | 1.0 / 1.0 / 1.0 / 1.0 |
| drop_OM2 | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 0.0 / - / 0.571 / - | - / - / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - |
| types_to_parent | 1.0 / 0.0 / 0.0 / - | 1.0 / 0.0 / 0.143 / - | 1.0 / 0.0 / 0.857 / - | 1.0 / 0.0 / 0.143 / - | 1.0 / 0.0 / 0.571 / - | - / - / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - |
| erode_branches | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 1.0 / - | - / - / 1.0 / - | 1.0 / 1.0 / 1.0 / - | 1.0 / 1.0 / 0.857 / - |

## 3. Census used by the gate simulation (620)

| class | cases with any voxel | cl >= 5 mm | cl >= 3 mm | pieces / case | cases >= 2 pieces | median cl mm |
|---|---|---|---|---|---|---|
| D1 | 74 | 74 | 74 | 1.014 | 1 | 32.25 |
| D2 | 49 | 49 | 49 | 1.0 | 0 | 26.9 |
| D3 | 4 | 4 | 4 | 1.0 | 0 | 37.75 |
| OM1 | 71 | 71 | 71 | 1.0 | 0 | 33.7 |
| OM2 | 32 | 31 | 32 | 1.0 | 0 | 39.7 |
| Ramus | 12 | 12 | 12 | 1.25 | 3 | 30.2 |
| PDA | 74 | 74 | 74 | 1.068 | 5 | 47.400000000000006 |
| PLB | 75 | 74 | 75 | 1.013 | 1 | 47.8 |

## 4. Unnamed trunk twigs, three round-1 methods on the same cases

| method | vessel | cases >= 3 mm | cases >= 5 mm | cases >= 10 mm | twigs >= 5 mm |
|---|---|---|---|---|---|
| delta | LAD | 1 | 1 | 0 | 1 |
| delta | LCx | 0 | 0 | 0 | 0 |
| delta | RCA | 0 | 0 | 0 | 0 |
| foxtrot | LAD | 1 | 1 | 0 | 1 |
| foxtrot | LCx | 0 | 0 | 0 | 0 |
| foxtrot | RCA | 0 | 0 | 0 | 0 |
| crucible | LAD | 4 | 4 | 3 | 4 |
| crucible | LCx | 3 | 3 | 2 | 3 |
| crucible | RCA | 0 | 0 | 0 | 0 |

## 5. Dominance from labels

```
{
 "by_PDA": {
  "right": 72,
  "left": 2,
  "no PDA: left PLA": 1
 },
 "cases_with_left_PDA_or_PLA": 4,
 "cases_with_any_left_and_any_right_posterior": 1
}
```

