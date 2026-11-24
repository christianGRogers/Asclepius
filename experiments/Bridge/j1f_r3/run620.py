"""Round 2 ruling §5 item 1 (and F-A17, F-A18), on the 620 D45 training cases only.

For each training case: reference = the D47 (A) stage-1 map (Atlas's `stage1_labels`, the converter the gate census
used; F-A18's expected counts are checked on the totals). Then, with the scorer of record (`j1f_scorer.py`, this dir):
  * pieces_of(ref): per class, number of pieces and their lengths -> compared row by row with Atlas's
    `census_r2.jsonl`, the piece distribution F-A15's lines were simulated on;
  * collapse4(ref) (SegQueue's function) against D25's `territory.to_four` on every voxel outside "Other" and 255,
    and the fallback count;
  * score_case(ref, ref): every piece detected and named, presence agrees (the identity), and which pieces sit in a
    case whose class is NOT present at 5 mm (they enter recall's denominator but not the locked counts).
Never opens a locked, sealed or quality-0 case: ids come from split.json's train620 (D45), re-checked against the pin.
Usage: python3 run620.py <icx_dir> <out.jsonl> [n_proc]"""
import hashlib, json, os, sys, time
from multiprocessing import Pool
import nibabel as nib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import j1f_scorer as S  # noqa: E402
sys.path.insert(0, os.path.join(HERE, '../../../trillium/icx4/lib'))
import territory  # noqa: E402
import importlib.util  # noqa: E402
_sp = importlib.util.spec_from_file_location('atlas_scorer', os.path.join(HERE, '../../Atlas/j1f_r2/j1f_scorer.py'))
A = importlib.util.module_from_spec(_sp); _sp.loader.exec_module(A)
PIN620 = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'
MARGIN = 8


def one(args):
    d, c = args
    t0 = time.time()
    im = nib.load(os.path.join(d, 'segmentations', f'{int(c[1:]) + 1}.coronary.nii.gz'))
    icx = np.asarray(im.dataobj).astype(np.uint8)
    z = np.array(im.header.get_zooms()[:3], float)
    nz = np.argwhere(icx > 0)
    lo, hi = np.maximum(nz.min(0) - MARGIN, 0), nz.max(0) + MARGIN + 1
    icx = icx[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]
    ref, info = A.stage1_labels(icx, z)
    st = {}
    c4 = S.collapse4(ref, z, st)
    d25 = territory.to_four(icx, z)
    m = (icx > 0) & (icx != 14) & (ref != S.IGNORE)
    rp = S.pieces_of(ref, z)
    sc = S.score_case(ref, ref, z, with_tf1=False, ref_pieces=rp)
    row = {'case': c, 'other': info, 'collapse_mismatch_vox': int((c4[m] != d25[m]).sum()),
           'collapse_fallback': st['fallback'], 'collapse_components': st['components'],
           'pieces': {S.NAMES[k]: [round(p['length_mm'], 2) for p in v] for k, v in rp.items()},
           'pieces_vox': {S.NAMES[k]: [p['vox'] for p in v] for k, v in rp.items()},
           'identity': {k: {'n': len(v['pieces']), 'det': sum(p['detected'] for p in v['pieces']),
                            'named': sum(p['named'] for p in v['pieces']),
                            'pres_ref': v['present_ref'], 'pres_pred': v['present_pred']} for k, v in sc.items()},
           'shape': list(icx.shape), 'zooms': z.tolist(), 't_s': round(time.time() - t0, 1)}
    return row


def main(d, outp, n):
    sp = json.load(open(os.path.join(d, 'split.json')))
    ids = sorted(sp['train620'])
    assert len(ids) == 620 and hashlib.sha256('\n'.join(ids).encode()).hexdigest() == PIN620
    done = set()
    if os.path.exists(outp):
        done = {json.loads(l)['case'] for l in open(outp)}
    todo = [(d, c) for c in ids if c not in done]
    with open(outp, 'a') as f, Pool(n) as p:
        for i, r in enumerate(p.imap_unordered(one, todo)):
            f.write(json.dumps(r) + '\n'); f.flush()
            if i % 20 == 0:
                print(i, len(todo), r['case'], r['t_s'], flush=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], int(sys.argv[3]) if len(sys.argv) > 3 else 3)
