---
tags: [plans, experiment, verification, losses, topology, literature]
author: Delta
round: 1
updated: 2026-10-04
---

# Topology losses on coronaries: the numbers are verified, and they recover branches but do not connect them

## Question

The vault's [[Topology-aware losses on thin tubular structures]] carries the load-bearing
numbers for any topology-first plan. Are those sources real, are the numbers right, and what
do they actually say about *coronary* data (as opposed to retina, roads, Circle of Willis)?

## Method

Primary sources fetched from arXiv (`export.arxiv.org` metadata + `arxiv.org/html` full text,
grepped for the tables), Crossref for DOIs, and the Tecnalia repository record for the one
paywalled paper. Nothing here is from a secondary summary.

| Source | Identifier | Verified |
|---|---|---|
| clDice — Shit et al., CVPR 2021 | arXiv:2003.07311 | title/authors/abstract |
| Skeleton Recall — Kirchhoff et al., ECCV 2024 | arXiv:2404.03010v2 | full text: Table 2, overhead paragraph, method (skeleton dilated with diamond kernel r=2) |
| cbDice — Shi et al., MICCAI 2024 | arXiv:2407.01517 | title/authors/abstract |
| ImageCAS-X — Bransby et al., preprint 31 Aug 2026 | arXiv:2608.30404 | full text: Table 2, Table 3, Table 5, App. E |
| BCS — Owusu-Ansah et al., STACOM 2026 preprint 30 Jul 2026 | arXiv:2607.28327 | full text: §1.1, §2.3, Table 2 |
| Clinically-informed topology benchmark — Acebes, Galdran, Moustafa, Clapers, Camara, LNCS (STACOM) 2026 | doi:10.1007/978-3-032-17734-6_2 | Crossref + abstract (Tecnalia repository); full text not opened |
| TopCoW — Yang et al., NEJM AI 2026 | doi:10.1056/AIdbp2500994; arXiv:2312.17670v3 | Crossref; arXiv text §5.1 |
| CorSegRec (DPC-Walk reconnection) — Qiu et al. | arXiv:2504.01597 | title/abstract (88.53 % Dice, 1.07 mm HD on ASOCA) |
| Marginal loss for partial labels — Shi, Xiao, Chen, Zhou, MedIA 2021 | arXiv:2007.03868 | title/abstract |

## Result

**All sources exist and every number I re-read matches the vault.** The coronary-specific
evidence, verbatim from the tables:

*ImageCAS-X Table 2* (160 double-read test cases, 0.5 mm isotropic, one run per method, shared
framework, 1000 epochs × 250 iterations, post-processing = threshold 0.5 + remove components
< 100 voxels):

| Method | DSC | HD95 mm | Betti err | clDice | ASSD mm |
|---|---|---|---|---|---|
| nnU-Net | 89.8 ± 3.2 | 7.08 | 5.6 ± 3.5 | 92.3 | 1.02 |
| nnU-Net + clDice | 90.0 ± 3.5 | 9.70 | **8.0 ± 4.4** | 91.7 | 1.20 |
| CAS-Net (Dong et al., MedIA 2023) | 91.2 ± 2.8 | 2.99 | **1.9 ± 1.5** | 93.3 | 0.73 |
| Inter-observer | 92.8 ± 3.1 | 2.46 | 0.4 ± 0.4 | 95.4 | 0.53 |
| Original ImageCAS labels vs ICX | 41.8 ± 6.7 | 16.15 | 7.0 ± 6.7 | 78.2 | 2.23 |

The clDice weight is not stated (App. Table 5 lists only "Dice, CE, clDice [DS]"). The authors'
own sentence: *"topological errors such as vessel breaks are present in all model predictions
despite high DSC and clDice."* Their component-removal rule is size-based, not keep-largest,
*"as the LCx and LAD can connect directly to the aortic annulus resulting in variable number of
true components."*

*BCS Table 2* (ImageCAS 750/250, 1.0 mm isotropic, 3 seeds, three backbones, topology weight
α = 0.05 for every topology loss): clDice changes nothing (Dice within 0.004, β₀ within 2.3);
Skeleton Recall raises FFR-CT decision agreement ~10 pp and BCS by 0.04–0.07 **and roughly
doubles β₀** (4.3→8.0, 2.9→5.8, 7.9→11.9). §2.3: *"𝒞skel leaves more disconnected components
than 𝒞topo (Δβ₀ = +2.94, d_z = 0.68, p < 10⁻¹⁰) in 70.8 % of cases"*, and *"The FFR solver
bridges gaps below 1.5 mm before computing flow."* Their conclusion: *"Recovering branches and
keeping them connected are separable properties."* Mechanism stated in §1: Skeleton Recall and
soft-BCS are recall-based, so *"they control which branches appear but not how they join up."*

*Skeleton Recall* (own paper): +1.2 Dice on 13-class TopCoW with nnU-Net, clDice OOM there;
overhead *"approximately 88 % additional training time and 52 % more VRAM"* for clDice vs an
additional 8 % / 2 % for Skeleton Recall (averaged over their 5 datasets).

*Acebes et al. 2026* (ASOCA, abstract): topology-aware methods *"perform similarly on primary
segments"*; differences appear in secondary/tertiary segments, where annotation inconsistency
matters more than method.

*TopCoW* §5.1: the two winning multiclass teams used skeleton/centreline objectives
(clDice+SkelRecall; cbDice+BTI) and *"seemed to improve connectivity"* — an observational
remark about challenge entries, not a controlled ablation.

## What it implies

1. **No topology loss has been shown to reduce fragmentation on coronary CCTA.** On ImageCAS,
   clDice is neutral (BCS, 3 seeds) or harmful (ImageCAS-X, Betti 5.6→8.0); Skeleton Recall
   recovers branches and *increases* components. A topology-first plan therefore cannot rest on
   a loss to deliver connectivity; connectivity has to come from post-processing (gap bridging
   — which is what the FFR solver in BCS silently did) and be **measured**.
2. Skeleton Recall is still the right loss to carry: it is the only one with a coronary branch-
   recovery gain, it is cheap (CPU skeleton in the data loader) and multiclass-native. Its known
   side effect (more fragments) is exactly what a reconnection step and a rooted-connectivity
   metric are for.
3. Architecture matters more than the loss for topology on this cohort: CAS-Net's Betti error
   is 1.9 vs nnU-Net's 5.6 in the same framework. That is one run, one framework, and nnU-Net
   was run inside ICX's framework rather than its own pipeline, so it is a hint, not a ruling.
4. The four classes this project labels are the *primary* segments, where Acebes et al. find
   topology methods do not differ. Topology work pays off on the distal parts of those trunks
   and on whatever side branches the 4-class convention folds into them.

## Limits

- ImageCAS-X and BCS are 2026 preprints (BCS a workshop paper); single framework each.
- BCS runs at 1.0 mm, ~3× coarser than native; breaks are more likely there.
- Acebes et al. read at abstract level only; do not quote numbers from it.
- CorSegRec's DPC-Walk numbers are ASOCA-only and the reconnection stage is not ablated in
  isolation against a simple distance rule.
