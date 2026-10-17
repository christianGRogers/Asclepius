# CCTA sourcing brief (shared by all sourcing agents)

Goal (project lead's top priority, 2026-10-12): find as many CT scans of the coronary arteries as possible,
**labels not needed**, to feed a team of annotators who correct 14-class coronary predictions. We already have
ImageCAS (1000 CCTA, Guangdong) and ImageCAS-X (labels on 800 of them). Anything derived from ImageCAS is a
duplicate and does not count as new scans (note it, flag it).

## Fit tiers (classify every source)
- **T1** ECG-gated, contrast-enhanced coronary CT angiography (CCTA / CTCA / "coronary CTA").
- **T2** Other contrast-enhanced cardiac CT where coronaries are visible (cardiac CTA for TAVI/LAA/whole-heart,
  congenital heart CTA, cardiac functional CT, triple rule-out).
- **T3** Non-gated contrast chest CT where coronaries are partly visible (CTPA, aortic CTA, contrast chest CT).
  Large but lower value; report counts, don't chase every one.
- **Exclude** non-contrast (calcium scoring), MRI, X-ray angiography, ultrasound. Mention only if asked about.

## Deliverable
Write `sourcing/<YourName>.json`: a list of objects with
`name, url, tier, n_scans (number, and whether it is patients/studies/series), est_size_gb, format (DICOM/NIfTI/...),
labels (what, if any), license, access ("open-download" | "free-registration" | "DUA/application" | "restricted/
national" | "unavailable"), steps_to_access (exact), provenance/duplicates (e.g. "subset of X"),
verified (what you actually opened/tested: page read, file list seen, one file downloaded), notes`.
Also `sourcing/<YourName>.md`: a short ranked summary (best first) with sources cited as URLs.

For every **open-download** source you rate T1/T2, give a **tested download recipe**: actually download one
small file or one series (≤ 1 GB) to prove it works and that it is contrast cardiac CT (check DICOM tags or
NIfTI header/intensities: contrast lumen ~300–600 HU in the aorta), then **delete it**. Local disk is small
(~10 GB free): never keep more than 2 GB at once, put tests under `sourcing/tmp_<YourName>/` and remove them.

## Rules
- Verify, don't guess. Separate "read the primary page" from "a paper says so". Mark unverified claims.
- Never create accounts, accept a DUA, or submit an access form on anyone's behalf. List what the project
  lead must sign/register for, with the exact URL and expected wait.
- Never upload anything anywhere. Never touch Girder. Do not commit to git (the orchestrator does that).
- Note licences carefully (commercial use, redistribution, derivative labels) — the annotations will be shared.
- Be polite to servers (no parallel hammering). Use `pip install` freely in your own environment.
- Prefer quantity of genuinely new, independent CCTA scans; dedupe across sources where you can.
- Today is 2026-10-12. Search for 2024–2026 releases too.
