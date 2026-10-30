"""Lima R5 E2: the four bands of E1 on the harness's LA-capped heart (issue #223 item 2, control).

``janusm.harness.phantom`` opens the pool into the LA (label 4) at the base, with an RV over the
septum, and background (label 0) everywhere else, as on a read. The walls move by exactly the
shift; the base plane does not move. So the truth is the shift itself.

Two grids x three walls (uniform; varying; varying and oblique) x two sub-voxel offsets x both
borders x +-0.3 / +-0.5 mm, for each band of E1 (``e1_open_base_remedy.band_variant``).
Phantoms only; no case is opened.

    python experiments/JanusM/Lima/r5/e2_la_capped_heart.py experiments/JanusM/Lima/r5/e2_la_capped_heart.json
"""
import importlib.util
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
sys.path.insert(0, str(REPO / "src"))

from janusm import guard  # noqa: E402
from janusm import harness as H  # noqa: E402

spec = importlib.util.spec_from_file_location("e1", HERE / "e1_open_base_remedy.py")
E1 = importlib.util.module_from_spec(spec)
spec.loader.exec_module(E1)

GRIDS = ((0.5, 0.5, 0.5), (0.4, 0.4, 0.5))
SHAPES = ((0.0, 0.0), (2.3, 0.0), (2.3, 23.0))
OFFSETS = ((0.1, 0.2, 0.3), (0.37, 0.05, 0.21))


def main(out):
    guard.refuse([], what="Lima R5 E2 (phantoms; no case is opened)")
    rows = []
    for grid in GRIDS:
        for cs, tilt in SHAPES:
            for off in OFFSETS:
                lab, aff = H.phantom(grid, origin_offset_mm=off, cavity_shift_mm=cs, tilt_deg=tilt)
                sp = np.linalg.norm(aff[:3, :3], axis=0)
                cav_r, sol_r = H.borders(lab)
                for border in ("endo", "epi"):
                    bands = {v: E1.band_variant(lab, sp, border, v) for v in E1.VARIANTS}
                    for size in (0.3, 0.5):
                        for sign in (1.0, -1.0):
                            b = sign * size
                            sh = dict(endo_shift_mm=b) if border == "endo" else dict(epi_shift_mm=b)
                            lt, _ = H.phantom(grid, origin_offset_mm=off, cavity_shift_mm=cs,
                                              tilt_deg=tilt, **sh)
                            cav_t, sol_t = H.borders(lt)
                            a, t = (cav_r, cav_t) if border == "endo" else (sol_r, sol_t)
                            for v, band in bands.items():
                                est = H.signed_bias(a, t, sp, roi=band) if band.any() else float("nan")
                                rows.append(dict(grid=list(grid), cs=cs, tilt=tilt, off=list(off),
                                                 border=border, true_mm=b, variant=v,
                                                 band_vox=int(band.sum()),
                                                 err=None if not np.isfinite(est) else float(est - b)))
                print(grid, cs, tilt, off, flush=True)
    summ = {}
    for v in E1.VARIANTS:
        for border in ("endo", "epi"):
            sel = [r for r in rows if r["variant"] == v and r["border"] == border]
            e = [abs(r["err"]) for r in sel if r["err"] is not None]
            summ[f"{v}/{border}"] = dict(n=len(sel), n_nan=len(sel) - len(e),
                                         worst_abs_err=max(e) if e else None,
                                         mean_band_vox=float(np.mean([r["band_vox"] for r in sel])),
                                         pass_005=bool(e) and len(e) == len(sel) and max(e) <= 0.05)
    Path(out).write_text(json.dumps({"harness_version": H.HARNESS_VERSION, "summary": summ,
                                     "rows": rows}, indent=1))
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main(sys.argv[1])
