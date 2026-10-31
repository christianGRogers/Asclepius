"""Kilo R4 K1 (#251 item 2; #243): the affine acceptance candidates on the shipped tests' own static-chest phantom.

The PS3-S3 xfail (``tests/test_janusm_scar_registration.py``) uses this phantom, its "tight" cuts (1.2 x the aligned
phantom's QC values, floor 0.003) and the shipped ``register_lie``. Here every stage is forced (cuts -1) so rigid and
affine both exist, then each acceptance rule (JA51 4(b) as shipped; #243's (a), (b), (c); Kilo's (k); definitions in
``score_shipped.py``, pre-registered on #251) is applied with the tight cuts. Motions: 3 % isotropic scale
both ways (the xfail's case and its mirror), Golf's 6 % uniaxial scale, and the rigid-only 4 mm shift where affine
must be rejected (the PS3-S3 companion test). Several noise seeds per motion.

Phantom only: nothing is downloaded, no case is opened, no image is written.
Usage: PYTHONPATH=src:tests python experiments/JanusM/Kilo/r4/k1_phantom_rules.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "tests"))
sys.path.insert(0, str(ROOT / "experiments/JanusM/bench_lie"))
sys.path.insert(0, str(HERE))
import janusm_synth as Y  # noqa: E402
from janusm import geometry as G  # noqa: E402
from janusm.scar import registration as R  # noqa: E402
from score_shipped import RULES, accept  # noqa: E402

FAST = dict(n_samples=10_000, maxfev=600)
FORCE = R.QCCuts(-1.0, -1.0, -1.0, -1.0)


def main():
    ph = Y.StaticChest(gap_mm=5.0)
    geo = G.analyse(ph.labels, affine=ph.affine)
    ph.first = R.prepare_first_pass(ph.first_pass, ph.labels, ph.affine, geometry=geo)
    r0 = R.carry(ph.first, R.Transform(np.eye(3), np.zeros(3), ph.first.centre), ph.first_pass.shape, ph.affine)
    aligned_qc = R.qc(ph.lie(), r0)
    cut = np.maximum(aligned_qc.values() * 1.2, 0.003)

    def tre(T, motion):
        p = ph.first.myo_world
        return float(np.linalg.norm(T.inverse(p) - ph.true_lie_points(motion, p), axis=1).mean())

    motions = {"scale_+3": lambda s: ph.scale(1.03), "scale_-3": lambda s: ph.scale(0.97),
               "shift_4mm": lambda s: ph.shift(4.0, seed=11 + s)}

    def uniaxial(f, seed):
        n = np.random.default_rng(seed).normal(0, 1, 3)
        n /= np.linalg.norm(n)
        return np.linalg.inv(np.eye(3) + f * np.outer(n, n)), np.zeros(3)   # the phantom's scale() convention

    motions["uniaxial_+6"] = lambda s: uniaxial(0.06, 40 + s)
    rows = []
    for name, mk in motions.items():
        for s in range(3):
            motion = mk(s)
            lie = ph.lie(motion, seed=100 + s)
            reg = R.register_lie(ph.first, lie, ph.affine, FORCE, seed=s, **FAST)
            st = {x.name: x for x in reg.stages}
            a, r = st["affine"], st["rigid"]
            san = R.affine_sanity(a.transform.matrix)
            row = {"motion": name, "seed": s, "tre_rigid": round(tre(r.transform, motion), 3),
                   "tre_affine": round(tre(a.transform, motion), 3), "log_det": round(san["log_det"], 4),
                   "sanity_ok": san["ok"],
                   "rigid_norm": np.round(r.qc.values() / cut, 3).tolist(),
                   "affine_norm": np.round(a.qc.values() / cut, 3).tolist()}
            for rule in RULES:
                row[rule] = accept(rule, a.qc.values(), r.qc.values(), cut, san["ok"], san["log_det"])
            rows.append(row)
            print(json.dumps(row), flush=True)
    better = [r for r in rows if r["tre_affine"] < r["tre_rigid"] - 0.25]
    worse = [r for r in rows if r["tre_affine"] > r["tre_rigid"] + 0.25]
    summ = {rule: {"kept_when_better": f"{sum(r[rule] for r in better)}/{len(better)}",
                   "kept_when_worse": f"{sum(r[rule] for r in worse)}/{len(worse)}"} for rule in RULES}
    out = {"phantom": "tests/janusm_synth.StaticChest(gap_mm=5)", "cuts": "tight: max(1.2 x aligned QC, 0.003)",
           "cut_values": np.round(cut, 4).tolist(), "aligned_qc": np.round(aligned_qc.values(), 4).tolist(),
           "rows": rows, "summary": summ}
    (HERE / "k1_phantom_rules.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summ, indent=1))


if __name__ == "__main__":
    main()
