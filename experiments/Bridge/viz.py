"""Scatter-render skeleton vertices: rule labels (top) vs ImageCAS-X majority labels (bottom); anterior + superior views (RAS)."""
import sys, os, numpy as np
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import label as Lb
COL = np.array(['#000000', '#e6b800', '#e62828', '#2878ff', '#28c850', '#c800c8', '#999999', '#dddddd'])
ex, out, method = sys.argv[1], sys.argv[2], sys.argv[3]
for c in sys.argv[4:]:
    d = Lb.load_case(os.path.join(ex, c + '.npz'))
    lab, olab, res, ef = Lb.label_case(d, method)
    cnt = d['CNT'][:, :8]; icx = np.where(cnt[:, 1:7].sum(1) > 0, cnt[:, 1:7].argmax(1) + 1, 7)
    X = d['RAS']; s = 2 + 3 * d['R']
    fig, ax = plt.subplots(2, 2, figsize=(10, 9))
    for i, L in enumerate((lab, icx)):
        ax[i, 0].scatter(-X[:, 0], X[:, 2], c=COL[L], s=s); ax[i, 0].set_title(f'{c} {"rule" if i == 0 else "ICX"} anterior view (patient L on right)')
        ax[i, 1].scatter(-X[:, 0], X[:, 1], c=COL[L], s=s); ax[i, 1].set_title('superior view (anterior up)')
        o = np.asarray(res['ostium_vox']) @ d['A'][:3, :3].T + d['A'][:3, 3]
        for a, (u, v) in zip(ax[i], ((0, 2), (0, 1))):
            a.plot(-o[0] if u == 0 else o[u], o[v], 'kx', ms=12, mew=3); a.set_aspect('equal'); a.set_xticks([]); a.set_yticks([])
    plt.tight_layout(); plt.savefig(os.path.join(out, f'{c}_{method}.png'), dpi=55); plt.close()
