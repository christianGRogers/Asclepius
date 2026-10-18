"""Stage C, after prediction: check all predictions, then Dice on the open ImageCAS-X test cases only.
  * every prediction must load; unreadable ones (a job killed mid-write) are deleted so the next chunk redoes them;
  * Dice (per class, whole tree, detection) against ImageCAS-X collapsed to the four classes exactly as prepare.py
    collapses the training labels, on open-36 and dev-44 only (sealed.py, A14). The 80 sealed test cases and the
    20 sealed quality-0 cases are predicted but never scored, and their predictions are not summarised;
  * a per-case table of which classes each prediction contains, for the SegQueue hand-off, written to the
    workdir (all cases) and to results/ (non-sealed cases only).
Usage: score.py <workdir> <icx_dir> <results_dir> <n_proc>   (exit 3 = predictions missing or broken or seal refused)
Writes <workdir>/dice_per_case.json; report.py turns it into results/."""
import os, sys, json
from multiprocessing import Pool
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from territory import to_four  # noqa: E402
import sealed  # noqa: E402

NAMES = ['LM', 'LAD', 'LCx', 'RCA']
PRED = ICX = None
SEALED, GROUP = set(), {}


def init(w, icx, sealed_cases, group):
    """Set the worker globals (also the Pool initializer, so nothing depends on fork)."""
    global PRED, ICX, SEALED, GROUP
    PRED, ICX, SEALED, GROUP = f'{w}/predictions', icx, set(sealed_cases), dict(group)


def dice(a, b):
    s = int(a.sum()) + int(b.sum())
    return None if s == 0 else 2.0 * int((a & b).sum()) / s


def check(c):
    p = f'{PRED}/{c}.nii.gz'
    if not os.path.exists(p):
        return c, None
    try:
        a = np.asarray(nib.load(p).dataobj)
    except Exception:
        os.remove(p)
        return c, None
    return c, [int(v) for v in np.unique(a) if v]


def reference(c):
    """ImageCAS-X for case c, collapsed to the four classes exactly as for training. Returns (labels, zooms)."""
    li = nib.load(os.path.join(ICX, f'{int(c[1:]) + 1}.coronary.nii.gz'))
    z = li.header.get_zooms()[:3]
    return to_four(np.asarray(li.dataobj).astype(np.int64), z).astype(np.uint8), z


def score(c):
    if c in SEALED:   # unreachable (the case list is sealed.scored_groups); kept as the last guard
        raise RuntimeError(f'refusing to score sealed case {c}')
    pr = np.asarray(nib.load(f'{PRED}/{c}.nii.gz').dataobj).astype(np.uint8)
    rf, _ = reference(c)
    if pr.shape != rf.shape:
        raise ValueError(f'{c}: prediction {pr.shape} vs ImageCAS-X {rf.shape}')
    r = {'case': c, 'group': GROUP[c], 'tree': dice(pr > 0, rf > 0), 'cls': {}}
    for k, n in enumerate(NAMES, 1):
        a, b = pr == k, rf == k
        r['cls'][n] = {'dice': dice(a, b), 'in_ref': bool(b.any()), 'in_pred': bool(a.any())}
    return r


if __name__ == '__main__':
    W, icx, OUT, NP = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])
    cases = json.load(open(f'{W}/layout.json'))['cases']
    try:
        S = sealed.load(f'{W}/sealed_test.json')
        GROUPS = sealed.scored_groups(S, sealed.icx_test_ids(icx), set(cases))
    except sealed.SealedError as e:
        print(f'[score] {e}', flush=True)
        sys.exit(3)
    args = (W, icx, sealed.sealed_set(S), sealed.group_of(GROUPS))
    init(*args)
    os.makedirs(OUT, exist_ok=True)

    with Pool(NP, initializer=init, initargs=args) as p:
        present = dict(p.map(check, sorted(cases)))
    missing = [c for c, v in present.items() if v is None]
    index = {'n_cases': len(present), 'missing': missing,
             'classes_per_case': {c: [NAMES[k - 1] for k in v] for c, v in present.items() if v is not None}}
    json.dump(index, open(f'{W}/predictions_index_all.json', 'w'))   # workdir only: includes sealed cases
    index['classes_per_case'] = {c: v for c, v in index['classes_per_case'].items() if c not in SEALED}
    index['sealed_cases_omitted'] = sum(c in SEALED for c in present)
    json.dump(index, open(f'{OUT}/predictions_index.json', 'w'))
    if missing:
        print(f'[score] {len(missing)} of {len(present)} predictions missing or unreadable (first {missing[:5]})')
        sys.exit(3)

    todo = sealed.refuse_sealed([c for g in sealed.GROUPS for c in GROUPS[g]], S, 'score')
    print(sealed.describe(S, GROUPS).replace('[icx4]', '[score]'), flush=True)
    with Pool(NP, initializer=init, initargs=args) as p:
        rows = p.map(score, todo)
    json.dump(rows, open(f'{W}/dice_per_case.json', 'w'))
    print(f'[score] Dice for {len(rows)} open cases -> {W}/dice_per_case.json', flush=True)
