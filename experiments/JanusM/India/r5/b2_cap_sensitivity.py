"""India R5, item 2 of #223: how much the cap-scoped remedy depends on its two free parameters.

``b1_band_remedy.band_cap`` defines a cap face by a reach (distance to the nearest open pool
face) and an angle (its normal against that pool face's normal). This reruns the E6-open
phantom (0.5 mm grid, three walls, both borders, +-0.3 / +-0.5 mm) and the cut capsule (0.5 mm
grid, three walls, one offset) over reach {12, 20, 30} mm and angle {30, 45, 60} degrees, and
records the worst error and the share of the shipped epicardial band each setting keeps.
Synthetic only; no case is opened.

Run from the repo root:  python experiments/JanusM/India/r5/b2_cap_sensitivity.py
"""
from __future__ import annotations

import json
import pathlib
import sys

import numpy as np

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import b1_band_remedy as B  # noqa: E402

H, T = B.H, B.T


def main():
    B.guard.refuse([], what="India R5 b2 cap sensitivity (synthetic phantoms; no case opened)")
    sp = (0.5, 0.5, 0.5)
    cases = []
    for rot, rough in [(None, False), (23, False), (11, True)]:
        Fc, Fs, base, _ = T._e6_phantom(sp, rot, rough)
        lab = T._e6_labels(Fc, Fs, base)
        cases.append(("E6-open", lab, np.array(sp), {"endo": Fc, "epi": Fs}, base))
    rng = np.random.default_rng(20261030)
    off = rng.uniform(0.0, 0.5, size=(1, 3))[0]
    caps = []
    for cs, tilt in ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0)):
        cav, sol, lab, aff = H._open_base_parts(sp, 0.0, 0.0, off, cs, tilt)
        caps.append((lab, np.linalg.norm(aff[:3, :3], axis=0), cs, tilt, cav, sol))
    out = []
    for reach in (12.0, 20.0, 30.0):
        for angle in (30.0, 45.0, 60.0):
            errs, keep = [], []
            for _, lab, spa, Fd, base in cases:
                cf = B.cap_faces(lab, spa, reach, angle)
                for border, F in Fd.items():
                    shipped = H.ja37_band(lab, spa, border)
                    band = B._drop_near(shipped, cf, spa, H.JA37_BAND_MM)
                    if border == "epi":
                        keep.append(band.sum() / shipped.sum())
                    ref = (F < 0) & (base < 0)
                    for s in (-0.5, -0.3, 0.3, 0.5):
                        test = ((F - s) < 0) & (base < 0)
                        errs.append(H.signed_bias(ref, test, spa, roi=band)
                                    - T._e6_truth(F, s, spa, band)[0])
            cerrs = []
            for lab, spa, cs, tilt, cav_r, sol_r in caps:
                cf = B.cap_faces(lab, spa, reach, angle)
                for border in ("endo", "epi"):
                    band = B._drop_near(H.ja37_band(lab, spa, border), cf, spa, H.JA37_BAND_MM)
                    for s in (-0.5, -0.3, 0.3, 0.5):
                        sh = (s, 0.0) if border == "endo" else (0.0, s)
                        cav_t, sol_t, _, _ = H._open_base_parts(sp, *sh, off, cs, tilt)
                        a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                        cerrs.append(H.signed_bias(a, t, spa, roi=band) - s)
            row = dict(reach_mm=reach, angle_deg=angle,
                       e6_worst=round(float(np.max(np.abs(errs))), 4),
                       capsule_worst=round(float(np.max(np.abs(cerrs))), 4),
                       e6_epi_band_kept_min=round(float(min(keep)), 3))
            print(row, flush=True)
            out.append(row)
    (HERE / "b2_cap_sensitivity.json").write_text(json.dumps(
        {"harness_version": H.HARNESS_VERSION, "rows": out}, indent=1))


if __name__ == "__main__":
    main()
