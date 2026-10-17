# Bridge Trillium experiment: does rule naming (R) or grammar decoding (H) beat the direct model's own names (D)?

Model: **the Atlas run's** master-recipe 4-class nnU-Net (A13, inference/scoring only; plan `nnUNetResEncUNetPlans_60G_iso05`; softmax: Atlas validation --npz; training details in Atlas's results). Scored on its val split (80 cases) against Atlas's own proxy labels. tF1 @ 1.5 mm with reference-derived ostia (provisional per A9).

| Arm | n | tF1 @1.5 | tF1 @0 | macro Dice | cases with swap | centreline name acc. | FP comps |
|---|---|---|---|---|---|---|---|
| D: direct model names | 80 | 0.847 | 0.843 | 0.838 | 0 | 0.991 | 1.49 |
| R: rule renaming of D foreground | 80 | 0.834 | 0.830 | 0.827 | 3 | 0.981 | 1.49 |
| H: grammar decode of D softmax | 80 | 0.833 | 0.830 | 0.827 | 0 | 0.987 | 1.49 |
| O: oracle names on D foreground (naming upper bound) | 80 | 0.856 | 0.853 | 0.849 | 0 | 1.000 | 1.49 |

| Paired | mean diff tF1 | 95 % CI | better / worse cases |
|---|---|---|---|
| R-D | -0.0128 | [-0.0251, -0.0020] | 22 / 51 |
| H-D | -0.0133 | [-0.0223, -0.0060] | 20 / 51 |
| O-D | +0.0097 | [+0.0046, +0.0148] | 63 / 5 |

**A7 verdict** (adopt only if CI excludes 0 in its favour and swap rate is no higher):

- R: do not adopt (A7 rule not met)
- H: do not adopt (A7 rule not met)

Reading guide: O−D is how much naming headroom the direct model leaves on its own lumen. If R−D or H−D is positive with a CI above 0, structure out-names the network and Bridge v3 / A7 ship R or H; if the CIs sit at or below 0, the direct model names as well as the rules and R/H stay QA only.
