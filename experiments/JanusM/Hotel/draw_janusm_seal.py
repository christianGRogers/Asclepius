"""Hotel: a proposed Janus-M sealed test and decision set, drawn before any image is looked at.

Population: the patients of janusm_r1_pool_volumes.tsv (free of every coronary hold-out).
Rule: rank patients by sha256(SALT + patient) within each source; take the first
ceil(0.30 * n_source) as sealed and the next ceil(0.20 * n_source) as the decision set; the rest
train. Every volume of a sealed patient is sealed. Nothing is frozen by this script: the judge
rules and a role:swe PR freezes the file (sha256-pinned) before any read of these volumes.

Usage: python draw_janusm_seal.py OUT_JSON
"""
import hashlib
import json
import math
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from coronary_holdout import PoolGuard  # noqa: E402

SALT = "asclepius-janusm-seal-r1:"
SEAL_FRAC, DECISION_FRAC = 0.30, 0.20


def main(out: Path) -> None:
    guard = PoolGuard()
    rows = [ln.split("\t") for ln in (HERE / "janusm_r1_pool_volumes.tsv").read_text().splitlines()
            if ln and not ln.startswith("#")]
    by_src = defaultdict(lambda: defaultdict(list))
    for name, _item, src, *_ in rows:
        assert guard.reason(name) is None, name
        pat = guard._patient(guard._stem(name))
        by_src[src][pat].append(name)
    res = {"salt": SALT, "rule": __doc__.split("Rule: ")[1].split("\n\n")[0].replace("\n", " "),
           "sealed": {}, "decision": {}, "train": {}, "per_source": {}}
    for src, pats in sorted(by_src.items()):
        ranked = sorted(pats, key=lambda p: hashlib.sha256((SALT + p).encode()).hexdigest())
        n = len(ranked)
        ns, nd = math.ceil(SEAL_FRAC * n), math.ceil(DECISION_FRAC * n)
        if n < 3:  # a source this small trains only
            ns, nd = 0, 0
        for i, p in enumerate(ranked):
            part = "sealed" if i < ns else "decision" if i < ns + nd else "train"
            res[part][p] = sorted(pats[p])
        res["per_source"][src] = {"patients": n, "sealed": ns, "decision": nd, "train": n - ns - nd}
    res["counts"] = {k: len(res[k]) for k in ("sealed", "decision", "train")}
    out.write_text(json.dumps(res, indent=1))
    print(json.dumps({"per_source": res["per_source"], "counts": res["counts"]}, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]))
