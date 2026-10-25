---
tags: [plans/experiment, round10, literature, fine-tune, continual-learning, anchoring, domain-shift, power]
author: Foxtrot
round: 10
updated: 2026-10-25
issue: christianGRogers/Asclepius#113
---

# Fine-tuning catches up with less compute, forgets without rehearsal, and team reads started from a seed agree more and are less accurate

**Question.** What does the published evidence say about the four Round 10 questions that the project's own data
cannot yet answer?
1. Warm fine-tune from Janus 0 against from-scratch training on ImageCAS-X + pool.
2. Forgetting ImageCAS-X while fine-tuning on the pool.
3. What reads started from an automatic mask measure.
4. How many runs a comparison needs.

**Method.** Each citation was checked against the paper's full text where it was available (arXiv/ar5iv HTML, Europe
PMC full text, the accepted manuscript), and every DOI against Crossref, on 2026-10-25. **Where only the abstract was
read, the row says so.** No number below comes from memory.

| # | Source | What it shows (where) | How it applies here | Caveat |
|---|---|---|---|---|
| 1 | He, Girshick, Dollár, *Rethinking ImageNet Pre-training*, ICCV 2019, doi:10.1109/ICCV.2019.00502, arXiv:1811.08883 | Random init reaches fine-tuning's accuracy given a longer schedule. Fig. 1 caption: it "needs more iterations to converge, but converges to a solution that is no worse". Table 1: R50 Mask R-CNN 40.7 vs 40.9 AP at 5×, 41.3 vs 41.1 at 6× (1× = 90k iterations). It **breaks down with little data**: 1k images give 9.9 (pre-trained) vs 3.5 AP (Fig. 7–8) | From-scratch on ImageCAS-X + pool (Crucible P4) should end where a warm start does, at about 5× the compute. A warm start is the cheap route for per-wave models | COCO detection, not CT. The "little data" regime is ours for the pool part (about 140 primary reads) |
| 2 | Ash & Adams, *On Warm-Starting Neural Network Training*, NeurIPS 2020, arXiv:1910.08475 | When a dataset grows, a model warm-started on the first half then trained on all of it generalizes **worse** than a fresh one (Table 1: CIFAR-10 ResNet-SGD 56.2 vs 51.7; CIFAR-100 ResNet-Adam 41.4 vs 35.0; gaps of about 1–7 points). "Shrink, perturb" closes the gap (Sec. 4, Fig. 7) | The one documented risk of warm-starting, and the reason the **final** model is a from-scratch retrain (P4-like), decided against the best warm model on D35 | Classification only, no segmentation. Shrink-perturb evidence is in figures, not a table |
| 3 | González, Ranem, Pinto dos Santos, Othman, Mukhopadhyay, *Lifelong nnU-Net*, Sci Rep 13:9381 (2023), doi:10.1038/s41598-023-34484-2 | Sequential nnU-Net fine-tuning onto a new domain **forgets** the old one. Rehearsal (replaying 25 % of earlier cases) prevents most of it. Table 1: hippocampus HarP 90.48 static, 20.20 sequential, 88.17 rehearsal; prostate I2CVB 93.05 / 21.04 / 90.64. Table 2 (cardiac, Siemens → Philips): Siemens LV 80.5 sequential vs 93.9 rehearsal | **Janus 1 must keep ImageCAS-X in its training mix**, and val 80 must guard against forgetting. Task 716 as written trains on pool reads only | MRI (prostate, hippocampus, cardiac), not CT. Forgetting was uneven: one first task was not forgotten |
| 4 | Tajbakhsh et al., *CNNs for Medical Image Analysis: Full Training or Fine Tuning?*, IEEE TMI 35(5):1299–1312 (2016), doi:10.1109/TMI.2016.2535302 | Fine-tuning "outperformed or, in the worst case, performed as well as" full training, and was more robust to training-set size (abstract; Figs. 2b, 4b, 6b for detection and classification) | Supports a warm fine-tune on a small target set | ImageNet pre-training, not same-domain. In its one segmentation task (Fig. 9), the small-data advantage was **not** shown |
| 5 | Kirkpatrick et al., *Overcoming catastrophic forgetting*, PNAS 114(13):3521–3526 (2017), doi:10.1073/pnas.1611835114 | The standard reference for catastrophic forgetting (EWC) | Background for (3) | Abstract and metadata only |
| 6 | Campello et al., *The M&Ms Challenge*, IEEE TMI 40(12):3543–3554 (2021), doi:10.1109/TMI.2021.3090082 | Models degrade on vendors and centres absent from training. Table IX: baseline −6.0 % Dice on vendor C; the top teams −1.6 to −1.7 %. Fig. 8: highest on centres in training with labels, lowest on unseen centres. The top three teams used nnU-Net with intensity augmentation and no domain adaptation (text by Table VIII) | Per-source reporting should separate **sources seen in fine-tuning** from **unseen** ones. The 22-source seal is mostly unseen to a fine-tune on the 5 open sources | Cardiac MRI. "More vendors in training helps" was not tested directly |
| 7 | Guberina et al., *Do AI-based contouring algorithms influence physicians in the online adaptive radiotherapy of patients with bladder cancer?*, Tech Innov Patient Support Radiat Oncol 38:100401 (2026), doi:10.1016/j.tipsro.2026.100401 | 13 physicians corrected propagated contours. They removed the algorithm's error only "on average to 70 % and at best to 43 %". The worse algorithm still gave the worse corrected contour in 151 of 169 comparisons (Table 1; slope 0.70 ± 0.02, Fig. 2): "the bias introduced by the algorithm was not fully compensated by the physician" | **Reads started from a TotalSegmentator seed (D26) will keep part of the seed's error.** That is the L5 risk, now with a number from segmentation | 9 patients; registration-propagated contours |
| 8 | Arjmandi et al., *Clinical validation of AI-assisted contouring in prostate radiation therapy treatment planning…*, J Appl Clin Med Phys 27(1):e70425 (2025), doi:10.1002/acm2.70425 | With AI-started contours, inter-observer CTV Dice **rose** from 0.78 to 0.89 (Tables 2–3), while agreement with the expert reference **fell**, 0.85 → 0.81 and 0.83 → 0.80 (Table 4) | The exact A10 failure mode: two seed-started reads agree more with each other, so inter-read tF1 rises and the A10 bar rises with it, while both move away from the truth | 2 readers; the authors hedge on the cause |
| 9 | Dratsch et al., *Automation Bias in Mammography*, Radiology 307(4):e222176 (2023), doi:10.1148/radiol.222176 | With incorrect "AI" suggestions, the share of correct ratings fell from 79.7 % to 19.8 % (inexperienced readers), from 81.3 % to 24.8 % (moderately experienced) and from 82.3 % to 45.5 % (very experienced) (abstract) | Inexperienced annotators anchor most. That argues for the A12 first-five-reads review (D18) | The suggestions came from a purported AI, i.e. they were scripted. Classification. Abstract only |
| 10 | Karimi, Dou, Warfield, Gholipour, *Deep learning with noisy labels*, MedIA 65:101759 (2020), doi:10.1016/j.media.2020.101759 | A review of label noise in medical segmentation (Sec. IV). Sec. V-C trains on computer-generated noisy segmentations | Background for seed-derived labels | — |
| 11 | Bouthillier et al., *Accounting for Variance in ML Benchmarks*, Proc. MLSys 3 (2021), arXiv:2103.03098 | Data sampling is the largest source of variance. Initialisation is "generally less than 50 % of the variance of bootstrap", on a par with data order (Fig. 1). Recommendation: randomise as many sources as possible and use several runs (Sec. 5) | Supports A22's seed term **and** a case bootstrap. It is not evidence that seeds dominate. Our own numbers show the seed term dominates only above about 50 cases | — |
| 12 | Christodoulou et al., *Confidence intervals uncovered*, MICCAI 2024, arXiv:2409.17763 | 221 segmentation papers; 1 reported CIs (Sec. 3, RQ1). In 64.9 % of the 77 papers whose CIs could be reconstructed, the runner-up's mean lay inside the winner's CI (Fig. 4b) | Report a CI and an MDE with every D35 decision (A19) | The CIs were reconstructed, not reported |
| 13 | Isensee et al., *nnU-Net Revisited*, MICCAI 2024, arXiv:2404.09556 | Table 1: CNN U-Nets (ResEnc, MedNeXt) match or beat Transformer and Mamba models. Examples: ResEnc L 88.17 vs SwinUNETR 81.27 on KiTS; U-Mamba about equal | No architecture change is indicated for Janus 1 | **Correction to Foxtrot v5:** cite Table 1 only (Table 2 is an Auto3DSeg ablation), and "match or beat", not "beat every" |

## What it changes in the plan

- **Warm fine-tune for every per-wave model, with ImageCAS-X rehearsal** (1, 3, 4). The final model is a from-scratch
  retrain on everything, compared once against the best warm model on D35 (1, 2).
- **A forgetting guard on val 80** for every fine-tune (3).
- **Seed anchoring is expected, not hypothetical** (7, 8). Inter-read agreement inflated by a shared seed raises
  A10's bar and makes the test conservative on extent. The plan measures it before any pool read (Foxtrot v6 §7),
  and puts L5 to the lead with this evidence.
- **Per-source reports split seen from unseen sources** (6).
- **Corrections to my own earlier text:** Foxtrot v5 §1 cited nnU-Net Revisited for "ResEnc M/L/XL match or beat
  every transformer and Mamba model" (Table 1). Table 1 supports "match or beat"; MedNeXt is best on some datasets.
