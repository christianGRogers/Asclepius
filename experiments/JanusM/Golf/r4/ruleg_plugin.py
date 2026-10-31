"""pytest plugin (Golf R4, #251 item 2): swap JA51 4(b) for candidate rule g or b inside the shipped register_lie, to
run the PS3-S3 tests against it without editing src/. Diagnostic only.

Usage: RULE=g PYTHONPATH=src:tests:experiments/JanusM/Golf/r4 pytest -p ruleg_plugin --runxfail \
         tests/test_janusm_scar_registration.py -k ps3_s3
"""
import os
import numpy as np
from janusm.scar import registration as R

RULE = os.environ.get("RULE", "g")
_last = {}
_orig_sanity = R.affine_sanity


def sanity(m):
    s = _orig_sanity(m)
    _last["ld"] = s["log_det"]
    return s


def rule(new, old, cuts):
    a, r = R.normalised(new, cuts), R.normalised(old, cuts)
    if not (np.isfinite(a).all() and np.isfinite(r).all()):
        return False
    ld = abs(_last.get("ld", 0.0))
    if RULE == "g":
        return bool(a.max() <= r.max() and (new.passes(cuts) or ld >= 0.02))
    if RULE == "b":
        return bool(a.max() < r.max() and not ((a > 1) & (r <= 1)).any())
    raise ValueError(RULE)


R.affine_sanity = sanity
R.qc_rule_accepts = rule
