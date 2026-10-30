"""The paired-seal scoring harness (Round 2 paired-scar ruling, JA27, JA29, JA32; JA35 item 6).

Ruling: ``vault/JanusM/Judgements/Round 2 - paired-scar.md``. One call, :func:`score`, turns
per-segment CT and LGE Kim bins into the JA32 decision and everything JA32 says is reported beside
it.

Inputs, per patient (:class:`Patient`), one entry per AHA segment (index 0 is segment 1):

* ``ref``: the adjudicated LGE Kim bin, 0 (no scar) or 1-4 (1-25 / 26-50 / 51-75 / 76-100 %);
* ``ct``: the CT Kim bin, or :data:`NOT_GRADED` when registration failed twice (JA29);
* ``ischaemic``: whether an LGE-positive segment's pattern is ischaemic (subendocardial or
  transmural);
* ``strata``: the patient's JA27 strata (:data:`STRATA`).

Patients carry no identifier: the harness never needs one, so none can leak into its output.

**Intention-to-diagnose (JA29).** A not-graded segment counts as wrong: a miss if LGE-positive, a
false call (read as bin 1) if LGE-negative. It therefore never enters the scar-on-both set of the
transmurality endpoint. The graded-only analysis drops not-graded segments instead, and is
reported, never deciding.

**Primary analysis (JA32).** Seal patients outside every primary-excluding stratum (acute,
non-ischaemic pattern, phase-unmatched; prior CABG stays in, JA27), and within them the LGE-negative
and ischaemic-pattern LGE-positive segments. Every CI is a 95 % percentile bootstrap that resamples
patients (the cluster), and each bar is judged on a lower bound, one look:

* segment sensitivity for presence >= 0.75;
* segment specificity >= 0.93;
* transmurality agreement (exact Kim bin, segments scar on both) >= the development LGE inter-reader
  agreement on the same statistic (:func:`reader_agreement`) - 0.10. If that anchor is < 0.60 the
  endpoint is reported only and the decision rests on presence.

**Reported, never deciding:** linear- and quadratic-weighted kappa over all segments, patient-level
sensitivity and specificity, Bland-Altman of scar share (when shares are given), per-territory and
per-protocol results (prior-CABG patients are left out of territories, JA27), the not-graded rate,
the graded-only analysis and every JA27 stratum.

The same per-patient sufficient statistics drive :mod:`janusm.scar.power`, so the power script and
the seal are scored by one implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Mapping, Optional, Sequence

import numpy as np

NOT_GRADED = -1
N_BINS = 5  # Kim bin 0 (no scar) and 1-4

#: JA27 strata. Each is reported on its own; the first three are never pooled into the primary.
STRATA = ("acute", "non_ischaemic", "phase_unmatched", "prior_cabg")
EXCLUDED_FROM_PRIMARY = frozenset({"acute", "non_ischaemic", "phase_unmatched"})

#: JA32 bars on the 95 % lower bound.
SENS_BAR = 0.75
SPEC_BAR = 0.93
TBIN_MARGIN = 0.10
MIN_ANCHOR = 0.60  # below this the transmurality endpoint is reported only

#: Standard AHA 17-segment coronary map (Cerqueira 2002, secondary sources only, JA14), 0-based.
TERRITORIES: Dict[str, List[int]] = {
    "LAD": [0, 1, 6, 7, 12, 13, 16],
    "RCA": [2, 3, 8, 9, 14],
    "LCx": [4, 5, 10, 11, 15],
}

# Column layout of the per-patient statistics. Sums over patients are sufficient for every
# endpoint, so a cluster bootstrap is one matrix product of resampling weights with this table.
TP, POS, TN, NEG, BOTH, AGREE, PAT_POS, PAT_TP, PAT_NEG, PAT_TN = range(10)
CONF0 = 10
N_STATS = CONF0 + N_BINS * N_BINS

ENDPOINTS = (
    "sens",
    "spec",
    "tbin",
    "kappa_linear",
    "kappa_quadratic",
    "patient_sens",
    "patient_spec",
)


@dataclass(frozen=True)
class Patient:
    """One patient's per-segment reads. No identifier, by design."""

    ref: np.ndarray
    ct: np.ndarray
    ischaemic: Optional[np.ndarray] = None
    strata: frozenset = field(default_factory=frozenset)
    protocol: str = ""
    ref_share: Optional[np.ndarray] = None  # LGE scar share per segment, 0-1 (Bland-Altman only)
    ct_share: Optional[np.ndarray] = None

    def __post_init__(self):
        ref = np.asarray(self.ref, dtype=int)
        ct = np.asarray(self.ct, dtype=int)
        if ref.shape != ct.shape or ref.ndim != 1:
            raise ValueError("ref and ct must be 1-D and the same length")
        if ref.min() < 0 or ref.max() >= N_BINS:
            raise ValueError("ref must hold Kim bins 0-4")
        if ct.min() < NOT_GRADED or ct.max() >= N_BINS:
            raise ValueError("ct must hold Kim bins 0-4 or NOT_GRADED")
        unknown = set(self.strata) - set(STRATA)
        if unknown:
            raise ValueError(f"unknown strata {sorted(unknown)}; known: {STRATA}")
        if self.ischaemic is None:
            isch = np.ones(ref.shape, bool)
        else:
            isch = np.asarray(self.ischaemic, bool)
        if isch.shape != ref.shape:
            raise ValueError("ischaemic must match ref")
        object.__setattr__(self, "ref", ref)
        object.__setattr__(self, "ct", ct)
        object.__setattr__(self, "ischaemic", isch)
        object.__setattr__(self, "strata", frozenset(self.strata))


# -------------------------------------------------------------------------------------------------
# Intention-to-diagnose and the per-patient table


def intention_to_diagnose(ref: np.ndarray, ct: np.ndarray) -> np.ndarray:
    """Replace not-graded segments by a wrong call: a miss (0) if LGE-positive, else bin 1."""
    ref = np.asarray(ref)
    ct = np.asarray(ct)
    return np.where(ct == NOT_GRADED, np.where(ref > 0, 0, 1), ct)


def patient_stats(ref: np.ndarray, ct: np.ndarray, mask: Optional[np.ndarray] = None) -> np.ndarray:
    """Per-patient sufficient statistics, shape (N, N_STATS).

    ``ref`` and ``ct`` are (N, S) Kim bins; ``ct`` must already be resolved (no NOT_GRADED).
    ``mask`` (N, S) selects the segments that count; a masked-out segment contributes nothing.
    """
    ref = np.atleast_2d(np.asarray(ref, int))
    ct = np.atleast_2d(np.asarray(ct, int))
    if (ct < 0).any():
        raise ValueError("resolve NOT_GRADED first (intention_to_diagnose, or mask it out)")
    m = np.ones(ref.shape, bool) if mask is None else np.atleast_2d(np.asarray(mask, bool))
    n = ref.shape[0]
    pos = (ref > 0) & m
    neg = (ref == 0) & m
    called = ct > 0
    both = pos & called
    out = np.zeros((n, N_STATS))
    out[:, TP] = both.sum(1)
    out[:, POS] = pos.sum(1)
    out[:, TN] = (neg & ~called).sum(1)
    out[:, NEG] = neg.sum(1)
    out[:, BOTH] = both.sum(1)
    out[:, AGREE] = (both & (ref == ct)).sum(1)
    # patient level: scar on LGE in any counted segment, scar on CT in any counted segment
    p_pos = pos.any(1)
    p_called = (called & m).any(1)
    p_neg = ~p_pos & m.any(1)
    out[:, PAT_POS] = p_pos
    out[:, PAT_TP] = p_pos & p_called
    out[:, PAT_NEG] = p_neg
    out[:, PAT_TN] = p_neg & ~p_called
    cell = np.where(m, ref * N_BINS + ct, N_BINS * N_BINS)  # spare cell for masked segments
    rows = np.repeat(np.arange(n), ref.shape[1])
    conf = np.zeros((n, N_BINS * N_BINS + 1))
    np.add.at(conf, (rows, cell.ravel()), 1)
    out[:, CONF0:] = conf[:, : N_BINS * N_BINS]
    return out


def _ratio(num, den):
    num = np.asarray(num, float)
    den = np.asarray(den, float)
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, num / np.where(den > 0, den, 1), np.nan)


def _kappa(conf: np.ndarray, quadratic: bool) -> np.ndarray:
    """Weighted kappa from (..., 5, 5) confusion counts (rows LGE, columns CT)."""
    k = np.arange(N_BINS)
    d = np.abs(np.subtract.outer(k, k)) / (N_BINS - 1)
    w = 1 - (d**2 if quadratic else d)
    tot = conf.sum((-1, -2))
    p = conf / np.where(tot > 0, tot, 1)[..., None, None]
    e = p.sum(-1)[..., :, None] * p.sum(-2)[..., None, :]
    po = (w * p).sum((-1, -2))
    pe = (w * e).sum((-1, -2))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where((tot > 0) & (pe < 1), (po - pe) / (1 - pe), np.nan)


def endpoints(sums: np.ndarray) -> Dict[str, np.ndarray]:
    """Every endpoint from summed statistics, shape (..., N_STATS) -> dict of arrays (...)."""
    sums = np.asarray(sums, float)
    conf = sums[..., CONF0:].reshape(sums.shape[:-1] + (N_BINS, N_BINS))
    return {
        "sens": _ratio(sums[..., TP], sums[..., POS]),
        "spec": _ratio(sums[..., TN], sums[..., NEG]),
        "tbin": _ratio(sums[..., AGREE], sums[..., BOTH]),
        "kappa_linear": _kappa(conf, quadratic=False),
        "kappa_quadratic": _kappa(conf, quadratic=True),
        "patient_sens": _ratio(sums[..., PAT_TP], sums[..., PAT_POS]),
        "patient_spec": _ratio(sums[..., PAT_TN], sums[..., PAT_NEG]),
    }


def bootstrap_weights(n: int, n_boot: int, rng: np.random.Generator) -> np.ndarray:
    """(n_boot, n) patient resampling counts: each row is one cluster bootstrap replicate."""
    return rng.multinomial(n, np.full(n, 1.0 / n), size=n_boot).astype(float)


def cluster_bootstrap(
    stats: np.ndarray, n_boot: int, rng: np.random.Generator, alpha: float = 0.05
) -> Dict[str, Dict[str, float]]:
    """Point estimate and percentile CI of every endpoint, resampling patients (rows of stats)."""
    nan = float("nan")
    n = stats.shape[0]
    if n == 0:
        return {k: {"point": nan, "lower": nan, "upper": nan} for k in ENDPOINTS}
    point = endpoints(stats.sum(0))
    boot = endpoints(bootstrap_weights(n, n_boot, rng) @ stats)
    out = {}
    for k in ENDPOINTS:
        b = boot[k][~np.isnan(boot[k])]
        lo, hi = np.percentile(b, [50 * alpha, 100 - 50 * alpha]) if b.size else (nan, nan)
        out[k] = {"point": float(point[k]), "lower": float(lo), "upper": float(hi)}
    return out


# -------------------------------------------------------------------------------------------------
# The JA32 rule


def reader_agreement(read1: np.ndarray, read2: np.ndarray) -> Dict[str, float]:
    """The development anchor: exact Kim-bin agreement of two LGE readers, segments both call scar.

    It is the same statistic as the transmurality endpoint (``tbin``), so the bar compares like
    with like (JA32). Arrays are (N, S) or (S,) Kim bins.
    """
    a = np.asarray(read1, int).ravel()
    b = np.asarray(read2, int).ravel()
    both = (a > 0) & (b > 0)
    n = int(both.sum())
    agreement = float((a[both] == b[both]).mean()) if n else float("nan")
    return {"agreement": agreement, "segments": n}


def bars(anchor: Optional[float]) -> Dict[str, Optional[float]]:
    """JA32 lower-bound bars; ``tbin`` is None (reported only) if the anchor is absent or < 0.60."""
    deciding = anchor is not None and not np.isnan(anchor) and anchor >= MIN_ANCHOR
    tbin = (anchor - TBIN_MARGIN) if deciding else None
    return {"sens": SENS_BAR, "spec": SPEC_BAR, "tbin": tbin}


def decide(
    ci: Mapping[str, Mapping[str, float]], bar: Mapping[str, Optional[float]]
) -> Dict[str, object]:
    """Pass or fail per deciding endpoint, and overall (all deciding endpoints pass)."""
    per = {}
    for k, b in bar.items():
        if b is None:
            continue
        lo = ci[k]["lower"]
        per[k] = bool(not np.isnan(lo) and lo >= b)
    return {"per_endpoint": per, "passed": bool(per) and all(per.values())}


# -------------------------------------------------------------------------------------------------
# The harness


def _stack(patients: Sequence[Patient]):
    if not patients:
        raise ValueError("no patients to score")
    if len({p.ref.shape[0] for p in patients}) != 1:
        raise ValueError("every patient must have the same number of segments")
    ref = np.stack([p.ref for p in patients])
    ct = np.stack([p.ct for p in patients])
    isch = np.stack([p.ischaemic for p in patients])
    return ref, ct, isch


def _analysis(ref, ct, mask, n_boot, rng, graded_only=False):
    if graded_only:
        mask = mask & (ct != NOT_GRADED)
        ct = np.where(ct == NOT_GRADED, 0, ct)
    else:
        ct = intention_to_diagnose(ref, ct)
    keep = mask.any(1)  # a patient with no counted segment is not in this analysis's bootstrap
    st = patient_stats(ref[keep], ct[keep], mask[keep])
    res = cluster_bootstrap(st, n_boot, rng)
    tot = st.sum(0)
    res["counts"] = {
        "patients": int(len(st)),
        "positive_segments": int(tot[POS]),
        "negative_segments": int(tot[NEG]),
        "scar_on_both": int(tot[BOTH]),
    }
    return res


def _bland_altman(patients: Sequence[Patient], keep: np.ndarray) -> Optional[Dict[str, float]]:
    diffs = []
    for p, k in zip(patients, keep):
        if not k or p.ref_share is None or p.ct_share is None:
            continue
        rs = np.asarray(p.ref_share, float)
        cs = np.asarray(p.ct_share, float)
        ok = (p.ct != NOT_GRADED) & ~np.isnan(rs) & ~np.isnan(cs)
        diffs.append(cs[ok] - rs[ok])
    d = np.concatenate(diffs) if diffs else np.zeros(0)
    if d.size < 2:
        return None
    bias, sd = float(d.mean()), float(d.std(ddof=1))
    return {
        "bias": bias,
        "loa_lower": bias - 1.96 * sd,
        "loa_upper": bias + 1.96 * sd,
        "segments": int(d.size),
    }


def score(
    patients: Sequence[Patient],
    anchor: Optional[float],
    n_boot: int = 2000,
    seed: int = 20261030,
    territories: Optional[Mapping[str, Iterable[int]]] = None,
) -> Dict[str, object]:
    """Score a seal (or a development set) by JA32: the decision plus everything reported beside it.

    ``anchor`` is the development LGE inter-reader agreement (:func:`reader_agreement`). The output
    is plain JSON-ready data with counts and estimates only, never a per-patient row.
    """
    rng = np.random.default_rng(seed)
    ref, ct, isch = _stack(patients)
    n, s = ref.shape
    excluded = np.array([bool(p.strata & EXCLUDED_FROM_PRIMARY) for p in patients], bool)
    seg_primary = (ref == 0) | isch  # LGE-negative, or LGE-positive with an ischaemic pattern
    primary_mask = seg_primary & ~excluded[:, None]

    primary = _analysis(ref, ct, primary_mask, n_boot, rng)
    bar = bars(anchor)
    graded = ct != NOT_GRADED
    keep = ~excluded
    report = {
        "rule": {
            "bars_lower95": bar,
            "anchor": anchor,
            "tbin_margin": TBIN_MARGIN,
            "tbin_deciding": bar["tbin"] is not None,
            "n_boot": n_boot,
            "seed": seed,
        },
        "primary": primary,
        "decision": decide(primary, bar),
        "graded_only": _analysis(ref, ct, primary_mask, n_boot, rng, graded_only=True),
        "not_graded": {
            "segment_rate": float((~graded[keep]).mean()) if keep.any() else float("nan"),
            "patients_not_graded": int((~graded).all(1)[keep].sum()),
            "patients": int(keep.sum()),
        },
        "bland_altman_scar_share": _bland_altman(patients, keep),
        "strata": {},
        "by_protocol": {},
        "by_territory": {},
    }
    for st in STRATA:
        inn = np.array([st in p.strata for p in patients], bool)
        if inn.any():
            # a stratum is scored on all its segments, whatever the LGE pattern
            every = np.ones((int(inn.sum()), s), bool)
            report["strata"][st] = _analysis(ref[inn], ct[inn], every, n_boot, rng)
    for proto in sorted({p.protocol for p in patients}):
        inn = np.array([p.protocol == proto for p in patients], bool) & keep
        if inn.any():
            report["by_protocol"][proto] = _analysis(
                ref[inn], ct[inn], primary_mask[inn], n_boot, rng
            )
    terr = TERRITORIES if territories is None else territories
    cabg = np.array(["prior_cabg" in p.strata for p in patients], bool)  # scar yes, territory no
    for name, segs in terr.items():
        segs = [i for i in segs if i < s]
        tm = np.zeros((n, s), bool)
        tm[np.ix_(~cabg, segs)] = True
        report["by_territory"][name] = _analysis(ref, ct, primary_mask & tm, n_boot, rng)
    return report
