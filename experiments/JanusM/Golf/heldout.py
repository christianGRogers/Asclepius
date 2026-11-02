"""Golf's held-out guard: refuse, in code, any case Janus-M may not open, download, read or score.

Held out (README "Binding from the project"; PM instruction 2026-10-30):
  - every volume and real patient in the pool seal configs/segqueue14/sealed-pool-2026-10.json (primary, report-only,
    extension order / reserve), grouped by real patient with segtrain.pool_seal.ingest_patient (the ingest rule);
  - every patient and volume named anywhere in a Round 10 D35 draw (experiments/*/r10*/*decision_set*proposal*.json,
    reserve lists included);
  - the ImageCAS cases sealed by A14 (trillium/icx4/sealed_test.json: sealed_icx_test + sealed_quality0).
Public copies reuse the pool's case numbers, so a public case is checked under its pool name `<Source>__<case>`.

    from heldout import refuse
    refuse("TotalSegmentator-cardiac", "s0356")   # raises HeldOutError
    refuse("ImageCAS", "c0002")                   # raises HeldOutError

CLI: python heldout.py <Source> <case> [...]   (exit 3 if any is held out)
"""
import glob, json, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from segtrain.pool_seal import ingest_patient, _stem, load_pool_seal  # noqa: E402

NAME = re.compile(r"([A-Za-z][A-Za-z0-9_.-]*__[A-Za-z0-9_.-]+)")


class HeldOutError(RuntimeError):
    pass


def _names(path):
    return {_stem(m) for m in NAME.findall(Path(path).read_text())}


def _build():
    load_pool_seal()                       # verifies the pinned sha256; refuses a changed seal file
    names = _names(ROOT / "configs/segqueue14/sealed-pool-2026-10.json")
    draws = sorted(set(glob.glob(str(ROOT / "experiments/*/r10*/*decision_set*proposal*.json"))))
    if len(draws) < 3:
        raise HeldOutError(f"expected the three Round 10 D35 draws, found {draws}")
    for p in draws:
        names |= _names(p)
    keys = set(names) | {ingest_patient(n) for n in names if ingest_patient(n)}
    S = json.loads((ROOT / "trillium/icx4/sealed_test.json").read_text())
    icx = set(S["sealed_icx_test"]) | set(S["sealed_quality0"])
    if len(icx) != 100:
        raise HeldOutError("trillium/icx4/sealed_test.json does not hold the 100 A14 cases")
    return keys, icx, draws


_KEYS, _ICX, DRAWS = _build()


def reason(source, case):
    if source == "ImageCAS":
        return f"ImageCAS {case}: A14 sealed" if case in _ICX else None
    stem = f"{source}__{case}"
    for k in (stem, ingest_patient(stem)):
        if k and k in _KEYS:
            return f"{stem}: held out (pool seal, reserve or a D35 draw; patient {ingest_patient(stem)})"
    return None


def refuse(source, case):
    r = reason(source, case)
    if r:
        raise HeldOutError(f"REFUSING {r}")
    return case


if __name__ == "__main__":
    a = sys.argv[1:]
    bad = [reason(a[0], c) for c in a[1:]]
    for c, r in zip(a[1:], bad):
        print(c, r or "allowed")
    sys.exit(3 if any(bad) else 0)
