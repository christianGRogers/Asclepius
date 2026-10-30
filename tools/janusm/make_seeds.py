"""Janus-M read seeds on Fir (JA7, JA10): the lead runs this; nobody else does.

For each of the 100 frozen Janus-M read cases (60 seal + 40 decision, from the JA6
freeze file), run TotalSegmentator ``heartchambers_highres`` on the CT if its output
is not there yet, then write ``<case>.janusm-seed.nii.gz``: the JA1 labels coarsened
to 2 mm and smoothed (``janusm_reads.seeds``), on the CT's grid.

Seeds are written for the 10 blank cases too: they are never served to a reader,
but the anchoring report compares blank reads with them.

Refuses the whole run, before touching any file, if any case is a coronary hold-out
(``janusm_reads.holdout``, the JA12 guard's adapter). Prints one aggregate JSON line
and nothing per case; send back only that.

Usage (from the repository root; see docs/JANUSM-READ-PROTOCOL.md section 5)::

    python tools/janusm/make_seeds.py --freeze configs/janusm/sealed-r1.json \\
        --layout $SCRATCH/icx4/layout.json --totalseg-dir $SCRATCH/janusm/hc \\
        --out $SCRATCH/janusm/seeds [--run-totalseg]
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))

from janusm_reads import holdout, readset, seeds  # noqa: E402

SEED_SUFFIX = ".janusm-seed.nii.gz"


def ct_paths(layout_path: Path) -> dict:
    """``{case: ct path}`` from the icx4 layout file (``{"cases": {c: {"ct": ...}}}``)."""
    data = json.loads(Path(layout_path).read_text())
    return {c: v["ct"] for c, v in data["cases"].items()}


def totalseg_command(ct: str, out: Path) -> list:
    return ["TotalSegmentator", "-i", ct, "-o", str(out), "-ta", "heartchambers_highres",
            "--ml", "-d", "gpu", "-q"]


def one(case: str, ct_path: str, ts_dir: Path, out_dir: Path, run_totalseg: bool) -> dict:
    import nibabel as nib
    import numpy as np

    ts_path = ts_dir / f"{case}.nii.gz"
    if not ts_path.exists():
        if not run_totalseg:
            return {"case": case, "ok": False, "reason": "no heartchambers_highres output"}
        subprocess.run(totalseg_command(ct_path, ts_path), check=True)
    ct = nib.load(ct_path)
    ts = nib.load(str(ts_path))
    if ts.shape[:3] != ct.shape[:3] or not np.allclose(ts.affine, ct.affine, atol=1e-3):
        return {"case": case, "ok": False, "reason": "TotalSegmentator output not on the CT grid"}
    seed = seeds.make_seed(np.asarray(ts.dataobj).astype(np.int16), ct.header.get_zooms()[:3])
    img = nib.Nifti1Image(seed, ct.affine)
    img.set_data_dtype(np.uint8)
    nib.save(img, str(out_dir / f"{case}{SEED_SUFFIX}"))
    counts = np.bincount(seed.ravel(), minlength=5)[1:5]
    return {"case": case, "ok": bool((counts > 0).all()), "counts": counts.tolist(),
            "reason": "" if (counts > 0).all() else "a class is empty after coarsening"}


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    p.add_argument("--freeze", required=True, help="the JA6 freeze file (sealed-r1.json)")
    p.add_argument("--layout", required=True, help="icx4 layout.json (case -> CT path)")
    p.add_argument("--totalseg-dir", required=True, type=Path)
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--run-totalseg", action="store_true",
                   help="run TotalSegmentator for cases with no output yet (needs the GPU)")
    p.add_argument("--dry-run", action="store_true",
                   help="check the freeze file, the guard and the layout; write nothing")
    args = p.parse_args(argv)

    sets = readset.load_freeze(args.freeze)
    cases = sets[readset.DECISION] + sets[readset.SEAL]
    holdout.refuse(cases, what="the Janus-M seed job")  # JA12: first, before any file
    cts = ct_paths(args.layout)
    missing = [c for c in cases if c not in cts]
    if missing:
        sys.exit(f"REFUSED: {len(missing)} cases are not in the layout: {missing[:5]}")
    if args.dry_run:
        print(json.dumps({"cases": len(cases), "decision": len(sets[readset.DECISION]),
                          "seal": len(sets[readset.SEAL]),
                          "blank_cases": len(readset.blank_cases(sets[readset.SEAL])),
                          "holdouts": 0, "dry_run": True}, sort_keys=True))
        return 0
    args.totalseg_dir.mkdir(parents=True, exist_ok=True)
    args.out.mkdir(parents=True, exist_ok=True)
    rows = [one(c, cts[c], args.totalseg_dir, args.out, args.run_totalseg) for c in cases]
    bad = [r for r in rows if not r["ok"]]
    print(json.dumps({
        "cases": len(rows), "seeds_ok": len(rows) - len(bad),
        "blank_cases": len(readset.blank_cases(sets[readset.SEAL])),
        "failed": [{"case": r["case"], "reason": r["reason"]} for r in bad],
        "coarse_mm": seeds.COARSE_MM, "smooth_mm": seeds.SMOOTH_MM,
    }, sort_keys=True))
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
