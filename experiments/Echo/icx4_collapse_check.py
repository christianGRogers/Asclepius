"""Echo (#49): does every 14 -> 4 collapse in the repo match D25, and do they agree with each other?

Checks, CPU only, no data needed:
  1. the five copies of the ImageCAS-X -> 4 table give the same class for values 1..13;
  2. each copy's handling of "Other" (14);
  3. how often the voxel-index "nearest" (segtrain.reads.icx_to_territory) and the mm
     "nearest" (trillium/icx4/lib/territory.py, what icx4 trains on) disagree on
     synthetic trees at ImageCAS spacing (0.35, 0.35, 0.5 mm).

Run from the repo root:  python experiments/Echo/icx4_collapse_check.py
"""
import importlib.util
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from segqueue14 import labels  # noqa: E402
from segtrain import namer, proxy, reads  # noqa: E402

spec = importlib.util.spec_from_file_location("territory", ROOT / "trillium/icx4/lib/territory.py")
territory = importlib.util.module_from_spec(spec)
spec.loader.exec_module(territory)

# D25 as written, value by value (ImageCAS-X Suppl. Table 4 numbering).
NAMES = ["LM", "LAD", "LCx", "D1", "D2", "OM1", "OM2", "IM", "RCA", "R-PDA", "R-PLA", "L-PDA", "L-PLA"]
D25 = {"LM": 1, "LAD": 2, "D1": 2, "D2": 2,
       "LCx": 3, "OM1": 3, "OM2": 3, "IM": 3, "L-PDA": 3, "L-PLA": 3,
       "RCA": 4, "R-PDA": 4, "R-PLA": 4}

copies = {
    "segqueue14.labels.ICX14_TO_4": lambda v: labels.ICX14_TO_4.get(v, 0),
    "segtrain.reads.icx_to_territory": lambda v: int(reads.icx_to_territory(np.array([v]))[0]),
    "segtrain.proxy.ICX_TO_4": lambda v: proxy.ICX_TO_4.get(v, 0),
    "segtrain.namer.icx_to_four": lambda v: int(namer.icx_to_four(np.array([v]))[0]),
    "trillium/icx4 territory.to_four": lambda v: int(territory.to_four(np.array([v]), (1, 1, 1))[0]),
}

print("1. Values 1..13 against D25")
bad = 0
for value, name in enumerate(NAMES, start=1):
    got = {k: f(value) for k, f in copies.items()}
    ok = all(g == D25[name] for g in got.values())
    bad += not ok
    print(f"   {value:2d} {name:6s} -> {D25[name]}  {'ok' if ok else 'MISMATCH ' + str(got)}")
print(f"   mismatches: {bad}")

print("2. 'Other' (14) on its own, with no LAD/LCx in the volume")
for k, f in copies.items():
    print(f"   {k:34s} -> {f(14)}")

print("3. Other resolved by voxel index vs by mm, ImageCAS spacing (0.35, 0.35, 0.5)")
sp = (0.35, 0.35, 0.5)
rng = np.random.default_rng(0)
flips = others = cases_with_flip = 0
N = 200
for _ in range(N):
    vol = np.zeros((40, 40, 40), np.int64)
    # An LAD and an LCx segment, and an "Other" blob somewhere between them.
    a = rng.integers(5, 35, 3)
    b = rng.integers(5, 35, 3)
    for t in np.linspace(0, 1, 60):
        p = np.round(a + t * (b - a) * 0.4).astype(int)
        q = np.round(b + t * (a - b) * 0.4).astype(int)
        vol[tuple(p)] = 2
        vol[tuple(q)] = 6  # OM1 -> LCx
    c = np.round((a + b) / 2 + rng.normal(0, 3, 3)).clip(2, 37).astype(int)
    blob = vol[c[0] - 2:c[0] + 3, c[1] - 2:c[1] + 3, c[2] - 2:c[2] + 3]
    blob[blob == 0] = 14
    mm = territory.to_four(vol, sp)
    vx = reads.icx_to_territory(vol)
    o = vol == 14
    f = int((mm[o] != vx[o]).sum())
    flips += f
    others += int(o.sum())
    cases_with_flip += f > 0
print(f"   {N} synthetic cases, Other placed between LAD and LCx (worst case):")
print(f"   Other voxels whose class differs: {flips}/{others} = {flips / max(others, 1):.2%}; "
      f"cases with any difference: {cases_with_flip}/{N}")
