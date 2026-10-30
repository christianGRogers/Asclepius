"""E3: can Stage A thinning be calibrated without a scar reference? (Janus-M R2, path jm/rest-ccta, item 9)

A simulation, no image. A reference population of hearts has 16 segment thicknesses each:

    thickness = scale_p * phase_p * shape_s * exp(noise_ps) * (1 - depth if the segment is thinned) + error

- scale_p: patient size, lognormal (CV 0.12);
- phase_p: reconstruction phase, unknown per patient (ImageCAS records none): end-diastole 1.00, mid-diastole 1.14
  (Chen 2025: 5.7 vs 6.5 mm), or systole 1.40 (assumed); the mix is a parameter;
- shape_s: the normal segment pattern; noise_ps: normal segment-to-segment variation (SD `cv_n`, swept);
- a fraction `prev` of patients have a chronic infarct: 2-4 contiguous segments of one territory (AHA default
  map) thinned by `depth` (relative);
- error: segment-thickness measurement error, SD `sig_m` mm (JA8's co-primary; E2 maps it to border ASSD).

Three rules, each calibrated *only* on the unlabelled population (it contains the infarcts, as a real one would):
- A: the CMR end-diastolic cut, thickness <= 5.5 mm (Shah 2013), borrowed as is;
- B: per-segment population 2.5th percentile of absolute thickness;
- C (Lima): patient-relative and shape-corrected, z = (thickness / patient median - segment shape) / segment scale, flagged
  below a robust cut (median - k * 1.4826 * MAD of the pooled z), and **reported per territory**: a territory is
  flagged when >= 2 of its segments are flagged and they are contiguous. k is set so that <= 5 % of patients
  have any flagged territory, from the pooled data itself.

Reported: the share of infarct-free patients with any flag (patient-level false flags), by phase; the sensitivity
for the infarct territory; and the depth needed for 80 % sensitivity at each measurement error.

    python calibrate_sim.py OUT_JSON
"""
import json
import sys

import numpy as np

AHA = {"LAD": [1, 2, 7, 8, 13, 14, 17], "RCA": [3, 4, 9, 10, 15], "LCx": [5, 6, 11, 12, 16]}
# AHA adjacency on the bullseye (rings of six, apical four), for "contiguous"
RING = {1: [2, 6, 7], 2: [1, 3, 8], 3: [2, 4, 9], 4: [3, 5, 10], 5: [4, 6, 11], 6: [5, 1, 12],
        7: [8, 12, 1, 13], 8: [7, 9, 2, 13, 14], 9: [8, 10, 3, 14, 15], 10: [9, 11, 4, 15], 11: [10, 12, 5, 15, 16],
        12: [11, 7, 6, 16, 13], 13: [14, 16, 7, 8, 12], 14: [13, 15, 8, 9], 15: [14, 16, 9, 10, 11],
        16: [15, 13, 11, 12]}
TERR16 = {t: [s for s in v if s <= 16] for t, v in AHA.items()}
# Normal segment pattern (relative to the patient's median): septum thicker, apex thinner. Placeholder values in
# the direction of CT/CMR normals; Job JM-0b measures the real pattern (rel_thickness_by_segment_mean_sd).
SHAPE = np.array([1.00, 1.08, 1.10, 1.02, 0.98, 0.98, 1.00, 1.08, 1.10, 1.02, 0.98, 0.98,
                  0.88, 0.92, 0.90, 0.88])
PHASES = {"ED": 1.00, "MD": 1.14, "SYS": 1.40}
ED_MEDIAN_MM = 5.7  # Chen 2025, end-diastolic global mean on CT


def population(n, prev, depth, cv_n, sig_m, phase_mix, rng):
    scale = ED_MEDIAN_MM * np.exp(rng.normal(0, 0.12, n))
    ph_names = rng.choice(list(PHASES), size=n, p=[phase_mix[k] for k in PHASES])
    ph = np.array([PHASES[k] for k in ph_names])
    true = scale[:, None] * ph[:, None] * SHAPE[None, :] * np.exp(rng.normal(0, cv_n, (n, 16)))
    sick = rng.random(n) < prev
    lesion = np.zeros((n, 16), bool)
    terr = np.array([None] * n, object)
    for i in np.nonzero(sick)[0]:
        t = rng.choice(list(TERR16))
        seed = rng.choice(TERR16[t])
        k = rng.integers(2, 5)
        segs = {seed}
        while len(segs) < min(k, len(TERR16[t])):
            nb = [x for s in segs for x in RING[s] if x in TERR16[t] and x not in segs]
            if not nb:
                break
            segs.add(rng.choice(nb))
        lesion[i, [s - 1 for s in segs]] = True
        terr[i] = t
    true = np.where(lesion, true * (1 - depth), true)
    meas = true + rng.normal(0, sig_m, (n, 16))
    return meas, lesion, sick, terr, ph_names


def territory_flags(flag):
    """flag: n x 16 bool -> n x 3 bool (LAD, RCA, LCx): >= 2 flagged, contiguous segments in the territory."""
    out = np.zeros((flag.shape[0], 3), bool)
    for j, (t, segs) in enumerate(TERR16.items()):
        for s in segs:
            nbs = [x for x in RING[s] if x in segs]
            out[:, j] |= flag[:, s - 1] & flag[:, [x - 1 for x in nbs]].any(1)
    return out


def rule_c_scores(meas):
    # a linear ratio, not a log: millimetre error is symmetric, and a log would skew it into the left tail that
    # the mirror null cannot see
    rel = meas / np.median(meas, 1, keepdims=True)
    shape = np.median(rel, 0)  # the pattern is learned from the unlabelled population itself
    z = rel - shape
    # per-segment robust scale from the right half (thinning cannot reach it): thin apical segments carry a
    # larger relative measurement error, and a single pooled scale under-calls their false flags
    scale = np.array([1.4826 * np.median(np.abs(c[c >= 0])) for c in z.T])
    return z / scale


def calibrate_c(z, target=0.05, rng=None):
    """Find the cut so that <= target of *null* patients have any flagged territory. No label is used. The null
    is the **mirror** of the pooled scores' right half (z >= median), which thinning cannot reach: reflected
    about the median it gives a symmetric null with the real tail shape of the measurement error. Null patients
    are 20 000 draws of 16 segments from it; the cut is read off their territory-flag rate."""
    rng = rng or np.random.default_rng(0)
    z = z.ravel()
    med = np.median(z)
    right = z[z >= med] - med
    pool = np.r_[med + right, med - right]
    null = rng.choice(pool, (20000, 16))
    mad = 1.4826 * np.median(right)
    for k in np.arange(1.0, 6.01, 0.05):
        if territory_flags(null < med - k * mad).any(1).mean() <= target:
            return med - k * mad, float(k)
    return med - 6 * mad, 6.0


def evaluate(meas, lesion, sick, terr, ph, cut_c):
    tnames = list(TERR16)
    res = {}
    flagsA = meas <= 5.5
    q = np.percentile(meas, 2.5, axis=0)
    flagsB = meas <= q[None, :]
    flagsC = rule_c_scores(meas) < cut_c
    for name, f in (("A_cmr_5p5mm", flagsA), ("B_pop_p2p5", flagsB), ("C_relative_territory", flagsC)):
        tf = territory_flags(f)
        anyflag = tf.any(1)
        hit = np.array([tf[i, tnames.index(terr[i])] for i in np.nonzero(sick)[0]])
        r = {"patient_false_flag": round(float(anyflag[~sick].mean()), 3),
             "territory_sensitivity": round(float(hit.mean()), 3) if len(hit) else None}
        r["patient_false_flag_by_phase"] = {p: round(float(anyflag[~sick & (ph == p)].mean()), 3)
                                            for p in PHASES if (~sick & (ph == p)).any()}
        res[name] = r
    return res


def main(out):
    rng = np.random.default_rng(20261030)
    grid = []
    mixes = {"all_ED": {"ED": 1.0, "MD": 0.0, "SYS": 0.0},
             "mixed": {"ED": 0.4, "MD": 0.4, "SYS": 0.2}}
    for mix_name, mix in mixes.items():
        for cv_n in (0.06, 0.10, 0.15):
            for sig_m in (0.25, 0.5, 1.0):
                for depth in (0.2, 0.3, 0.4, 0.5):
                    for prev in (0.1, 0.3):
                        meas, lesion, sick, terr, ph = population(2000, prev, depth, cv_n, sig_m, mix, rng)
                        cut, k = calibrate_c(rule_c_scores(meas))
                        r = evaluate(meas, lesion, sick, terr, ph, cut)
                        grid.append(dict(phase_mix=mix_name, cv_n=cv_n, sig_m=sig_m, depth=depth, prev=prev,
                                         k_mad=k, **r))
    # depth needed for 80 % territory sensitivity under rule C (mixed phase, prevalence 0.1)
    need = {}
    for cv_n in (0.06, 0.10, 0.15):
        for sig_m in (0.25, 0.5, 1.0):
            rows = [g for g in grid if g["phase_mix"] == "mixed" and g["prev"] == 0.1 and g["cv_n"] == cv_n
                    and g["sig_m"] == sig_m]
            ok = [g["depth"] for g in sorted(rows, key=lambda g: g["depth"])
                  if g["C_relative_territory"]["territory_sensitivity"] >= 0.8]
            need[f"cv{cv_n}_sig{sig_m}"] = ok[0] if ok else ">0.5"
    json.dump({"grid": grid, "depth_for_80pct_sensitivity_rule_C": need}, open(out, "w"), indent=1)
    print(json.dumps(need, indent=1))
    for g in grid:
        if g["cv_n"] == 0.10 and g["prev"] == 0.1 and g["depth"] in (0.3, 0.4):
            print(g["phase_mix"], g["sig_m"], g["depth"], g["k_mad"],
                  {k: (v["patient_false_flag"], v["territory_sensitivity"]) for k, v in g.items()
                   if isinstance(v, dict) and "patient_false_flag" in v})


if __name__ == "__main__":
    main(sys.argv[1])
