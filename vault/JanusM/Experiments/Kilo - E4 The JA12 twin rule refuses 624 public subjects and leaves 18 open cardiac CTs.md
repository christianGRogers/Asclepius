---
aliases: [Kilo E4]
tags: [janus-m, experiment, data, guard, twins, kilo, paired-scar]
status: done
round: 2
path: jm/paired-scar
updated: 2026-10-30
---

# Kilo E4: the JA12 twin rule refuses 624 public subjects and leaves 18 open cardiac CTs

**Question** (Round 1 ruling §6 item 7). TotalSegmentator publishes no patient id, so a coronary-held-out patient
could appear in the public release under a second s-number. JA12 requires the guard to refuse as a **twin** every
public subject matching a held-out subject on sex and institute, with age within ±5 years, of any study type. How many
public subjects does that refuse, and what is left for Janus-M's public-data experiments?

**Method.** `experiments/JanusM/Kilo/heldout.py` (Round 1 guard, extended: `refused_with_twins`, `check_public`),
driven by `e4_twins.py`, on the public `meta.csv` of TotalSegmentator v1 (Zenodo 6802614, CC BY 4.0; 1204 rows). Only
`meta.csv` was read; no image. The held-out set is my Round 1 list (16 s-numbers from the pool seal, the pool list, the
ImageCAS-X seal and every Round 10 D35 draw, which covers the reserve). The shared JA12 guard (#138) had not landed when
this ran, so this is the Round 1 guard plus the rule. A held-out id missing from `meta.csv` stops the run; a row with
no age would be refused on sex and institute alone (there are none). Output: `results_e4_twins.json`. It holds counts
and the open cardiac ids, never a held-out subject's demographics.

**Result.**

| | Subjects | Cardiac protocol ("ct heart", "ct coronary arteries", "ct aortic valve") |
|---|---|---|
| All | 1204 | 71 |
| Held out (direct) | 16 | 12 |
| JA12 twins | **624** | **41** |
| Open | 564 | **18** |

- All 16 held-out subjects come from one institute code (H), 9 men and 7 women. Ages are spread out, so the ±5-year
  windows cover most of institute H. That is why the rule refuses about half the release. It is the conservative
  over-refusal the ruling asked for, and costs public training cases, not Janus-M's seal or decision set (JA5: those
  are ImageCAS-X train only).
- Of the 18 open cardiac CTs, 14 have contrast in the LV blood pool (median LV HU > 150). Four are unenhanced.
- Twins by study type: mostly non-cardiac studies (thorax-abdomen-pelvis 68, thorax-neck 48, head CTA 46, …).

**The shared guard (#145) refuses more, and it binds.** `janusm.guard` pins its twins in
`configs/janusm/ts-twins-r1.json`, applying the same rule within each release, v1 and v2.0.1 (707 twins in all).
Ages differ between releases, so a subject can be a twin through its v2 metadata alone.

| On v1 `meta.csv` | Kilo (v1 only) | Shared guard (#145) |
|---|---|---|
| ids refused (held out + twins) | 640 (16 + 624) | **700** (16 + 684) |
| refused by Kilo but not the guard | 0 | — |
| cardiac protocol, open | 18 | **15** (13 enhanced) |

The three extra cardiac refusals are s0335, s0532 and s1237. **Disclosure:** s1237 was opened in E5's first run
(its public CT and masks). It is a possible twin of held-out s0980, matched through v2 metadata only, and not itself a
held-out patient. No coronary quantity was computed. The local copy is deleted, and E5 was re-run on the 13 enhanced
cases the guard allows. s0335 and s0532 were downloaded but never opened (unenhanced; E5 skips them before reading the
image). Reported on #143 and to the PM, who added s1237 to the lead's twin question.

**Disclosure.** No held-out subject's image was opened, in Round 1 or here. But **29 of the 40 public cases my Round 1
E1–E3 used are twins** under this rule (31 under the shared guard); 11 (9) remain open. Twins are not known to be held-out patients. The rule refuses
them because they cannot be ruled out. My Round 1 numbers (E1–E3) therefore rest mostly on cases the guard would now
refuse. They stay on record. Kilo v2's final numbers are computed on no twin. E5's first run opened one, s1237
(above), and was re-run without it.
None of these subjects can enter a coronary score.

**What it changes.**
- **Every Janus-M fetch of a public TotalSegmentator case must apply the twin rule before the first byte of an image.**
  `fetch_ts_cardiac.py` now does this (shared guard and its own rule), and asserts it again per case.
  `e5_lie_registration.py` refuses the whole run if a held-out or twin directory is on disk.
- **The public TotalSegmentator cardiac set is too small to be Janus-M's evidence base.** 15 cases, 13 enhanced, are
  enough for a CPU simulation. They are not enough for pretraining or as a report-only stratum. This strengthens JA5:
  Janus-M's data is ImageCAS-X train.
- The shared guard (#145) carries the rule. Kilo's code now calls `janusm.guard.refuse` first, and keeps its own
  v1-only check only as a second layer.
