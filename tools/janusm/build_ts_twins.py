"""Build ``configs/janusm/ts-twins-r1.json``: TotalSegmentator "twins" of held-out pool patients.

Round 1 §4 (JA12): TotalSegmentator publishes no patient id, so one held-out patient could appear
in the public release under a second s-number. The rule flags as a twin every public subject that
matches a held-out subject on **sex and institute, age within ±5 years, any study type**. A
missing sex on either side matches any sex (conservative). Round 2 (JA22, ``vault/JanusM/
Judgements/Round 2 - rest-ccta.md``) widens it: a blank institute on either side matches any
institute. The widening only adds twins; it never removes one. It is applied to each public release
separately (v1.0 and v2.0.1 relabel institutes, so rows are compared only within one release),
and the union is refused. Round 2 refines the rule; the guard reads only this pinned output.

Inputs are the two public ``meta.csv`` files (no patient data: age, sex, institute letter, study
type), fetched once by the operator, e.g. with ``remotezip`` from Zenodo 6802614 (v1.0,
``Totalsegmentator_dataset/meta.csv``) and 10047292 (v2.0.1, ``meta.csv``). Their sha256 go into
the output. The held-out ids come from ``janusm.guard.held_out_ts_ids()``.

    python tools/janusm/build_ts_twins.py --v1 META_V1.csv --v2 META_V201.csv [--out PATH]

Then pin the new file's sha256 in ``janusm.guard.PINNED``.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "src"))
from janusm.guard import TWINS_RELPATH, held_out_ts_ids  # noqa: E402

AGE_WINDOW = 5.0
RULE = ("twin = any public TotalSegmentator subject, other than the held-out subject itself, "
        "in the same release with the same institute (a blank institute on either side matches "
        "any), the same sex (a missing sex matches any), "
        f"and age within +/-{AGE_WINDOW:g} years; any study type (Round 1 §4, JA12; JA22)")


def read_meta(path: Path) -> dict:
    rows = csv.DictReader(path.read_text(encoding="utf-8-sig").splitlines(), delimiter=";")
    return {r["image_id"].strip(): r for r in rows}


def _age(r):
    try:
        return float(r["age"])
    except (KeyError, TypeError, ValueError):
        return None


def twins_in(meta: dict, held: set) -> dict:
    """{twin id: [held-out ids it matches]} within one release."""
    out = {}
    for h in sorted(held & set(meta)):
        hr = meta[h]
        ha, hs, hi = _age(hr), hr["gender"].strip().lower(), hr["institute"].strip()
        for sid, r in meta.items():
            if sid == h:
                continue
            i = r["institute"].strip()
            if hi and i and i != hi:   # JA22: a blank institute matches any
                continue
            s = r["gender"].strip().lower()
            if hs and s and s != hs:
                continue
            a = _age(r)
            if ha is not None and a is not None and abs(a - ha) > AGE_WINDOW:
                continue
            out.setdefault(sid, []).append(h)
    return out


def build(v1: Path, v2: Path) -> dict:
    held = set(held_out_ts_ids(REPO))
    releases = {"v1.0": (v1, "zenodo 6802614"), "v2.0.1": (v2, "zenodo 10047292")}
    twins, per = {}, {}
    for tag, (path, rec) in releases.items():
        meta = read_meta(path)
        t = twins_in(meta, held)
        per[tag] = {"source": rec, "meta_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "subjects": len(meta), "held_out_present": sorted(held & set(meta)),
                    "twins": len(t)}
        for k, v in t.items():
            twins.setdefault(k, set()).update(v)
    return {
        "rule": RULE,
        "releases": per,
        "held_out": sorted(held),
        "n_twins": len(twins),
        "twins": {k: sorted(v) for k, v in sorted(twins.items())},
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--v1", type=Path, required=True)
    ap.add_argument("--v2", type=Path, required=True)
    ap.add_argument("--out", type=Path, default=REPO / TWINS_RELPATH)
    a = ap.parse_args(argv)
    data = build(a.v1, a.v2)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(data, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    a.out.write_bytes(raw)
    print(f"{a.out}: {data['n_twins']} twins of {len(data['held_out'])} held-out ids; "
          f"sha256 {hashlib.sha256(raw).hexdigest()}")


if __name__ == "__main__":
    main()
