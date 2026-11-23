"""Janus 1-F round 3 (judge): the five proposed L2 forms on a CORRECT stage-2 branch that the model draws with a gap.

Round 3's advocates all tested L2 on correct branches that are drawn whole. A real network also draws a correct thin
branch in pieces (Atlas's round-2 erosion finding: whole D1s vanish at one voxel). This script asks which L2 form a
correct-but-broken branch passes. CPU, D45's 620 TRAINING labels only (the split pin is asserted; no locked, sealed,
quality-0 or D60 file is opened).

Per case, for each host, one traced side branch stands in for a stage-2 class (as Foxtrot v3 §6.1): D2 (LAD), OM2 (LCx),
PLB collapsing to the RCA (RCA). Its largest piece is relabelled 13 (a stage-2 class); everything else stays as the
reference (stage-1 classes). Three versions:
  whole   the stand-in as drawn;
  gap3    the stand-in with a 3 mm gap cut at half its geodesic length (voxels whose geodesic distance from the host
          lies in [L/2, L/2 + 3 mm] removed);
  gap8    the same with an 8 mm gap.
Per stage-2 26-component of >= 20 voxels it records:
  d1    the nearest distance (mm) to stage-1 foreground (every predicted voxel that is not stage-2);
  dall  the nearest distance (mm) to every other predicted coronary voxel (stage-1 and other stage-2 components);
  touch whether it 26-touches any other predicted voxel.
The forms (a case FAILS if any component meets the condition):
  Bridge L2'   d1 > 5 mm
  Atlas P-r3-2 / Crucible   d1 > 30 mm
  Delta L2'    not touch and d1 > 30 mm
  Foxtrot L2d  dall > 30 mm
`summarise` draws 2 000 random 100-case sets and applies ">= 95 of 100 cases clean" (point count).
Usage: python l2_forms.py run <icx620_dir> <split_j1l.json> <out.jsonl> [n_proc] [n_cases=120]
       python l2_forms.py summarise <out.jsonl> <summary.json>"""
import hashlib, json, os, sys
from multiprocessing import Pool
import nibabel as nib
import numpy as np
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '../../Atlas/j1f_r3'))
import j1f_scorer as S  # noqa: E402  (the scorer of record; its import asserts the tf1.py and labels.py pins)

STANDIN = {'LAD': (2, 6), 'LCx': (3, 9), 'RCA': (4, 12)}
GAPS = {'whole': 0.0, 'gap3': 3.0, 'gap8': 8.0}


def _versions(lab, c4, host, z):
    trunk, cls = STANDIN[host]
    m = lab == cls
    if host == 'RCA':
        m &= c4 == 4
    comp, nc = ndi.label(m, S.S26)
    if not nc:
        return None
    sizes = ndi.sum(m, comp, range(1, nc + 1))
    piece = comp == (1 + int(np.argmax(sizes)))
    if piece.sum() < S.MIN_PIECE_VOX:
        return None
    seeds = np.argwhere(piece & ndi.binary_dilation(lab == trunk, S.S26))
    if not len(seeds):                                   # attached to its host only through another branch
        seeds = np.argwhere(piece & ndi.binary_dilation((lab > 0) & ~piece & (lab != S.IGNORE), S.S26))
    if not len(seeds):
        return None
    g = S._geodesic(piece, seeds, z)
    L = float(np.max(g[np.isfinite(g)]))
    out = {}
    for name, w in GAPS.items():
        p = piece.copy()
        if w:
            p &= ~((g >= L / 2) & (g < L / 2 + w))
        pred = lab.copy()
        pred[piece] = 0
        pred[p] = 13
        out[name] = pred
    return out, round(L, 1)


def _measure(pred, z):
    """Distances are computed in the component's box + 31 mm; anything farther is recorded as 99 (both lines,
    5 mm and 30 mm, are inside that window, so no decision depends on the cap)."""
    s2 = pred == 13
    fg = (pred > 0) & (pred != S.IGNORE)
    s1 = fg & ~s2
    comp, nc = ndi.label(s2, S.S26)
    objs = ndi.find_objects(comp)
    mg = np.ceil(31.0 / z).astype(int)
    rows = []
    for i in range(1, nc + 1):
        sl = objs[i - 1]
        box = tuple(slice(max(s.start - mg[k], 0), min(s.stop + mg[k], pred.shape[k])) for k, s in enumerate(sl))
        p = comp[box] == i
        if p.sum() < S.MIN_PIECE_VOX:
            continue
        other = fg[box] & ~p
        one = s1[box]
        dall = float(ndi.distance_transform_edt(~other, sampling=z)[p].min()) if other.any() else 99.0
        d1 = float(ndi.distance_transform_edt(~one, sampling=z)[p].min()) if one.any() else 99.0
        touch = bool((ndi.binary_dilation(p, S.S26) & other).any())
        rows.append({'d1': round(min(d1, 99.0), 2), 'dall': round(min(dall, 99.0), 2), 'touch': touch,
                     'vox': int(p.sum())})
    return rows


def one(path):
    c = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    im = nib.load(path)
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    nz = ndi.find_objects((icx > 0).astype(np.uint8))[0]
    mg = np.ceil(36.0 / z).astype(int)
    icx = icx[tuple(slice(max(s.start - mg[k], 0), min(s.stop + mg[k], icx.shape[k])) for k, s in enumerate(nz))]
    lab, _ = S.stage1_labels(icx, z)
    c4 = S.collapse4(lab, z)
    row = {'case': c}
    for host in STANDIN:
        v = _versions(lab, c4, host, z)
        if v is None:
            continue
        preds, L = v
        row[host] = {'len_mm': L, **{k: _measure(p, z) for k, p in preds.items()}}
    return row


FORMS = {
    'Bridge L2prime (d1 > 5)': lambda r: r['d1'] > 5,
    'Atlas/Crucible (d1 > 30)': lambda r: r['d1'] > 30,
    'Delta L2prime (no touch, d1 > 30)': lambda r: (not r['touch']) and r['d1'] > 30,
    'Foxtrot L2d (dall > 30)': lambda r: r['dall'] > 30,
}


def summarise(inp, out, draws=2000):
    rows = [json.loads(l) for l in open(inp)]
    rows.sort(key=lambda r: r['case'])
    rng = np.random.default_rng(20261123)
    res = {'cases': len(rows), 'draws': draws, 'rule': '>= 95 of 100 cases clean (point count)', 'hosts': {}}
    for host in STANDIN:
        hr = [r[host] for r in rows if host in r]
        h = {'cases_with_standin': len(hr), 'len_mm_median': float(np.median([r['len_mm'] for r in hr]))}
        for ver in GAPS:
            for fname, f in FORMS.items():
                fail = np.array([any(f(c) for c in r[ver]) for r in hr])
                rates = []
                for _ in range(draws):
                    idx = rng.choice(len(fail), 100, replace=False)
                    rates.append(fail[idx].sum() > 5)
                h[f'{ver} | {fname}'] = {'cases_failing': int(fail.sum()), 'share': round(float(fail.mean()), 4),
                                         'P(false-fail)': round(float(np.mean(rates)), 4)}
        res['hosts'][host] = h
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res, indent=1))


def main(d, split, out, npr=4, n=120):
    sp = json.load(open(split))
    train = sorted(sp['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == \
        '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
    assert not set(train) & set(sp['locked100'])
    # n training cases with the smallest sha256('asclepius-j1f-r3-judge-l2:' + id)
    train = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r3-judge-l2:' + c).encode()).hexdigest())[:n]
    paths = [os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in train]
    assert all(os.path.exists(p) for p in paths)
    with Pool(npr, maxtasksperchild=20) as pool, open(out, 'w') as f:
        for r in pool.imap_unordered(one, paths):
            f.write(json.dumps(r) + '\n'); f.flush()


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'run':
        main(a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 4, int(a[5]) if len(a) > 5 else 120)
    else:
        summarise(a[1], a[2])
