"""Compare the JA12 guard (``janusm.guard``) with the five Round 1 prototype guards it replaces.

Each prototype is run as committed in ``experiments/JanusM/<advocate>/`` on the inputs it was
written for, and its verdict is set beside the guard's on the same name:

* Golf ``heldout.reason(source, case)``: pool names, TotalSegmentator ids, ImageCAS-X ids;
* Hotel ``coronary_holdout.PoolGuard.reason`` (pool names) and ``held_out_totalseg_ids`` (TS ids);
* India ``fetch_ts_cardiac.pool_subjects`` (TS ids);
* Juliet ``exclusion.is_forbidden(volume, forbidden_patients('strict'))`` (pool names, TS ids);
* Kilo ``heldout.refused_totalseg_ids`` (TS ids) and the refusal steps of
  ``allowed_volumes.main`` (sealed / reserve / D35 / privacy; pool names).

Inputs: every ``<Source>__<case>`` named in the pool list, the QC report, the pool seal and the
Round 10 draw files; every TotalSegmentator id in the pool and in ``tools/ccta/
totalseg_cardiac_ids.json`` (plus every id of the public ``meta.csv`` files if given);
ImageCAS-X ``c0000``..``c0999``.

Every disagreement is listed with the guard's reason; :data:`EXPLAINED` says why each kind is
expected. ``python tools/janusm/compare_prototypes.py [--meta CSV ...] [--out JSON]``
"""

from __future__ import annotations

import argparse
import collections
import csv
import importlib.util
import json
import re
import sys
import types
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from janusm.guard import D35_DRAWS, SEAL_RELPATH, load_guard  # noqa: E402

JM = REPO / "experiments" / "JanusM"
NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*__[A-Za-z0-9_.-]+")
TS = re.compile(r"\bs\d{4}\b")

#: Why a kind of disagreement is expected (keyed by the kind of the guard's reason, or by the
#: prototype rule the guard does not copy).
EXPLAINED = {
    "twin": "JA12/§4 twin rule: the prototypes predate it (none refuses twins).",
    "icx": "A14 sealed 100 / test 160 / val 80: only Golf checked ImageCAS, and only the sealed "
           "100; JA12 adds the test split and val 80.",
    "plos": "PLOS-Peng2016: JA12/JA5; only Kilo refused it.",
    "d35": "Round 10 D35 draws: the guard reads all five draw files (every list except those "
           "marked trainable); Golf's glob missed Crucible's and Foxtrot's files, Hotel read only "
           "each file's drawn list, Kilo omitted Foxtrot.",
    "proto_draw_text": "Golf reads every name anywhere in a draw file, including lists the draw "
                       "marks as trainable (Atlas 'trainable_before_extension_decision', drawn "
                       "by no other draw); the guard leaves those out (NOT_HELD_OUT_KEYS).",
    "proto_pool_wide": "Not seen today: Kilo's and India's TotalSegmentator lists read the whole "
                       "pool list, the guard only held-out patients (JA5 lets the rest in). All "
                       "16 pool TotalSegmentator subjects are held out now, so they agree.",
}


def _load(path: Path, name: str):
    sys.path.insert(0, str(path.parent))
    try:
        spec = importlib.util.spec_from_file_location(name, path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(path.parent))


def _kind(reason: str) -> str:
    r = reason or ""
    for key, word in (("twin", "twin"), ("plos", "PLOS"), ("icx", "ImageCAS-X"),
                      ("d35", "D35"), ("reserve", "reserve"), ("seal", "seal")):
        if word in r:
            return key
    return "other"


def universe(meta_paths=()):
    pool = set()
    qc = "vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv"
    for rel in ["configs/segqueue14/pool-2026-10.txt", SEAL_RELPATH, *D35_DRAWS, qc]:
        pool |= {n[: -len(".nii.gz")] if n.endswith(".nii.gz") else n
                 for n in NAME.findall((REPO / rel).read_text(encoding="utf-8"))}
    pool = {n for n in pool if not n.startswith("TotalSegmentator")}
    ts = set(TS.findall((REPO / "configs/segqueue14/pool-2026-10.txt").read_text()))
    ts |= set(TS.findall((REPO / "tools/ccta/totalseg_cardiac_ids.json").read_text()))
    for p in meta_paths:
        rows = csv.DictReader(Path(p).read_text(encoding="utf-8-sig").splitlines(), delimiter=";")
        ts |= {r["image_id"].strip() for r in rows}
    icx = {f"c{i:04d}" for i in range(1000)}
    return sorted(pool), sorted(ts), sorted(icx)


def prototypes():
    """{advocate: {domain: callable(name) -> refused?}}, each prototype's own code."""
    out = {}
    golf = _load(JM / "Golf/heldout.py", "golf_heldout")
    out["Golf"] = {
        "pool": lambda n: bool(golf.reason(*n.split("__", 1))),
        "ts": lambda s: bool(golf.reason("TotalSegmentator-cardiac", s)),
        "icx": lambda c: bool(golf.reason("ImageCAS", c)),
    }
    hotel = _load(JM / "Hotel/coronary_holdout.py", "hotel_holdout")
    hg, hts = hotel.PoolGuard(), hotel.held_out_totalseg_ids()
    out["Hotel"] = {"pool": lambda n: bool(hg.reason(n)), "ts": lambda s: s in hts}
    if "remotezip" not in sys.modules:   # India imports it at the top; pool_subjects() needs none
        sys.modules["remotezip"] = types.SimpleNamespace(RemoteZip=None)
    india = _load(JM / "India/fetch_ts_cardiac.py", "india_fetch")
    its = india.pool_subjects()
    out["India"] = {"ts": lambda s: s in its}
    jul = _load(JM / "Juliet/exclusion.py", "juliet_exclusion")
    jf = jul.forbidden_patients("strict")
    out["Juliet"] = {
        "pool": lambda n: jul.is_forbidden(n + ".nii.gz", jf),
        "ts": lambda s: jul.is_forbidden(f"TotalSegmentator-cardiac__{s}.nii.gz", jf),
    }
    kilo = _load(JM / "Kilo/heldout.py", "kilo_heldout")
    kts = kilo.refused_totalseg_ids()
    kav = _load(JM / "Kilo/allowed_volumes.py", "kilo_allowed")
    kseal = kav.load_pool_seal(kav.SEAL)
    raw = json.loads(Path(kav.SEAL).read_text())
    kres = {kav.ingest_patient(p) or p for p in raw["primary"]["extension_order"]}
    kd35 = set()
    for path, get in kav.DRAWS.values():
        kd35 |= {kav.ingest_patient(p) or p for p in get(json.loads((REPO / path).read_text()))}

    def kilo_pool(n):  # allowed_volumes.main's refusal steps, in its order
        pat = kav.ingest_patient(n)
        return (kseal.is_sealed(n) or pat in kres or pat in kd35
                or n.split("__")[0] in kav.PRIVACY)

    out["Kilo"] = {"pool": kilo_pool, "ts": lambda s: s in kts}
    return out


def compare(meta_paths=()):
    g = load_guard()
    pool, ts, icx = universe(meta_paths)
    inputs = {"pool": pool, "ts": ts, "icx": icx}
    guard = {
        "pool": {n: g.reason(n) for n in pool},
        "ts": {s: g.reason(s, source="TotalSegmentator") for s in ts},
        "icx": {c: g.reason(c, source="ImageCAS-X") for c in icx},
    }
    report = {"guard": g.summary(), "inputs": {k: len(v) for k, v in inputs.items()},
              "explained": EXPLAINED, "prototypes": {}}
    for adv, doms in prototypes().items():
        rep = {}
        for dom, fn in doms.items():
            proto_only, guard_only, same = [], collections.defaultdict(list), 0
            for x in inputs[dom]:
                p, r = bool(fn(x)), guard[dom][x]
                if p == bool(r):
                    same += 1
                elif r:
                    guard_only[_kind(r)].append(x)
                else:
                    proto_only.append(x)
            rep[dom] = {"n": len(inputs[dom]), "same": same,
                        "guard_stricter": {k: {"n": len(v), "e.g.": v[:5]}
                                           for k, v in sorted(guard_only.items())},
                        "prototype_stricter": proto_only}
        report["prototypes"][adv] = rep
    return report


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--meta", nargs="*", default=(), help="public TotalSegmentator meta.csv files")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    rep = compare(a.meta)
    text = json.dumps(rep, indent=1, ensure_ascii=False) + "\n"
    if a.out:
        a.out.write_text(text, encoding="utf-8")
    for adv, doms in rep["prototypes"].items():
        for dom, d in doms.items():
            print(f"{adv:6s} {dom:4s} n={d['n']:5d} same={d['same']:5d} guard_stricter="
                  f"{ {k: v['n'] for k, v in d['guard_stricter'].items()} } "
                  f"prototype_stricter={len(d['prototype_stricter'])} "
                  f"{d['prototype_stricter'][:6]}")


if __name__ == "__main__":
    main()
