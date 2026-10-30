"""The Janus-M held-out guard (JA12): the check every Janus-M fetch, loader and Fir job runs first.

It replaces the five Round 1 prototypes (Golf's ``heldout.py``, Hotel's ``coronary_holdout.py``,
India's ``pool_subjects()``, Juliet's ``exclusion.py``, Kilo's ``heldout.py``). Ruling:
``vault/JanusM/Judgements/Round 1.md``, JA12 and §4.

Refused, by patient (``segtrain.pool_seal`` grouping, so every volume of a held-out patient):

* the coronary pool seal, primary and report-only (D27/D32/D33);
* its extension order, the A34 reserve;
* every Round 10 D35 draw: every list in the five draw files except the ones they mark as
  trainable (:data:`NOT_HELD_OUT_KEYS`);
* the A14 sealed 100, the ImageCAS-X test split (160) and val 80;
* PLOS-Peng2016 (any case);
* every public copy of a held-out pool patient under its public id (TotalSegmentator s-numbers,
  ImageCAS ids, and any pool source named as the pool names it);
* every TotalSegmentator "twin" of a held-out TotalSegmentator subject (Round 1 §4, widened by
  Round 2 JA22 to match a blank institute): the pinned list ``configs/janusm/ts-twins-r1.json``,
  built by ``tools/janusm/build_ts_twins.py``;
* once the JA6 freeze (#140) pins ``configs/janusm/sealed-r1.json``: Janus-M seal cases outside
  seal scoring, and decision cases outside decision scoring.

Every input file is sha256-pinned in :data:`PINNED`; a changed, missing or new (unpinned) list is
an error, never a pass. The guard reads repository files only: no network, no credentials, and it
never writes.

Use::

    from janusm.guard import refuse
    refuse(names, what="E2 TotalSegmentator fetch")      # raises HeldOutError on any hit

    from janusm.guard import load_guard
    g = load_guard()
    g.reason("TotalSegmentator-cardiac__s0655")          # -> "... coronary pool seal ..."
    g.reason("s0655", source="TotalSegmentator")         # public copy, same patient
    g.reason("3", source="ImageCAS")                     # ImageCAS id 3 is ImageCAS-X c0002

``refuse`` raises on the first call with any held-out name, listing them: the caller stops the whole
run. There is deliberately no "exclude" mode.

CLI: ``python -m janusm.guard [--source SRC] NAME ...`` prints a verdict per name; exit 3 on any
refusal. ``python -m janusm.guard --summary`` prints the counts.

Standard library only.
"""

from __future__ import annotations

import functools
import hashlib
import json
import os
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, FrozenSet, Iterable, List, Optional, Tuple

from janusm import sealed_r1
from segtrain import pool_seal
from segtrain.pool_seal import _CHANNEL, _READ_SUFFIX, _patient_key, _stem, ingest_patient

#: Bumped whenever what the guard refuses changes. Callers may record it beside their outputs.
#: v2: JA22 widens the twin rule (a blank institute matches any); 708 -> 711 refused.
GUARD_VERSION = "2"

#: Environment variable naming the repository checkout the guard reads (default: this checkout).
ROOT_ENV = "JANUSM_REPO"

SEAL_RELPATH = pool_seal.SEAL_RELPATH
A14_RELPATH = "trillium/icx4/sealed_test.json"
SPLITS_RELPATH = "trillium-results/icx14/results/splits.json"
TWINS_RELPATH = "configs/janusm/ts-twins-r1.json"
#: Every Round 10 D35 draw file. A new one matching :data:`D35_GLOBS` and not listed here fails.
D35_DRAWS = (
    "experiments/Atlas/r10/decision_set_proposal.json",
    "experiments/Bridge/r10/decision_set_proposal.json",
    "experiments/Crucible/r10/d35_proposal.json",
    "experiments/Delta/r10/d35_decision_set_proposal.json",
    "experiments/Foxtrot/r10/d35_proposal.json",
)
D35_GLOBS = ("experiments/*/r10*/*decision*proposal*.json",
             "experiments/*/r10*/*d35*proposal*.json")
#: Lists in a draw file that the draw marks as *not* held out (trainable now, or Janus 0 may
#: predict them). Every other ``<Source>__<case>`` name in a draw file is held out.
NOT_HELD_OUT_KEYS = ("trainable", "janus0_may_predict")

#: relpath -> sha256 of every input. A change to any of them is an explicit PR here.
PINNED: Dict[str, str] = {
    SEAL_RELPATH: pool_seal.SEAL_SHA256,
    A14_RELPATH: "319cbc949161c1ee8738153b30405d881f91846200e0ddbfa3b11bcc4233055b",
    SPLITS_RELPATH: "a53bd426cddcf70e92555abe9c01a867736b1390782abaa0160b1da5fb2d9e17",
    "experiments/Atlas/r10/decision_set_proposal.json":
        "bc47690cc1b0acb50037f19ea05ae0619444c1ed1396be592082371b022b6042",
    "experiments/Bridge/r10/decision_set_proposal.json":
        "fb551a7eb4b45c7e858ccf287c9c72dedf517ba9a0a9816dfe66b3145b79b403",
    "experiments/Crucible/r10/d35_proposal.json":
        "73effb061580089e2d3379405ade51dee756a23982c31807079cf9387d910429",
    "experiments/Delta/r10/d35_decision_set_proposal.json":
        "1a75fe41ffe44aa37c884b723c066a6b8cd3669164e0c670b6439028c2b966b1",
    "experiments/Foxtrot/r10/d35_proposal.json":
        "a588ad17f7e6f03e128627bfadec84b5b9cb277cd92234352f5b719d2a7cd514",
    TWINS_RELPATH: "ff3a1b78123e4382c4b8cf214c1766e49ac3abdf76503c7eb3f9e4e451daad95",
}

#: The Janus-M seal and decision set (JA6, #140), frozen in :mod:`janusm.sealed_r1`, which holds
#: the one pin. The guard reads these keys, each a list of ImageCAS-X case ids (``c0000`` form):
#: ``seal`` and ``seal_extension`` (refused outside seal scoring), ``decision`` (refused outside
#: decision scoring). ``jm0`` and other keys are ignored. File present but unpinned, or pinned
#: but missing, is an error.
JANUSM_SEAL_RELPATH = sealed_r1.PATH
JANUSM_SEAL_SHA256: Optional[str] = sealed_r1.SEALED_R1_SHA256

#: Purposes a caller declares. Only the Janus-M seal and decision lists depend on it; a coronary
#: hold-out is refused for every purpose.
ANY, SEAL_SCORING, DECISION_SCORING = "any", "seal_scoring", "decision_scoring"
PURPOSES = (ANY, SEAL_SCORING, DECISION_SCORING)

TS_SOURCE = "TotalSegmentator-cardiac"   # the pool's source name for TotalSegmentator studies
ICX_SOURCE = "ImageCAS-X"
PLOS_PREFIX = "PLOS-Peng2016"
#: Public dataset names -> the name the guard checks them under (lower-case keys).
PUBLIC_SOURCES = {
    "totalsegmentator": TS_SOURCE, "totalsegmentator-cardiac": TS_SOURCE,
    "totalsegmentator-v1": TS_SOURCE, "totalsegmentator-v2": TS_SOURCE,
    "totalsegmentator_dataset": TS_SOURCE, "totalsegmentator-v201": TS_SOURCE, "ts": TS_SOURCE,
    "imagecas": ICX_SOURCE, "imagecas-x": ICX_SOURCE, "icx": ICX_SOURCE,
}

_NAME = re.compile(r"[A-Za-z][A-Za-z0-9_.-]*__[A-Za-z0-9_.-]+")
_TS_ID = re.compile(r"s\d{4}")
_ICX_ID = re.compile(r"c\d{4}")
_IMAGECAS_ID = re.compile(r"(\d+)(\.img|\.label)?")


class HeldOutError(RuntimeError):
    """A held-out case reached a Janus-M run (JA12). The whole run stops."""


class GuardInputError(HeldOutError):
    """An input list is missing, changed (sha256) or unpinned. Never a pass."""


def default_root() -> Path:
    env = os.environ.get(ROOT_ENV)
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[2]


def _read_pinned(root: Path, rel: str, sha: Optional[str] = None) -> bytes:
    p = root / rel
    if not p.is_file():
        raise GuardInputError(f"JA12 guard input {rel} not found under {root}; refusing to go on")
    raw = p.read_bytes()
    want = sha if sha is not None else PINNED[rel]
    got = hashlib.sha256(raw).hexdigest()
    if got != want:
        raise GuardInputError(
            f"{rel}: sha256 {got} is not the pinned {want}; a held-out list changed. Changing "
            "it is an explicit PR to the file and janusm.guard.PINNED")
    return raw


def _names_outside(obj, skip=NOT_HELD_OUT_KEYS) -> set:
    """Every ``<Source>__<case>`` in a JSON value, keys included, outside keys marked trainable."""
    out = set()
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith(skip):
                continue
            out |= set(_NAME.findall(str(k)))
            out |= _names_outside(v, skip)
    elif isinstance(obj, list):
        for v in obj:
            out |= _names_outside(v, skip)
    elif isinstance(obj, str):
        out |= set(_NAME.findall(obj))
    return out


def _forms(stem: str) -> List[str]:
    forms = {stem}
    forms |= {_CHANNEL.sub("", s) for s in list(forms)}
    forms |= {_READ_SUFFIX.sub("", s) for s in list(forms)}
    return sorted(forms)


def _keys(name: str) -> set:
    """Patient keys of a pool name: itself, Bridge's patient key, the ingest patient."""
    return {k for k in (name, _patient_key(name), ingest_patient(name)) if k}


@dataclass(frozen=True)
class Guard:
    """The loaded guard. Build it with :func:`load_guard`."""

    root: str
    seal: pool_seal.PoolSeal
    reserve: FrozenSet[str]               # patient keys of the extension order
    d35: FrozenSet[str]                   # patient keys of every D35 draw name
    icx: Dict[str, FrozenSet[str]]        # "a14_sealed" / "icx_test" / "val80" -> c-ids
    ts_held_out: FrozenSet[str]           # held-out TotalSegmentator s-numbers
    ts_twins: Dict[str, Tuple[str, ...]]  # twin s-number -> held-out s-numbers it matches
    janusm: Dict[str, FrozenSet[str]] = field(default_factory=dict)  # JA6 lists, once pinned
    pins: Dict[str, str] = field(default_factory=dict)

    # ------------------------------------------------------------------ identify
    def _identify(self, name, source=None) -> Tuple[List[str], Optional[str], Optional[str]]:
        """(pool-name forms, TotalSegmentator s-number, ImageCAS-X c-id) for a name."""
        raw = str(name).strip().replace("\\", "/")
        stem = _stem(raw)
        if source is not None:
            src = PUBLIC_SOURCES.get(str(source).strip().lower(), str(source).strip())
            if src == ICX_SOURCE:
                return [], None, _icx_id(stem)
            if "__" not in stem:
                stem = f"{src}__{stem}"
        if "__" in stem:
            src, case = stem.split("__", 1)
            canon = PUBLIC_SOURCES.get(src.lower(), src)
            if canon == ICX_SOURCE:
                return [], None, _icx_id(case)
            stem = f"{canon}__{case}"
            ts = None
            if canon == TS_SOURCE:
                m = _TS_ID.match(case)
                ts = m.group(0) if m else None
            return _forms(stem), ts, None
        # A bare id or a path: look at every path segment.
        segs = [s for s in raw.split("/") if s] + [stem]
        ts = next((s for s in segs if _TS_ID.fullmatch(s)), None)
        icx = next((s for s in segs if _ICX_ID.fullmatch(s)), None)
        if icx is None and any("imagecas" in s.lower() for s in segs[:-1]):
            icx = _icx_id(stem)
        forms = _forms(f"{TS_SOURCE}__{ts}") if ts else []
        return forms, ts, icx

    # ------------------------------------------------------------------ verdicts
    def reason(self, name, source=None, purpose: str = ANY) -> Optional[str]:
        """Why ``name`` is refused (JA12), or None. ``source`` names the public dataset when
        ``name`` is a bare public id (``"s0655"``, ``"c0002"``, ImageCAS ``"3"``)."""
        if purpose not in PURPOSES:
            raise ValueError(f"purpose {purpose!r} is not one of {PURPOSES}")
        forms, ts, icx = self._identify(name, source)
        for f in forms:
            if f.split("__", 1)[0].startswith(PLOS_PREFIX):
                return f"{name}: PLOS-Peng2016 (JA5; never used)"
            why = self.seal.reason(f)
            if why:
                return f"{name}: coronary pool seal ({why})"
            keys = _keys(f)
            if keys & self.reserve:
                return f"{name}: coronary seal reserve / extension order (A34), patient {_pk(f)}"
            if keys & self.d35:
                return f"{name}: a Round 10 D35 draw, patient {_pk(f)}"
        if ts and ts in self.ts_held_out:
            return f"{name}: TotalSegmentator {ts} is a held-out pool patient"
        if ts and ts in self.ts_twins:
            return (f"{name}: TotalSegmentator {ts} is a possible twin of held-out "
                    f"{', '.join(self.ts_twins[ts])} (Round 1 §4)")
        if icx:
            for key, label in (("a14_sealed", "A14 sealed 100"),
                               ("icx_test", "ImageCAS-X test split"),
                               ("val80", "ImageCAS-X val 80")):
                if icx in self.icx[key]:
                    return f"{name}: ImageCAS-X {icx} is in the {label}"
            if purpose != SEAL_SCORING:
                for key in ("seal", "extension"):
                    if icx in self.janusm.get(key, ()):
                        return f"{name}: ImageCAS-X {icx} is a Janus-M seal case ({key}; JA6)"
            if purpose != DECISION_SCORING and icx in self.janusm.get("decision", ()):
                return f"{name}: ImageCAS-X {icx} is a Janus-M decision case (JA6)"
        return None

    def is_held_out(self, name, source=None, purpose: str = ANY) -> bool:
        return self.reason(name, source, purpose) is not None

    def check(self, names: Iterable, what: str = "this Janus-M run", source=None,
              purpose: str = ANY) -> list:
        """Return ``names`` unchanged if none is held out; otherwise raise :class:`HeldOutError`
        naming every hit. Call it before opening, fetching or scoring anything."""
        names = list(names)
        hits = [r for r in (self.reason(n, source, purpose) for n in names) if r]
        if hits:
            shown = "\n  ".join(hits[:20]) + ("\n  ..." if len(hits) > 20 else "")
            raise HeldOutError(
                f"REFUSING {what} (JA12 guard v{GUARD_VERSION}): {len(hits)} of {len(names)} "
                f"name(s) are held out:\n  {shown}")
        return names

    def summary(self) -> dict:
        return {
            "guard_version": GUARD_VERSION,
            "pins": dict(self.pins),
            "pool_seal_patients": len(self.seal.patients),
            "pool_seal_volumes": len(self.seal.volumes),
            "reserve_patient_keys": len(self.reserve),
            "d35_patient_keys": len(self.d35),
            "icx": {k: len(v) for k, v in self.icx.items()},
            "ts_held_out": sorted(self.ts_held_out),
            "ts_twins": len(self.ts_twins),
            "janusm_lists": {k: len(v) for k, v in self.janusm.items()},
        }


def _pk(name: str) -> str:
    return ingest_patient(name) or name


def _icx_id(case: str) -> Optional[str]:
    """ImageCAS-X ``c0002`` as is; an ImageCAS release id ``3`` (or ``3.img``) -> ``c0002``."""
    case = _stem(case)
    if _ICX_ID.fullmatch(case):
        return case
    m = _IMAGECAS_ID.fullmatch(case)
    if m and int(m.group(1)) >= 1:
        return f"c{int(m.group(1)) - 1:04d}"
    return None


# ---------------------------------------------------------------------- loading
def _held_out_pool(root: Path, pins: dict):
    """The coronary pool hold-outs, without the twin list: (seal, reserve keys, D35 keys)."""
    unlisted = sorted({str(p.relative_to(root)) for g in D35_GLOBS for p in root.glob(g)}
                      - set(D35_DRAWS))
    if unlisted:
        raise GuardInputError(f"unpinned Round 10 draw file(s) {unlisted}; add them to "
                              "janusm.guard.D35_DRAWS and PINNED")
    _read_pinned(root, SEAL_RELPATH)
    seal = pool_seal.load_pool_seal(root / SEAL_RELPATH)
    raw = json.loads((root / SEAL_RELPATH).read_text())
    reserve = set()
    for p in raw["primary"]["extension_order"]:
        reserve |= _keys(_stem(p))
    for a, b in raw.get("d32", {}).get("merged_aliases", {}).items():
        if _keys(a) & (seal.patients | reserve) or _keys(b) & (seal.patients | reserve):
            reserve |= _keys(a) | _keys(b)
    d35 = set()
    for rel in D35_DRAWS:
        names = _names_outside(json.loads(_read_pinned(root, rel).decode("utf-8")))
        if not names:
            raise GuardInputError(f"{rel}: no patient names found")
        for n in names:
            d35 |= _keys(_stem(n))
    pins.update({r: PINNED[r] for r in (SEAL_RELPATH, *D35_DRAWS)})
    return seal, frozenset(reserve), frozenset(d35)


def held_out_ts_ids(root=None) -> FrozenSet[str]:
    """TotalSegmentator s-numbers of every held-out pool patient (seal, reserve, D35 draws).
    ``tools/janusm/build_ts_twins.py`` builds the twin list from these."""
    root = Path(root) if root else default_root()
    seal, reserve, d35 = _held_out_pool(root, {})
    return _ts_ids(seal, reserve, d35)


def _ts_ids(seal, reserve, d35) -> FrozenSet[str]:
    out = set()
    for n in set(seal.volumes) | set(seal.patients) | set(reserve) | set(d35):
        src, _, case = n.partition("__")
        m = _TS_ID.match(case)
        if PUBLIC_SOURCES.get(src.lower(), src) == TS_SOURCE and m:
            out.add(m.group(0))
    return frozenset(out)


def _load(root: Path) -> Guard:
    pins: Dict[str, str] = {}
    seal, reserve, d35 = _held_out_pool(root, pins)
    a14 = json.loads(_read_pinned(root, A14_RELPATH).decode("utf-8"))
    splits = json.loads(_read_pinned(root, SPLITS_RELPATH).decode("utf-8"))
    icx = {
        "a14_sealed": frozenset(a14["sealed_icx_test"]) | frozenset(a14["sealed_quality0"]),
        "icx_test": frozenset(splits["test"]) | frozenset(a14["open_icx_test"])
        | frozenset(a14["excluded_dev_cases_in_test"]),
        "val80": frozenset(splits["val"]),
    }
    if len(icx["a14_sealed"]) != 100 or len(splits["val"]) != 80 or len(splits["test"]) != 160:
        raise GuardInputError("A14 sealed 100 / val 80 / test 160 have the wrong sizes")
    ts_held = _ts_ids(seal, reserve, d35)
    tw = json.loads(_read_pinned(root, TWINS_RELPATH).decode("utf-8"))
    if sorted(tw["held_out"]) != sorted(ts_held):
        raise GuardInputError(
            f"{TWINS_RELPATH} was built for held-out ids {sorted(tw['held_out'])}, but the guard "
            f"now holds out {sorted(ts_held)}; rebuild it with tools/janusm/build_ts_twins.py")
    twins = {k: tuple(v) for k, v in tw["twins"].items() if k not in ts_held}
    pins.update({r: PINNED[r] for r in (A14_RELPATH, SPLITS_RELPATH, TWINS_RELPATH)})
    janusm = _load_janusm_seal(root, pins)
    return Guard(root=str(root), seal=seal, reserve=reserve, d35=d35, icx=icx,
                 ts_held_out=ts_held, ts_twins=twins, janusm=janusm, pins=pins)


def _load_janusm_seal(root: Path, pins: dict) -> Dict[str, FrozenSet[str]]:
    p = root / JANUSM_SEAL_RELPATH
    if JANUSM_SEAL_SHA256 is None:
        if p.exists():
            raise GuardInputError(f"{JANUSM_SEAL_RELPATH} exists but janusm.guard."
                                  "JANUSM_SEAL_SHA256 does not pin it")
        return {}
    data = json.loads(_read_pinned(root, JANUSM_SEAL_RELPATH, JANUSM_SEAL_SHA256).decode("utf-8"))
    out = {k: frozenset(data[k]) for k in ("seal", "decision") if k in data}
    out["extension"] = frozenset(data.get("seal_extension", ()))
    if not out.get("seal") or not out.get("decision"):
        raise GuardInputError(f"{JANUSM_SEAL_RELPATH}: no seal or decision list")
    pins[JANUSM_SEAL_RELPATH] = JANUSM_SEAL_SHA256
    return out


@functools.lru_cache(maxsize=4)
def _cached(root: str) -> Guard:
    return _load(Path(root))


def load_guard(root=None) -> Guard:
    """Load and verify every pinned input (cached per checkout). Raises :class:`GuardInputError`
    on a missing, changed or unpinned list."""
    return _cached(str(Path(root) if root else default_root()))


def refuse(names: Iterable, what: str = "this Janus-M run", source=None, purpose: str = ANY,
           root=None) -> list:
    """Module-level :meth:`Guard.check`: the one call every Janus-M entry point makes first."""
    return load_guard(root).check(names, what=what, source=source, purpose=purpose)


def refuse_one(name, source=None, purpose: str = ANY, root=None):
    """Refuse a single name; return it if allowed."""
    refuse([name], what=str(name), source=source, purpose=purpose, root=root)
    return name


def main(argv=None) -> int:
    import argparse

    ap = argparse.ArgumentParser(prog="python -m janusm.guard", description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="*")
    ap.add_argument("--source", help="public dataset of bare ids (TotalSegmentator, ImageCAS, ...)")
    ap.add_argument("--purpose", default=ANY, choices=PURPOSES)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args(argv)
    g = load_guard()
    if a.summary:
        print(json.dumps(g.summary(), indent=1))
    bad = 0
    for n in a.names:
        r = g.reason(n, a.source, a.purpose)
        bad += bool(r)
        print(f"{n}\t{'REFUSED: ' + r if r else 'allowed'}")
    return 3 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
