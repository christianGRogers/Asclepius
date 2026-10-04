"""Run the rule labeller (label.py) over cached cases; score against ImageCAS-X; write jsonl.
usage: evaluate.py EXDIR OUT.jsonl METHOD [--cases list|@file] [--lmin 20]"""
import sys, os, glob, json, argparse, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb
ap = argparse.ArgumentParser(); ap.add_argument('ex'); ap.add_argument('out'); ap.add_argument('method')
ap.add_argument('--lmin', type=float, default=20.0); ap.add_argument('--cases')
ap.add_argument('--ostw')
a = ap.parse_args()
Lb.BRIDGE = float(os.environ.get('BRIDGE', 0))
if a.ostw:
    w = json.load(open(a.ostw)); Lb.OSTIUM_W = dict(F=w['F'], mean=np.array(w['mean']), scale=np.array(w['scale']), coef=np.array(w['coef']))
files = sorted(glob.glob(os.path.join(a.ex, 'c*.npz')))
files = [f for f in files if not f.endswith('.part.npz')]
if a.cases:
    keep = set(open(a.cases[1:]).read().split(',') if a.cases.startswith('@') else a.cases.split(','))
    files = [f for f in files if os.path.basename(f)[:5] in keep]
with open(a.out, 'w') as fo:
    for f in files:
        c = os.path.basename(f)[:5]
        d = Lb.load_case(f)
        try:
            lab, olab, res, ef = Lb.label_case(d, a.method, lmin=a.lmin)
        except Exception as e:
            fo.write(json.dumps(dict(case=c, fail='exception ' + repr(e)[:150])) + '\n'); continue
        res['case'] = c
        res['nvox'] = int(d['CNT'][:, 8].sum() + (d['ORPH'][:, 3].sum() if len(d['ORPH']) else 0))
        res['zooms'] = d['zooms'].tolist()
        # how many mask voxels sit near the LM bifurcation (the only LAD/LCx/LM decision point)
        if 'bif_vox' in res:
            b = np.asarray(res['bif_vox']) * d['zooms']
            dd = np.linalg.norm(d['P'] - b, axis=1); w = d['CNT'][:, 8]
            res['frac_vox_3mm_bif'] = float(w[dd < 3].sum() / w.sum()); res['frac_vox_5mm_bif'] = float(w[dd < 5].sum() / w.sum())
            for cls in (2, 3):
                sel = lab == cls
                if sel.any():
                    D = np.abs(d['P'][sel] - b); ww = w[sel]
                    res[f'pcont_{cls}'] = {W: float((np.prod(np.clip(1 - D / W, 0, 1), axis=1) * ww).sum() / ww.sum()) for W in (64, 96, 128)}
                    res[f'never_{cls}'] = {W: float(ww[D.max(1) > W].sum() / ww.sum()) for W in (64, 96, 128)}
        if d['icx_stats'] is not None:
            res['icx'] = d['icx_stats']
            C = Lb.confusion(d, lab, olab)
            res['conf'] = C.tolist()
            res['dice'] = {k: (None if np.isnan(v) else float(v)) for k, v in Lb.dice_from_conf(C).items()}
            # ostium truth from ICX: LM-majority vertex farthest from LAD/LCx-majority vertices
            cnt = d['CNT'][:, 1:4]
            maj = np.where(cnt.sum(1) > 0, cnt.argmax(1) + 1, 0)
            Mv = np.where(maj == 1)[0]; Bv = np.where((maj == 2) | (maj == 3))[0]
            if len(Mv) and len(Bv):
                from scipy.spatial import cKDTree
                dist = cKDTree(d['P'][Bv]).query(d['P'][Mv])[0]
                ost = d['P'][Mv[np.argmax(dist)]]
                res['icx_lm_len_proxy'] = float(dist.max())
                res['ostium_err'] = float(np.linalg.norm(np.asarray(res['ostium_vox']) * d['zooms'] - ost))
                for fe in ef:
                    fe['d_true'] = float(np.linalg.norm(d['P'][fe['e']] - ost))
                res['ef'] = ef
        fo.write(json.dumps(res) + '\n')
