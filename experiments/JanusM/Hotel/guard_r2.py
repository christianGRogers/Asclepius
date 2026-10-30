"""Hotel's Round 2 held-out guard for Janus-M: every JA12 category, until the shared guard (#138) lands.

Every Hotel v2 script calls this before it opens any case. It refuses, and a refusal stops the whole run:

* the D27/D32/D33 pool seal (primary and report-only), by patient (``segtrain.pool_seal``);
* the A34 reserve (the seal's extension order);
* every Round 10 D35 draw, by any advocate (glob over ``experiments/*/r10*/``);
* every volume on the pool list itself (wider than JA12 requires: the pool is the coronary model's);
* the A14 sealed 100, the ImageCAS-X test split (sealed 80, open 36, dev 44) and val 80;
* PLOS-Peng2016, by source;
* every TotalSegmentator s-number named in any of the above, and every TotalSegmentator **twin** of one
  (Round 1 ruling §4): a public subject with the same sex and institute as a held-out subject, age within
  +-5 years, any study type.

Standard library only. Run from anywhere; paths resolve from the repository root.

    python experiments/JanusM/Hotel/guard_r2.py                # print the refused counts
    python experiments/JanusM/Hotel/guard_r2.py --meta V1_META --meta V2_META   # + twin rule (union)
"""
from __future__ import annotations

import csv
import glob
import hashlib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from segtrain.pool_seal import _stem, ingest_patient, load_pool_seal  # noqa: E402

POOL_LIST = "configs/segqueue14/pool-2026-10.txt"
SEAL_FILE = "configs/segqueue14/sealed-pool-2026-10.json"
A14_FILE = "trillium/icx4/sealed_test.json"
SPLITS = "trillium-results/icx14/results/splits.json"
SPLITS_SHA256_PREFIX = "a53bd426cddc"  # JA6
D35_GLOBS = ["experiments/*/r10*/*decision_set*proposal*.json", "experiments/*/r10*/*d35*proposal*.json"]
REFUSED_SOURCES = {"PLOS-Peng2016"}
TS_ID = re.compile(r"TotalSegmentator[A-Za-z_-]*__(s\d{4})")
TWIN_AGE_YEARS = 5
MIN_TS_IDS = 16  # the pool list alone names 16; fewer means a file went missing


class HeldOut(RuntimeError):
    """A held-out case was asked for. The caller must stop, not skip."""


def _strings(x):
    if isinstance(x, str):
        yield x
    elif isinstance(x, dict):
        for k, v in x.items():
            yield k
            yield from _strings(v)
    elif isinstance(x, list):
        for v in x:
            yield from _strings(v)


class Guard:
    def __init__(self, ts_meta=None):
        """ts_meta: a TotalSegmentator meta.csv path, or a list of them (v1 and v2.0.1); twins are the union."""
        self.seal = load_pool_seal()  # checks the pinned sha256
        self.reserve = {e for e in self.seal.extension_order if isinstance(e, str)}
        self.d35_files = sorted({f for g in D35_GLOBS for f in glob.glob(str(ROOT / g))})
        if len(self.d35_files) < 5:
            raise HeldOut(f"only {len(self.d35_files)} Round 10 D35 files found; refusing to run")
        self.d35 = set()
        for f in self.d35_files:
            d = json.loads(Path(f).read_text())
            self.d35 |= set(_strings(d))
        self.pool = {ln.strip() for ln in (ROOT / POOL_LIST).read_text().splitlines() if ln.strip()}
        self.pool_stems = {_stem(v) for v in self.pool}
        self.pool_patients = {ingest_patient(_stem(v)) for v in self.pool}

        a14 = json.loads((ROOT / A14_FILE).read_text())
        raw = (ROOT / SPLITS).read_bytes()
        if not hashlib.sha256(raw).hexdigest().startswith(SPLITS_SHA256_PREFIX):
            raise HeldOut("splits.json hash differs from JA6's a53bd426cddc; refusing to run")
        splits = json.loads(raw)
        self.imagecas = (set(a14["sealed_icx_test"]) | set(a14["open_icx_test"]) | set(a14["sealed_quality0"])
                         | set(a14["excluded_dev_cases_in_test"]) | set(splits["test"]) | set(splits["val"]))
        self.imagecas_train = set(splits["train"])
        assert not (self.imagecas & self.imagecas_train), "a held-out ImageCAS case is in the train list"

        text = "".join(Path(ROOT / f).read_text() for f in [POOL_LIST, SEAL_FILE]) + "".join(
            Path(f).read_text() for f in self.d35_files)
        self.ts_ids = set(TS_ID.findall(text))
        if len(self.ts_ids) < MIN_TS_IDS:
            raise HeldOut(f"only {len(self.ts_ids)} held-out TotalSegmentator ids; refusing to run")
        self.ts_twins: dict[str, str] = {}
        for m in ([ts_meta] if isinstance(ts_meta, str) else (ts_meta or [])):
            for t, h in twins(m, self.ts_ids).items():
                self.ts_twins.setdefault(t, h)

    # --- pool volumes -------------------------------------------------------------------------
    def pool_reason(self, name: str) -> str | None:
        stem = _stem(name)
        pat = ingest_patient(stem)
        if any(stem.startswith(s + "__") for s in REFUSED_SOURCES):
            return "PLOS-Peng2016 (burned-in text)"
        if self.seal.is_sealed(name) or pat in self.seal.patients:
            return "coronary pool seal (D27/D32/D33)"
        if pat in self.reserve:
            return "seal reserve (A34)"
        if pat in self.d35 or stem in self.d35 or name in self.d35:
            return "a Round 10 D35 draw"
        if stem in self.pool_stems or pat in self.pool_patients:
            return "on the coronary pool list"
        m = TS_ID.search(name)
        if m and m.group(1) in self.ts_ids | set(self.ts_twins):
            return "held-out TotalSegmentator subject or twin"
        return None

    # --- ImageCAS(-X) -------------------------------------------------------------------------
    def imagecas_reason(self, case: str) -> str | None:
        if case in self.imagecas:
            return "A14 seal / ImageCAS-X test split / val 80"
        if case not in self.imagecas_train:
            return "not in the ImageCAS-X train list (not allowed by JA5)"
        return None

    # --- public TotalSegmentator --------------------------------------------------------------
    def ts_reason(self, sid: str) -> str | None:
        if sid in self.ts_ids:
            return "held-out TotalSegmentator s-number"
        if sid in self.ts_twins:
            return f"twin of held-out {self.ts_twins[sid]}"
        return None

    def check(self, kind: str, name: str) -> None:
        """Raise HeldOut on any refused case. kind: 'pool', 'imagecas' or 'ts'."""
        if kind == "ts" and not self.ts_twins:
            raise HeldOut("TotalSegmentator checks need the twin rule: construct Guard(ts_meta=...)")
        r = {"pool": self.pool_reason, "imagecas": self.imagecas_reason, "ts": self.ts_reason}[kind](name)
        if r:
            raise HeldOut(f"refused {kind} case {name}: {r}")

    def check_all(self, kind: str, names) -> list:
        names = list(names)
        for n in names:
            self.check(kind, n)
        return names


def read_meta(path: str) -> dict:
    with open(path, encoding="utf-8-sig") as fh:
        rows = list(csv.DictReader(fh, delimiter=";"))
    return {r["image_id"].strip(): r for r in rows}


def _age(r):
    try:
        return float(r.get("age", ""))
    except ValueError:
        return None


def twins(meta_path: str, held: set) -> dict:
    """{public s-number: held-out s-number it may be the same patient as}. Ruling §4: same sex and institute,
    |age difference| <= 5 years, any study type. A missing field matches anything (over-refusal is safe)."""
    meta = read_meta(meta_path)
    missing = held - set(meta)
    if missing:
        raise HeldOut(f"held-out ids absent from {meta_path}: {sorted(missing)}; wrong meta file")
    out = {}
    for h in sorted(held):
        hr = meta[h]
        ha = _age(hr)
        for sid, r in meta.items():
            if sid in held or sid in out:
                continue
            if hr["gender"].strip() and r["gender"].strip() and hr["gender"].strip() != r["gender"].strip():
                continue
            if hr["institute"].strip() and r["institute"].strip() and hr["institute"].strip() != r["institute"].strip():
                continue
            a = _age(r)
            if ha is not None and a is not None and abs(a - ha) > TWIN_AGE_YEARS:
                continue
            out[sid] = h
    return out


def main(argv):
    metas = [argv[i + 1] for i, a in enumerate(argv) if a == "--meta"]
    g = Guard(ts_meta=metas)
    meta = metas[0] if metas else None
    rep = {
        "d35_files": [str(Path(f).relative_to(ROOT)) for f in g.d35_files],
        "pool_volumes": len(g.pool),
        "pool_patients": len(g.pool_patients),
        "seal_patients": len(g.seal.patients),
        "reserve_patients": len(g.reserve),
        "imagecas_refused": len(g.imagecas),
        "imagecas_train_allowed": len(g.imagecas_train),
        "ts_held_out_ids": sorted(g.ts_ids),
    }
    if meta:
        rep["ts_meta_files"] = [Path(m).name for m in metas]
        rep["ts_meta_subjects"] = len(set().union(*(read_meta(m) for m in metas)))
        rep["ts_twins_refused"] = len(g.ts_twins)
        by = {}
        for t, h in g.ts_twins.items():
            by.setdefault(h, []).append(t)
        rep["ts_twins_per_held_out"] = {h: len(v) for h, v in sorted(by.items())}
        cardiac = {"ct heart", "ct heart-thorakale aorta", "ct aortic valve", "ct coronary arteries", "ct left artrium"}
        m = read_meta(metas[0])  # study types from the first file (v1)
        card = {s for s, r in m.items() if r.get("study_type", "").strip().lower() in cardiac}
        rep["ts_cardiac_studies"] = len(card)
        rep["ts_cardiac_held_out"] = len(card & g.ts_ids)
        rep["ts_cardiac_twins_refused"] = len(card & set(g.ts_twins))
        rep["ts_cardiac_left"] = len(card - g.ts_ids - set(g.ts_twins))
    print(json.dumps(rep, indent=1))
    return rep


if __name__ == "__main__":
    main(sys.argv[1:])
