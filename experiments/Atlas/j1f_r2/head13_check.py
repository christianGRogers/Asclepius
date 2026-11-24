"""Janus 1-F round 2 (Atlas): F-A2/F-A4's step-0 identity for the ADOPTED 13-output head (bg, LM, LAD, LCx, RCA,
D1, D2, D3, OM1, OM2, Ramus, PDA, PLB), on random Janus-0-like logits (5 channels, N voxels).
Parent copy: each child copies its parent's logit row; every member of a territory gets bias - log(k_territory)
(k: LAD 4, LCx 4, RCA 3). Checks: territory probability sums equal Janus 0's softmax (max abs error); the hierarchical
decode's territory equals Janus 0's argmax on every voxel; the share of voxels whose PLAIN 13-way argmax lands in
another territory than Janus 0's argmax. Usage: python head13_check.py"""
import numpy as np
rng = np.random.default_rng(0)
N = 2_000_000
for scale in (1, 3, 10):
    print(f'--- logit scale {scale}')
    z0 = rng.normal(0, scale, (5, N))
    par = [0, 1, 2, 3, 4, 2, 2, 2, 3, 3, 3, 4, 4]       # parent of each of the 13 outputs
    terr = np.array(par)
    k = {0: 1, 1: 1, 2: 4, 3: 4, 4: 3}
    z = z0[par] - np.log([k[t] for t in par])[:, None]
    def sm(a):
        a = a - a.max(0); e = np.exp(a); return e / e.sum(0)
    p0, p = sm(z0), sm(z)
    sums = np.stack([p[terr == t].sum(0) for t in range(5)])
    err = float(np.abs(sums - p0).max())
    hier = sums.argmax(0)
    j0 = p0.argmax(0)
    plain = terr[p.argmax(0)]
    print(f'max |territory sum - Janus 0| = {err:.2e}')
    print(f'hierarchical territory == Janus 0 argmax: {(hier == j0).mean():.6f}')
    print(f'plain 13-way argmax moves {(plain != j0).mean() * 100:.2f} % of voxels to another territory')
    fg = j0 > 0
    print(f'  of Janus 0 foreground voxels: {(plain[fg] != j0[fg]).mean() * 100:.2f} %')
    