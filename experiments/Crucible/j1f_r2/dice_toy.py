"""Janus 1-F round 2 (Crucible), item 4: which Dice term lets an untraced class be learned, in a CPU toy whose
proportions come from the 620 (band volumes from census620.py) and whose losses are nnU-Net's (per-sample soft Dice,
smooth 1e-5, background excluded, batch 2, plus CE).

Classes: 0 bg, 1 P (a traced parent, e.g. LAD), 2 S (an untraced child, e.g. a septal). One shared linear-softmax
"network" on 3 voxel features (vesselness, calibre, proximity to a parent) is trained on three kinds of image:
  * ICX (620): P singleton; S and band background -> {bg, S} inside the band; S beyond the band and far background
    -> {bg} (ImageCAS-X never traced S, so S is background there);
  * EXT (n_ext): an extended pool read, complete: every voxel singleton;
  * C4  (n_4c): a four-class pool read: P and S -> {P, S}; background {bg}.
CE term: marginal CE, -log sum_{c in set} p_c (Shi et al.). Dice term, one of:
  * leaf     : Fidon et al. Eq. 4 per sample: target_c = [set == {c}], prediction p_c on every voxel;
  * marginal : Fidon et al.'s Baseline 3 ("merged mass"): on a set voxel containing c, prediction = sum_{k in set} p_k
               and target 1;
  * ignore   : set-valued voxels leave the Dice term entirely (numerator and denominator), as nnU-Net's ignore label;
  * leaf_skip: leaf, but class c's Dice is dropped on a sample where c has no singleton voxel (c not annotated);
  * none     : CE only;
  * oracle   : every image fully labelled (ceiling of this toy);
  * naive    : no label sets at all: S is background in ICX, {P,S} -> P in C4 (training ImageCAS-X as drawn).
Measured on held-out, fully labelled images: S Dice, S recall and precision at argmax, P Dice.
Usage: dice_toy.py <census620.jsonl or -> <out.json>"""
import json, sys
import numpy as np
import torch

torch.set_num_threads(1)
SMOOTH = 1e-5


def band_ratio(path):
    """Median background volume inside the LAD band, per mm^3 of LAD tree, at 8 and 15 mm (from the census)."""
    if path == '-':
        return {'8': 12.0, '15': 35.0}
    r8, r15 = [], []
    for l in open(path):
        r = json.loads(l)
        b = r['bands']
        lt = r['class_mm']['LAD'] + r['class_mm']['D1'] + r['class_mm']['D2'] + r['class_mm']['D3']
        tv = r['bands']['tree_mm3'] * (lt / max(sum(r['class_mm'].values()), 1e-6))
        if tv > 0 and 'LADtree' in b['8']:
            r8.append(b['8']['LADtree'] / tv)
            r15.append(b['15']['LADtree'] / tv)
    return {'8': float(np.median(r8)), '15': float(np.median(r15))}


def make_image(rng, kind, band, s_in_band, ratio, present=0.9):
    """Voxel groups with features, weights (voxel counts) and label sets (bitmask over 3 classes)."""
    nP, nS = 300.0, 60.0 if rng.random() < present else 0.0
    nB = ratio[band] * (nP + nS) if band != '0' else 0.0
    nF = 40 * (nP + nS)
    g = []

    def grp(n_samples, total, mu, sd, truth):
        if total <= 0:
            return
        x = rng.normal(mu, sd, (n_samples, 3))
        g.append((x, np.full(n_samples, total / n_samples), truth))
    grp(60, nP, (2.0, 1.5, 3.0), (1, .7, .5), 1)
    if nS:
        sin = nS * (s_in_band if band != '0' else 0.0)
        grp(30, sin, (2.0, -1.0, 2.0), (1, .7, .5), 2)        # S inside the band
        grp(30, nS - sin, (2.0, -1.0, 0.6), (1, .7, .5), 2)   # S beyond the band (far from the parent)
    grp(100, nB, (0.0, 0.0, 1.5), (1, 1, .5), 0)              # background inside the band
    grp(200, nF, (0.0, 0.0, -1.0), (1, 1, .8), 0)             # far background
    X = np.concatenate([a for a, _, _ in g])
    W = np.concatenate([w for _, w, _ in g])
    T = np.concatenate([np.full(len(a), t) for a, _, t in g])
    inb = np.concatenate([np.full(len(a), i in ((1,) if not nS else (1, 3)) or (nS and i == 1)) for i, (a, _, _) in
                          enumerate(g)])
    # band membership by group index: groups are [P, S_in, S_out, B, F] (S groups only if nS)
    idx = []
    names = ['P'] + (['S_in', 'S_out'] if nS else []) + (['B'] if nB > 0 else []) + ['F']
    for nm, (a, _, _) in zip(names, g):
        idx += [nm] * len(a)
    idx = np.array(idx)
    del inb
    full = np.array([1, 2, 4])[T]
    if kind == 'EXT':
        sets = full
    elif kind == 'C4':
        sets = np.where(np.isin(T, (1, 2)), 2 | 4, 1)
    elif kind == 'ICX':
        sets = np.where(T == 1, 2, np.where(np.isin(idx, ('S_in', 'B')), 1 | 4, 1))
    elif kind == 'ICX_naive':
        sets = np.where(T == 1, 2, 1)
    elif kind == 'C4_naive':
        sets = np.where(np.isin(T, (1, 2)), 2, 1)
    return X.astype(np.float32), W.astype(np.float32), sets, T


def loss_fn(logits, W, sets, dice):
    p = torch.softmax(logits, 1)
    M = torch.tensor(np.stack([(sets >> k) & 1 for k in range(3)], 1).astype(np.float32))
    w = torch.tensor(W)
    ce = -(torch.log((p * M).sum(1) + 1e-12) * w).sum() / w.sum()
    if dice == 'none':
        return ce
    single = M.sum(1) == 1
    ds = []
    for c in (1, 2):
        if dice in ('leaf', 'leaf_skip', 'naive'):
            tgt = M[:, c] * single
            if dice == 'leaf_skip' and tgt.sum() == 0:
                continue
            pr = p[:, c]
            keep = torch.ones_like(pr)
        elif dice == 'ignore':
            tgt = M[:, c] * single
            pr = p[:, c]
            keep = single.float()
        elif dice == 'marginal':
            setv = ~single & (M[:, c] > 0)
            tgt = M[:, c] * single + setv.float()
            pr = torch.where(setv, (p * M).sum(1), p[:, c])
            keep = torch.ones_like(pr)
        inter = (pr * tgt * keep * w).sum()
        den = ((pr + tgt) * keep * w).sum()
        ds.append((2 * inter + SMOOTH) / torch.clamp(den + SMOOTH, min=1e-8))
    return ce - (torch.stack(ds).mean() if ds else 0.0)


def feats(X):
    return torch.tensor(np.concatenate([X, X ** 2, X[:, :1] * X[:, 1:2], X[:, 1:2] * X[:, 2:3]], 1))


def run(dice, band, s_in_band, n_ext, n_4c, ratio, steps=1500, seed=0):
    rng = np.random.default_rng(seed)
    torch.manual_seed(seed)
    naive = dice == 'naive'
    if dice == 'oracle':   # ceiling: every image fully labelled (what 620 + n extended reads of everything would give)
        imgs = [make_image(rng, 'EXT', band, s_in_band, ratio) for _ in range(620 + n_ext + n_4c)]
        n_ext = n_4c = 0
        dice = 'leaf'
    else:
        imgs = [make_image(rng, 'ICX_naive' if naive else 'ICX', band, s_in_band, ratio) for _ in range(620)]
    imgs += [make_image(rng, 'EXT', band, s_in_band, ratio) for _ in range(n_ext)]
    imgs += [make_image(rng, 'C4_naive' if naive else 'C4', band, s_in_band, ratio) for _ in range(n_4c)]
    lin = torch.nn.Linear(8, 3)
    with torch.no_grad():   # parent-copy start: S starts as a copy of P, both biased by -log 2
        lin.weight[2] = lin.weight[1]
        lin.bias[2] = lin.bias[1] - np.log(2)
        lin.bias[1] -= np.log(2)
    opt = torch.optim.Adam(lin.parameters(), lr=0.02)
    F = [feats(x) for x, _, _, _ in imgs]
    for _ in range(steps):
        tot = 0.0
        for i in rng.integers(0, len(imgs), 2):     # batch 2, per-sample Dice, uniform sampling over images
            x, w, s, _ = imgs[i]
            tot = tot + loss_fn(lin(F[i]), w, s, 'leaf' if naive else dice)
        opt.zero_grad()
        (tot / 2).backward()
        opt.step()
    # evaluation on 200 fully labelled images
    trng = np.random.default_rng(10_000 + seed)
    tp = np.zeros(3); fp = np.zeros(3); fn = np.zeros(3)
    with torch.no_grad():
        for _ in range(200):
            x, w, _, T = make_image(trng, 'EXT', band if band != '0' else '8', s_in_band, ratio)
            pr = lin(feats(x)).argmax(1).numpy()
            for c in (1, 2):
                tp[c] += w[(pr == c) & (T == c)].sum()
                fp[c] += w[(pr == c) & (T != c)].sum()
                fn[c] += w[(pr != c) & (T == c)].sum()
    dsc = lambda c: float(2 * tp[c] / max(2 * tp[c] + fp[c] + fn[c], 1e-9))
    return {'S_dice': round(dsc(2), 3), 'S_recall': round(float(tp[2] / max(tp[2] + fn[2], 1e-9)), 3),
            'S_precision': round(float(tp[2] / max(tp[2] + fp[2], 1e-9)), 3), 'P_dice': round(dsc(1), 3)}


if __name__ == '__main__':
    ratio = band_ratio(sys.argv[1] if len(sys.argv) > 1 else '-')
    print(json.dumps(grad_check()))
    out = {'band_ratio_bg_per_tree_mm3': ratio, 'runs': []}
    grid = [(band, sib) for band, sib in (('0', 0.0), ('8', 0.5), ('15', 0.8))]
    for dice in ('oracle', 'naive', 'none', 'leaf', 'leaf_skip', 'marginal', 'ignore'):
        for band, sib in grid:
            for n_ext in (10, 30, 60):
                res = [run(dice, band, sib, n_ext, 100, ratio, seed=s) for s in range(5)]
                agg = {k: [round(float(np.mean([r[k] for r in res])), 3), round(float(np.std([r[k] for r in res])), 3)]
                       for k in res[0]}
                row = {'dice': dice, 'band_mm': band, 'S_share_in_band': sib, 'n_ext': n_ext, **agg}
                out['runs'].append(row)
                print(json.dumps(row), flush=True)
    json.dump(out, open(sys.argv[2], 'w'), indent=1)


def grad_check():
    """nnU-Net's per-sample soft Dice on a patch where class c has no target voxel: dc = smooth / (sum_p + smooth),
    so d(-dc)/d(sum_p) = smooth / (sum_p + smooth)^2. Printed for predicted masses of 0.01 to 1000 voxels, beside the
    gradient of the same term when c has 50 target voxels and is half predicted."""
    rows = []
    for sp_ in (0.01, 0.1, 1, 10, 100, 1000):
        g0 = SMOOTH / (sp_ + SMOOTH) ** 2
        rows.append({'sum_pred_vox': sp_, 'grad_no_target': g0})
    # with a target of 50 voxels, prediction 25 inside, sum_pred 25: dc = 2*25/(75); d dc / d p_inside
    I, G, P = 25.0, 50.0, 25.0
    g_in = (2 * (G + P) - 2 * I) / (G + P) ** 2
    return {'no_target': rows, 'with_target_50_half_predicted_grad_per_voxel_inside': g_in}
