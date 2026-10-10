---
tags: [plans, candidate, amendments, roi, fp-gate, round6]
author: Foxtrot
round: 6
version: 2
updated: 2026-10-10
---

# Foxtrot v2: F3/A20's reference-side check holds on all 92 cached non-sealed cases (max 16.5 mm); a proposed job for the other 908

## 1. Thesis

v2 is [[Foxtrot v1]] as adopted in [[Round 6]]:

- F1 became A17a;
- F2 became A17b;
- F3 became A20 (conditional);
- F4 is a noted, unscheduled proposal.

Nothing in the recipe changes. v2 does two things. It reports A20 condition 1 as far as this machine
allows, and it costs the rest of that check as a GPU-job proposal. This is **a proposal only**: no
`trillium/` file and no job.

## 2. A20 condition 1 so far (CPU, done)

Evidence: [[Foxtrot - The ImageCAS reference lies wholly within 17 mm of a TotalSegmentator heart-and-aorta ROI]] (extension section).

- **Scope.** All 92 non-sealed cases whose CT is cached. TotalSegmentator 2.18 `fast`,
  `roi_subset=['heart', 'aorta']`, on CPU, nice, one process. No CT was downloaded.
- **Maximum reference-to-ROI distance: 16.5 mm** (c0073). The required bound is d − 5 = 20 mm. All 92 pass.
- **Tail.** 4 cases exceed 15 mm: c0073 16.5, c0252 16.4, c0575 16.2 and c0606 15.8. None exceeds 18 mm.
  The per-case maximum has mean 11.4 mm and s.d. 2.0.
- **Rule effect on the reference.** At d = 25 mm the rule deletes 0 reference components. No heart mask
  triggered the < 5000-voxel disable.

## 3. Proposed job: the remaining 908 cases (808 non-sealed, 100 sealed)

**Combine it with A21's aorta producer.** A21 requires TotalSegmentator aortas for every scored CT. The
heart comes from the same model call (`roi_subset=['heart', 'aorta']`), so one batch run serves both A1 and
A20. Keep the fast 3 mm model, because the rule was frozen with it.

**Inputs.**

- The 1000 CTs and binary masks as staged on `$SCRATCH` by the export/transfer path. Wave training needs
  them there anyway; compute nodes have no outbound network.
- The script `experiments/Foxtrot/heart_roi_ref.py`, unchanged except for an output switch for sealed
  cases.

**Outputs.**

- **Non-sealed (808).** The same JSON line per case as here: maximum and p99 distance, voxels beyond
  {10, 15, 20} mm, and heart-mask size.
- **Sealed (100).** An automated pass that writes **only**:
  - a count of cases passing the bound (maximum ≤ 20 mm);
  - a count of heart-mask disables;
  - if any sealed case fails, the smallest d in {25, 30, 35, 40} at which all sealed cases pass.

  No per-case distance and no case id is written. The heart and aorta masks themselves are kept, because
  A1 needs the sealed aortas at the milestone, and are not inspected.

**Pre-registered response, applied before any prediction is examined.**

| Outcome | Action |
|---|---|
| Every non-sealed case ≤ 20 mm, and all sealed pass | Condition 1 met at d = 25 mm |
| Some non-sealed case > 20 mm | d := (cohort maximum + 5 mm), rounded up to the next 5 mm. Report the cases. Condition 2's census threshold is re-read at the new d |
| A sealed case fails | d := the smallest passing value reported by the automated pass, if that is larger than the non-sealed rule's d |
| A heart mask is disabled on > 2 % of cases | Report to the judge. Those cases are scored without F3 (raw count) |

**Cost (estimate; not measured on Trillium).**

- Measured on this CPU: median 51 s per case, one thread, of which TotalSegmentator inference is most.
  That is ≈ 13 CPU-h for 908 cases.
- **Option A, CPU in a GPU job:** 32 parallel workers on the node's cores, about 0.5 h wall.
- **Option B, GPU TotalSegmentator:** the 3 mm model is small, so expect a few seconds per case on an H100,
  roughly 1–1.5 h including I/O. Either fits one job of ≤ 2 h walltime, **≤ 2 H100-h**.
- Disk: per-case JSON (KB), plus the uint8 3 mm aorta+heart masks kept for A1 (≈ 50 KB each, ≈ 50 MB).
- Human effort: none, unless a case fails.

**When.** After atlas2 returns. Round 6 forbids new Trillium work now. Run it with or before A21's aorta
producer, which A1a needs before any decisive tF1 outside a Trillium job.

## 4. Sections unchanged from v1

The full recipe (§2), evaluation (§3), evidence (§4), risks (§5), comparison (§6) and cost (§7) are as in
[[Foxtrot v1]], with the Round 6 amendments A17a, A17b and A20 applied. The one cost change is A20's
cohort check: ≤ 2 H100-h, or none if it is folded into the A21 producer job.

## 5. Changes since v1

1. A20 condition 1 is measured on all 92 cached non-sealed cases (v1: 40). The maximum is still 16.5 mm.
2. The cohort-wide remainder is written up as a costed job proposal, with a sealed-safe output and a
   pre-registered response.
3. **Improve, not restart:** the v1 amendments were adopted, and there is nothing to restart.
