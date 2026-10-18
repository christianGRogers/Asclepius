"""Bridge, Round 9 (proposal, not binding until the judge adopts it): a pre-registered sealed A10 set drawn from
the SegQueue14 pool (D23), by patient, stratified by source, ranked by a salted sha256 so anyone can recompute it.

Strata:
  primary      adult sources whose anatomy the four-class protocol and the A1 aorta ostium are defined for;
  report_only  ImageCHD (congenital heart disease) and ImageALCAPA (left coronary from the pulmonary artery: no
               aortic left ostium, so A1 cannot place one) -- scored and reported, never decisive;
  excluded     the three sets with suspect header spacing (tF1's 1.5 mm tolerance is in mm, so a wrong spacing
               makes the score meaningless) until their spacing is fixed; HOCMvalvesSeg and CCA200-HF move to
               primary, ImageALCAPA to report_only, once fixed.
Patient key: '<Source>__<first name field>' with time-point / phase / series suffixes removed (heuristic below;
the SWE who builds it must confirm patient ids per source). Several volumes of one patient are all sealed or none;
A10 scores one volume per patient (the lowest-ranked), so the unit of n is the patient.
Usage: python3 seal_pool.py <pool.txt> <n_primary> [n_report_only] > sealed_pool.json"""
import sys, re, json, hashlib
from collections import defaultdict

SALT = 'asclepius-sealed-round9-pool:'
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}
SUFFIX = re.compile(r'(_tp\d+|_p\d+|_(diast|syst)|_s\d+)$', re.I)

pool, n_primary = sys.argv[1], int(sys.argv[2])
n_report = int(sys.argv[3]) if len(sys.argv) > 3 else 20
vols = [l.strip() for l in open(pool) if l.strip() and not l.startswith('#')]


def patient(v):
    parts = v[:-len('.nii.gz')].split('__')
    src, case = parts[0], parts[1] if len(parts) > 1 else parts[0]
    return src, f'{src}__{SUFFIX.sub("", case)}'


by_pat = defaultdict(list)
src_of = {}
for v in vols:
    s, p = patient(v)
    by_pat[p].append(v)
    src_of[p] = s
stratum = {p: ('excluded' if s in SPACING_SUSPECT else 'report_only' if s in REPORT_ONLY else 'primary')
           for p, s in src_of.items()}
rank = lambda p: hashlib.sha256((SALT + p).encode()).hexdigest()


def draw(name, n):
    pats = [p for p in by_pat if stratum[p] == name]
    by_src = defaultdict(list)
    for p in pats:
        by_src[src_of[p]].append(p)
    for s in by_src:
        by_src[s].sort(key=rank)
    # proportional allocation by largest remainder, at least one patient from any source with >= 5 patients
    tot = len(pats)
    quota = {s: n * len(v) / tot for s, v in by_src.items()}
    alloc = {s: int(q) for s, q in quota.items()}
    for s, v in by_src.items():
        if len(v) >= 5 and alloc[s] == 0:
            alloc[s] = 1
    left = n - sum(alloc.values())
    for s in sorted(quota, key=lambda s: -(quota[s] - int(quota[s]))):
        if left <= 0:
            break
        alloc[s] += 1
        left -= 1
    chosen = sorted(p for s, v in by_src.items() for p in v[:alloc[s]])
    # extension order (pre-registered): the next patients by rank, round-robin by source, if wave 1 says n is short
    ext, i = [], 0
    rest = {s: v[alloc[s]:] for s, v in by_src.items()}
    while any(rest.values()) and len(ext) < n:
        for s in sorted(rest):
            if rest[s]:
                ext.append(rest[s].pop(0))
    return chosen, ext, {s: [alloc[s], len(v)] for s, v in sorted(by_src.items())}


prim, prim_ext, prim_alloc = draw('primary', n_primary)
rep, _, rep_alloc = draw('report_only', n_report)
out = {
    'salt': SALT, 'pool_list': pool, 'n_volumes': len(vols), 'n_patients': len(by_pat),
    'patients_per_stratum': {k: sum(1 for p in by_pat if stratum[p] == k) for k in ('primary', 'report_only', 'excluded')},
    'primary': {'n_patients': len(prim), 'n_volumes': sum(len(by_pat[p]) for p in prim),
                'allocation_[sealed,total]_by_source': prim_alloc, 'patients': prim,
                'volumes': sorted(v for p in prim for v in by_pat[p]),
                'scoring_volume': {p: min(by_pat[p], key=rank) for p in prim},
                'extension_order': prim_ext},
    'report_only': {'n_patients': len(rep), 'allocation_[sealed,total]_by_source': rep_alloc, 'patients': rep,
                    'volumes': sorted(v for p in rep for v in by_pat[p]),
                    'scoring_volume': {p: min(by_pat[p], key=rank) for p in rep}},
    'multi_volume_patients': {p: v for p, v in by_pat.items() if len(v) > 1},
}
json.dump(out, sys.stdout, indent=1)
