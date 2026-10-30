"""Golf R3 E8b: the spill share of every presence candidate, measured on the SHARED benchmark (bench_lie, Juliet, #179).

The counterfactual Golf and Kilo asked for on #179: the same heart, seed, motion, scar and noise, with the blood set
to remote (90 HU) so nothing outside the wall is bright, graded inside the SAME carried geometry (the transforms are
registered once, on the real case). Then
    spill share = (sens_full - sens_blood=remote) / sens_full,
per presence rule, blood level and arm (oracle = exact borders, R0, rigid, affine).  The false-call rate is given
both ways too.  Conditions: the benchmark's striking ones (CNR 5; motion 'none' and 'rigid'; every blood level).

Why it is exact: bench.make_case draws everything from its seed and reads the blood level only as a number, so
adding a 'remote' level and passing the real case's seed reproduces the case with only the blood changed (checked
per case: the scar masks and the LIE outside blood voxels must be identical, else the case is dropped).

bench_lie is not in this branch (it is Juliet's PR); pass its folder with --bench.  P-J needs the benchmark's tau,
so it is scored with tau taken from the scar-free segments of the other half of the hearts (bench score.half), here
from the full cases.
Usage: PYTHONPATH=<repo>/src python bench_spill.py <data_dir> --bench <path to bench_lie> [--procs 4]
Writes bench_spill.json (aggregates only).  CPU only.
"""
import argparse, hashlib, json, sys
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
BENCH = None
STRIKE = [(b, 5, m) for b in ("below", "equal", "above") for m in ("none", "rigid")]


def setup(bench_dir):
    global BENCH
    sys.path.insert(0, str(bench_dir))
    import bench  # noqa: F401
    bench.BLOOD["remote"] = bench.REMOTE
    BENCH = bench_dir


def seed_of(hid, blood, cnr, motion):
    return int(hashlib.sha256(f"bench-lie-r3:{hid}:{blood}:{cnr}:{motion}".encode()).hexdigest()[:8], 16)


def one_heart(args):
    hid, data_dir, bench_dir = args
    setup(bench_dir)
    import bench, menu
    h = bench.load_heart(hid, data_dir)          # janusm.guard.refuse inside
    if "skip" in h:
        return {"heart": hid, "skip": h["skip"]}
    geo = menu.fp_geometry(h)
    if geo is None:
        return {"heart": hid, "skip": "AHA failed"}
    rows = []
    for blood, cnr, motion in STRIKE:
        seed = seed_of(hid, blood, cnr, motion)
        c = bench.make_case(h, blood, cnr, motion, seed)
        if "skip" in c:
            continue
        r = bench.make_case(h, "remote", cnr, motion, seed)        # same seed: only the blood level differs
        bl = c["lie"] != r["lie"]
        same = bool((c["scar_t"] == r["scar_t"]).all())
        oracle = {"myo": c["lab_t"] == bench.G.MYO, "cav": c["lab_t"] == bench.G.LV, "seg": c["seg_t"],
                  "u": c["u_t"], "phi": c["phi_t"], "s": c["s_t"]}
        rig = menu.register(c["lie"], c["fp"], geo, "rigid", seed=seed % 1000)
        aff = menu.register(c["lie"], c["fp"], geo, "affine", init=rig, seed=seed % 1000)
        arms = {"oracle": oracle, "R0": menu.carry(geo, menu.identity(geo), c["lie"].shape),
                "rigid": menu.carry(geo, rig, c["lie"].shape), "affine": menu.carry(geo, aff, c["lie"].shape)}
        row = {"blood": blood, "cnr": cnr, "motion": motion, "scar_identical": same,
               "changed_voxel_share": round(float(bl.mean()), 4),
               "truth_vol": np.round(c["truth"]["vol"], 4).tolist(), "truth_depth": np.round(c["truth"]["depth"], 4).tolist(),
               "arms": {}}
        for name, car in arms.items():
            out = {}
            for tag, lie in (("full", c["lie"]), ("nb", r["lie"]), ("free", c["lie_free"]),
                             ("free_nb", r["lie_free"])):
                g = menu.grade(lie, car)
                out[tag] = {k: np.round(np.nan_to_num(np.asarray(g[k], float)), 4).tolist()
                            for k in ("pk_share", "pg_share", "ed")}
            row["arms"][name] = out
        rows.append(row)
        print(hid, blood, motion, "ok", flush=True)
    return {"heart": hid, "rows": rows}


def summarise(res, half):
    out = []
    hearts = [r for r in res if "rows" in r]
    # P-J tau: p99 of ed over scar-free segments of the OTHER half (full and scar-free cases), per blood, arm
    tau = {}
    for hv in (0, 1):
        for blood in ("below", "equal", "above"):
            for arm in ("oracle", "R0", "rigid", "affine"):
                vals = []
                for h in hearts:
                    if half(h["heart"]) == hv:
                        continue
                    for r in h["rows"]:
                        if r["blood"] != blood:
                            continue
                        neg = np.array(r["truth_vol"]) < 0.01
                        vals += list(np.array(r["arms"][arm]["full"]["ed"])[neg]) + r["arms"][arm]["free"]["ed"]
                tau[(hv, blood, arm)] = float(np.percentile(vals, 99)) if vals else np.inf
    for blood in ("below", "equal", "above"):
        for motion in ("none", "rigid", "both"):
            for arm in ("oracle", "R0", "rigid", "affine"):
                acc = {k: np.zeros(6) for k in ("P-K", "P-G", "P-J")}
                for h in hearts:
                    for r in h["rows"]:
                        if r["blood"] != blood or (motion != "both" and r["motion"] != motion) or not r["scar_identical"]:
                            continue
                        t = tau[(half(h["heart"]), blood, arm)]
                        pos = (np.array(r["truth_vol"]) >= 0.01) | (np.array(r["truth_depth"]) >= 0.01)
                        A = r["arms"][arm]
                        call = lambda g: {"P-K": np.array(g["pk_share"]) >= 0.05, "P-G": np.array(g["pg_share"]) >= 0.05,
                                          "P-J": np.array(g["ed"]) >= t}
                        cf, cn, ff, fn = call(A["full"]), call(A["nb"]), call(A["free"]), call(A["free_nb"])
                        for k in acc:
                            acc[k] += [(cf[k] & pos).sum(), (cn[k] & pos).sum(), pos.sum(),
                                       cf[k][~pos].sum() + ff[k].sum(), cn[k][~pos].sum() + fn[k].sum(),
                                       (~pos).sum() + len(ff[k])]
                row = {"blood": blood, "motion": motion, "arm": arm}
                for k, a in acc.items():
                    s_f, s_n = a[0] / max(a[2], 1), a[1] / max(a[2], 1)
                    row[k] = {"sens": round(s_f, 3), "sens_blood_remote": round(s_n, 3),
                              "spill_share": round((s_f - s_n) / s_f, 3) if s_f > 0 else None,
                              "fp_rate": round(a[3] / max(a[5], 1), 4), "fp_rate_blood_remote": round(a[4] / max(a[5], 1), 4),
                              "n_pos": int(a[2]), "n_neg": int(a[5])}
                out.append(row)
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("data_dir")
    ap.add_argument("--bench", required=True)
    ap.add_argument("--procs", type=int, default=4)
    a = ap.parse_args()
    setup(a.bench)
    from fetch import hearts                      # janusm.guard.refuse on the whole list
    import score
    ids = hearts()
    res = []
    with Pool(a.procs) as p:
        for r in p.imap_unordered(one_heart, [(i, a.data_dir, a.bench) for i in ids]):
            res.append(r)
            (Path("/home/user/golf_e8b_partial.json")).write_text(json.dumps(res))
    s = summarise(res, score.half)
    (HERE / "bench_spill.json").write_text(json.dumps({"hearts": len([r for r in res if "rows" in r]),
                                                      "skipped": [r for r in res if "skip" in r],
                                                      "rows": s}, indent=1) + "\n")
    for r in s:
        if r["motion"] == "both" and r["arm"] in ("oracle", "affine"):
            print(r["blood"], r["arm"], {k: (r[k]["sens"], r[k]["spill_share"]) for k in ("P-K", "P-G", "P-J")})
