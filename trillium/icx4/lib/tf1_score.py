"""Stage C3 (CPU): the decisive score (A1, A1a, A1b, A1c, A15) on the open ImageCAS-X test cases (issue #54).

* Cases: open-36 and dev-44 only, from lib/sealed.py (A14). A sealed case is refused, never scored.
* Metric: lib/segtrain_tf1.py, a verbatim copy of src/segtrain/tf1.py; refused unless its sha256 is TF1_SHA256
  (A1c, Round 8). The launcher and the job check the same hash.
* Reference: ImageCAS-X collapsed to the four classes exactly as for training (territory.to_four).
* Ostium of record: the reference centreline voxel nearest the TotalSegmentator aorta (A1; lib/aorta.py). A case
  without an aorta mask is still scored but provisional, and decides nothing (A1a).
* Per case and class: tF1 @ 1.5 mm (D3, decisive) and @ 0 mm, recall/precision, flagged classes (a tree whose
  ostium rules disagree, A1b: reported apart), classes_without_centreline (scored on the fallback centreline, the
  decisive default since Round 8), and raw FP components (A15).
As atlas2 does, every volume is cropped to the reference + prediction box plus 15 mm before scoring.
Idempotent: one JSON per case in <workdir>/tf1.d/. Errors are not cached (the next job retries them).
Usage: tf1_score.py <workdir> <icx_dir> <n_proc>   (exit 3 = refused: hash or seal; exit 1 = errors)"""
import hashlib
import json
import os
import sys
import time
from multiprocessing import Pool

import numpy as np
import nibabel as nib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sealed  # noqa: E402
from territory import to_four  # noqa: E402

#: A1c (Round 8): the only tF1 that may decide. The launcher (icx4) and the job carry the same value.
TF1_SHA256 = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'
TF1_PATH = os.path.join(HERE, 'segtrain_tf1.py')
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
SIDE_OF = {1: 'left', 2: 'left', 3: 'left', 4: 'right'}
CROP_MARGIN_MM = 15.0
T = None   # the frozen metric module, loaded by load_metric() after the hash check


def tf1_hash(path=TF1_PATH):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def load_metric():
    """Import segtrain_tf1 only if its hash is the frozen one (else RuntimeError)."""
    global T
    h = tf1_hash()
    if h != TF1_SHA256:
        raise RuntimeError(f'{TF1_PATH} has sha256 {h}, not the frozen {TF1_SHA256} (A1c): refusing to score')
    import segtrain_tf1
    T = segtrain_tf1
    return T


def _bbox(masks, sp, shape):
    u = np.zeros(shape, bool)
    for m in masks:
        u |= m
    if not u.any():
        return tuple(slice(0, s) for s in shape)
    idx = [np.nonzero(u.any(axis=tuple(j for j in range(3) if j != k)))[0] for k in range(3)]
    mv = np.ceil(CROP_MARGIN_MM / sp).astype(int)
    lo = np.maximum([a[0] for a in idx] - mv, 0)
    hi = np.minimum([a[-1] + 1 for a in idx] + mv, shape)
    return tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))


def classes_flagged(ref, report):
    """A1b: the reference classes whose tree carries a flagged ostium (by component and side), as atlas2."""
    comp, _ = T.components(ref > 0)
    out = set()
    for o in report.ostia:
        if not o.flagged:
            continue
        on = comp == o.tree
        for c in NAMES:
            if (o.side == 'tree' or o.side == SIDE_OF[c]) and np.any(on & (ref == c)):
                out.add(c)
    return sorted(out)


def score_arrays(ref, pred, sp, aorta=None, ct=None):
    """The A1 row for one case from arrays on one grid (ref, pred: 4-class uint8; aorta: bool; ct: HU)."""
    if T is None:
        load_metric()
    sp = np.asarray(sp, float)
    sl = _bbox([ref > 0, pred > 0], sp, ref.shape)
    ref, pred = ref[sl], pred[sl]
    aorta = aorta[sl] if aorta is not None else None
    ct = ct[sl] if ct is not None else None
    rep = T.find_ostia(ref, sp, aorta=aorta, ct=ct)
    r15 = T.tree_f1(ref, pred, sp, tol_mm=T.TOLERANCE_MM, ostia=rep)
    r0 = T.tree_f1(ref, pred, sp, tol_mm=0.0, ostia=rep)
    nm = lambda d: {NAMES[int(c)]: float(v) for c, v in d.items()}  # noqa: E731
    return dict(tf1=float(r15.tf1), tf1_tol0=float(r0.tf1), per_class=nm(r15.per_class),
                per_class_tol0=nm(r0.per_class), recall=nm(r15.recall), precision=nm(r15.precision),
                rooted_fraction=float(r15.rooted_fraction), provisional=bool(rep.provisional),
                flagged_classes=[NAMES[c] for c in classes_flagged(ref, rep)],
                classes_without_centreline=[NAMES[int(c)] for c in r15.classes_without_centreline],
                centreline_fallback=bool(r15.centreline_fallback),
                fp_components=int(T.fp_components(ref, pred)), ostia=[o.as_row() for o in rep.ostia],
                crop_offset=[s.start for s in sl])


def _load(path, dtype):
    img = nib.load(path)
    return np.asanyarray(img.dataobj).astype(dtype), img


def score_case(c, pred_path, icx_path, aorta_path=None, ct_path=None):
    pred, _ = _load(pred_path, np.uint8)
    icx, li = _load(icx_path, np.int64)
    sp = np.array(li.header.get_zooms()[:3], float)
    ref = to_four(icx, sp).astype(np.uint8)
    if pred.shape != ref.shape:
        raise ValueError(f'{c}: prediction {pred.shape} vs ImageCAS-X {ref.shape}')
    aorta = _load(aorta_path, np.uint8)[0] > 0 if aorta_path and os.path.exists(aorta_path) else None
    ct = _load(ct_path, np.float32)[0] if ct_path and os.path.exists(ct_path) else None
    for name, a in (('aorta', aorta), ('ct', ct)):
        if a is not None and a.shape != ref.shape:
            raise ValueError(f'{c}: {name} grid {a.shape} vs ImageCAS-X {ref.shape}')
    return dict(case=c, spacing=sp.tolist(), has_aorta=aorta is not None, has_ct=ct is not None,
                **score_arrays(ref, pred, sp, aorta=aorta, ct=ct))


CTX = {}


def init(ctx):
    CTX.update(ctx)
    load_metric()


def one(c):
    if c in CTX['sealed']:   # unreachable (the list is sealed.scored_groups); the last guard
        raise RuntimeError(f'refusing to score sealed case {c}')
    W, f = CTX['W'], f"{CTX['W']}/tf1.d/{c}.json"
    if os.path.exists(f):
        return json.load(open(f))
    t = time.time()
    try:
        r = score_case(c, f'{W}/predictions/{c}.nii.gz', os.path.join(CTX['icx'], f'{int(c[1:]) + 1}.coronary.nii.gz'),
                       aorta_path=f'{W}/aorta/{c}_aorta.nii.gz', ct_path=CTX['ct'].get(c))
    except Exception as e:
        print(f'[tf1] {c} ERROR {e!r}'[:400], flush=True)
        return dict(case=c, group=CTX['group'][c], error=repr(e)[:500])
    r.update(group=CTX['group'][c], sec=round(time.time() - t, 1))
    json.dump(r, open(f + '.part', 'w'))
    os.replace(f + '.part', f)
    print(f"[tf1] {c} ({r['group']}) tF1 {r['tf1']:.3f}{' provisional' if r['provisional'] else ''} "
          f"{r['sec']:.0f}s", flush=True)
    return r


if __name__ == '__main__':
    W, icx, NP = sys.argv[1], sys.argv[2], int(sys.argv[3])
    try:
        load_metric()
        S = sealed.load(f'{W}/sealed_test.json')
        L = json.load(open(f'{W}/layout.json'))['cases']
        groups = sealed.scored_groups(S, sealed.icx_test_ids(icx), set(L))
        todo = sealed.refuse_sealed([c for g in sealed.GROUPS for c in groups[g]], S, 'tf1')
    except (RuntimeError, sealed.SealedError) as e:
        print(f'[tf1] {e}', flush=True)
        sys.exit(3)
    print(f'[tf1] segtrain_tf1 sha256 {TF1_SHA256} = frozen (A1c); '
          f'{len(groups["open36"])} open-36 + {len(groups["dev44"])} dev-44 cases, {NP} workers', flush=True)
    os.makedirs(f'{W}/tf1.d', exist_ok=True)
    ctx = dict(W=W, icx=icx, sealed=sealed.sealed_set(S), group=sealed.group_of(groups),
               ct={c: L[c]['ct'] for c in todo})
    with Pool(NP, initializer=init, initargs=(ctx,), maxtasksperchild=4) as p:
        rows = p.map(one, todo, chunksize=1)
    ok, err = [r for r in rows if 'error' not in r], [r for r in rows if 'error' in r]
    json.dump(dict(tf1_sha256=TF1_SHA256, per_case=ok, errors=err), open(f'{W}/tf1_per_case.json', 'w'))
    print(f'[tf1] {len(ok)} scored, {len(err)} errors -> {W}/tf1_per_case.json', flush=True)
    sys.exit(1 if err else 0)
