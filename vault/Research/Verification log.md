---
tags: [verification, citations, research]
status: in-progress
updated: 2026-09-20
---

# Citation Verification Log

**Work in progress** — auditing claims marked unverified, abstract-only, secondhand, or flagged for hand fetch. This log will track outcomes and corrections as sources are verified.

## Summary (preliminary)
- Total claims audited: 0 (scanning complete, verification in progress)
- Resolved: 0
- Wrong: 0
- Still unreachable: 0

---

## To verify (extracted from Research/ notes)

### Annotation and label efficiency

1. **File:** How well two annotators agree on per-branch coronary labels.md
   - **Claim:** Inter-observer agreement ≈ 0.856 (used in Training plan)
   - **Status:** Unverified — source not found in original searches
   - **Outcome:** [Pending]

### Architectures and training

2. **File:** Binary-init fine-tuning and multi-task auxiliary heads for the multiclass model.md
   - **Claim:** Centerline-supervision multi-task learning improves accuracy and connectivity
   - **Source:** ScienceDirect, DOI-indexed
   - **Status:** Flagged for hand fetch — abstract only, Dice/connectivity unverified
   - **Outcome:** [Pending]

3. **Same file**
   - **Claim:** Joint direction- and centerline-aware learning (JLNet) enforces vessel connectivity learning
   - **Source:** ACM DL summary only
   - **Status:** Flagged for hand fetch — quantitative comparison unverified
   - **Outcome:** [Pending]

4. **File:** Foundation and promptable models do not yet beat a configured nnU-Net for coronaries.md
   - **Claim:** Mask SAM 3D fine-tuned on coronary CCTA with vesselness-derived bounding-box prompts
   - **Source:** Int J CARS 2026, DOI 10.1007/s11548-025-03536-5 (PMID 41145776)
   - **Status:** Flagged for hand fetch — PubMed record only, quantitative Dice unverified
   - **Outcome:** [Pending]

5. **Same file**
   - **Claim:** SSL pretraining + nnU-Net specific combination results unverified
   - **Source:** None specified
   - **Status:** Unverified
   - **Outcome:** [Pending]

### Augmentation and preprocessing

6. **File:** Calcified plaque, stents and motion are the CCTA failure modes.md
   - **Claim:** AJR editorial on stent-imaging and in-stent restenosis in small-caliber vessels
   - **Source:** AJR editorial (403 error, no authenticated browser)
   - **Status:** Flagged for hand fetch
   - **Outcome:** [Pending]

7. **Same file**
   - **Claim:** TW-MoCoNet motion-correction reports 80.2% reduction in moderate-artifact segments
   - **Source:** Search summaries only, not opened in full
   - **Status:** Flagged for hand fetch — unverified
   - **Outcome:** [Pending]

### Datasets and benchmarks

8. **File:** Public coronary CCTA datasets.md
   - **Claim:** CCA-200 (200 CCTA cases) reports Dice 0.778
   - **Source:** IEEE TMI 2025 paper citing CCA-200 (not independently opened)
   - **Status:** Unverified secondhand
   - **Outcome:** [Pending]

9. **Same file**
   - **Claim:** PCCTA120 (120 CCTA volumes with artery and plaque masks)
   - **Source:** 2026 joint artery+plaque segmentation paper (not independently opened)
   - **Status:** Unverified secondhand
   - **Outcome:** [Pending]

---

## Verification progress

[Verification attempts will be logged here as sources are accessed or determined unreachable]

