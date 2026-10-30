"""Module parity (Janus-M Round 3, path jm/paired-scar, PS3-S7, JA54): the shipped Scar-0 against the benchmark.

The shared benchmark (``menu.grade``) decided the Scar-0 menu (JA54). This ties the shipped module
(``janusm.scar.scar0``) to it: on the same LIE image and the same **oracle** geometry (the truth on the LIE grid,
which isolates the rule from registration), both grade every segment, and the per-segment ``ev`` (E-V share),
``ed`` (E-D extent) and ``pg_share`` (P-G share) must agree within ``TOL`` (0.02).

Conditions: the striking ones pre-registered on #179 (CNR 5; motion none or rigid; every blood level).

- CI (``tests/test_janusm_scar0_menu.py``) runs :func:`parity` on the bench_lie **phantom** heart only. Nothing is
  downloaded.
- Offline (Round 4 advocates): this script on the benchmark hearts. The JA12 guard runs on the whole heart list
  first (``fetch.hearts``), and again per heart in ``bench.load_heart``. It writes ``module_parity.json`` (summary
  numbers only: no images, no case ids beyond the public benchmark heart names already in the repository).

Usage (offline): PYTHONPATH=src python experiments/JanusM/bench_lie/module_parity.py <data_dir> [--hearts a,b] [--out f]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(HERE))
import bench  # noqa: E402
from janusm.scar import PASSED  # noqa: E402
from janusm.scar import scar0 as S  # noqa: E402
from janusm.scar.common import CarriedGeometry  # noqa: E402
from janusm.scar.registration import COLUMN_DEG, COLUMN_MM  # noqa: E402

#: PS3-S7: per-segment agreement required between the benchmark and the module.
TOL = 0.02
#: The striking conditions pre-registered on #179: CNR 5, motion none or rigid, any blood level.
STRIKING = [(b, 5, m) for b in bench.BLOOD for m in ("none", "rigid")]
KEYS = ("ev", "ed", "pg_share")


def _menu():
    # menu.py imports SimpleITK at the top for its registration; grade() is numpy and scipy only. Without
    # SimpleITK, a stub stands in for the import alone and is removed at once, so nothing else (an importorskip
    # elsewhere in the test run) ever sees it.
    if "menu" in sys.modules:
        return sys.modules["menu"]
    try:
        import SimpleITK  # noqa: F401
    except ImportError:
        import types

        stub = types.ModuleType("SimpleITK")
        stub.__getattr__ = lambda name: None
        sys.modules["SimpleITK"] = stub
        try:
            import menu
        finally:
            if sys.modules.get("SimpleITK") is stub:
                del sys.modules["SimpleITK"]
        return menu
    import menu

    return menu


def seed_of(hid: str, blood: str, cnr: int, motion: str) -> int:
    """The benchmark's own seed (run.py), so a case here is the case scored in results.jsonl."""
    return int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)


def oracle_geometry(case) -> CarriedGeometry:
    """The truth geometry on the LIE grid (run.py's ``oracle`` arm) as the module takes it. The E-D column id is
    the module's own (``registration._columns``: 3 degrees x 2 mm), from the benchmark's angle and position."""
    myo = case["lab_t"] == bench.G.MYO
    seg = np.where(myo, case["seg_t"], 0).astype(np.int16)
    col = np.full(myo.shape, -1, np.int64)
    ia = np.floor(case["phi_t"][myo] / COLUMN_DEG).astype(np.int64)
    js = np.floor(case["s_t"][myo] / COLUMN_MM).astype(np.int64) + 100_000
    col[myo] = ia * 1_000_000 + js
    u = np.where(myo, case["u_t"], np.nan).astype(np.float32)
    return CarriedGeometry(myo=myo, cavity=case["lab_t"] == bench.G.LV, segments=seg, u=u, column=col,
                           spacing=np.full(3, bench.V), affine=bench.A_RAS)


def module_values(lie, car: CarriedGeometry) -> dict:
    out = S.scar0(lie, car, status=PASSED)
    v = {k: np.full(17, np.nan) for k in KEYS}
    for s, row in out.segments.items():
        if not row["graded"]:
            continue
        v["ev"][s - 1] = row["share_ev"]
        v["ed"][s - 1] = row["extent_ed"]
        v["pg_share"][s - 1] = row["share_pg"]
    return v


def compare(bench_v: dict, mod_v: dict) -> dict:
    """Per key: segments compared (both finite), segments finite on one side only, max |difference|."""
    res = {}
    for k in KEYS:
        a, b = np.asarray(bench_v[k], float), np.asarray(mod_v[k], float)
        both = np.isfinite(a) & np.isfinite(b)
        d = np.abs(a[both] - b[both])
        res[k] = {"n": int(both.sum()), "n_one_sided": int((np.isfinite(a) ^ np.isfinite(b)).sum()),
                  "max_abs_diff": float(d.max()) if d.size else None,
                  "segments_over_tol": [int(i) + 1 for i in np.flatnonzero(both)[d > TOL]]}
    return res


def parity(heart: dict, conds=STRIKING, *, image: str = "lie") -> list:
    """Grade every condition's case with ``menu.grade`` and with ``scar0`` on the oracle geometry."""
    menu = _menu()
    rows = []
    for blood, cnr, motion in conds:
        seed = seed_of(heart["id"], blood, cnr, motion)
        case = bench.make_case(heart, blood, cnr, motion, seed)
        if "skip" in case:
            rows.append({"heart": heart["id"], "blood": blood, "cnr": cnr, "motion": motion, "skip": case["skip"]})
            continue
        car = oracle_geometry(case)
        oracle = {"myo": car.myo, "cav": car.cavity, "seg": case["seg_t"], "u": case["u_t"],
                  "phi": case["phi_t"], "s": case["s_t"]}
        g = menu.grade(case[image], oracle)
        res = compare({k: g[k] for k in KEYS}, module_values(case[image], car))
        rows.append({"heart": heart["id"], "blood": blood, "cnr": cnr, "motion": motion, "seed": seed,
                     "parity": res, "pass": all(r["max_abs_diff"] is None or r["max_abs_diff"] <= TOL
                                                for r in res.values())})
    return rows


def summary(rows: list) -> dict:
    done = [r for r in rows if "parity" in r]
    out = {"tol": TOL, "conditions": "CNR 5; motion none, rigid; blood below, equal, above (oracle geometry)",
           "n_cases": len(done), "n_skipped": len(rows) - len(done),
           "n_pass": sum(r["pass"] for r in done), "scar_version": S.SCAR_VERSION}
    for k in KEYS:
        m = [r["parity"][k]["max_abs_diff"] for r in done if r["parity"][k]["max_abs_diff"] is not None]
        out[f"max_abs_diff_{k}"] = max(m) if m else None
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("data_dir")
    ap.add_argument("--hearts", help="comma-separated subset of the benchmark list")
    ap.add_argument("--out", default=str(HERE / "module_parity.json"))
    a = ap.parse_args()
    from fetch import hearts as heart_list

    ids = heart_list()                                   # JA12 guard on the whole list, before anything is read
    if a.hearts:
        ids = [i for i in a.hearts.split(",") if i in ids]
    rows = []
    for hid in ids:
        h = bench.load_heart(hid, Path(a.data_dir))     # guard again, per heart
        if "skip" in h:
            rows.append({"heart": hid, "skip": h["skip"]})
            continue
        rows += parity(h)
        print(hid, [r.get("pass") for r in rows if r["heart"] == hid], flush=True)
    Path(a.out).write_text(json.dumps({"summary": summary(rows), "cases": rows}, indent=1) + "\n")
    print(json.dumps(summary(rows), indent=1))


if __name__ == "__main__":
    main()
