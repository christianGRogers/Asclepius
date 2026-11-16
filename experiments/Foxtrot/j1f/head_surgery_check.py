"""Janus 1-F (Foxtrot v1): two checks on CPU for the proposed warm start and loss.

1. Head surgery. Janus 0's last layer (each deep-supervision head) is a 1x1x1 conv: logits z = W x + b over
   {bg, LM, LAD, LCx, RCA}. Grow it to 1-F's classes by giving every child of parent P (P itself included) P's row of
   W and the bias b_P - log k_P (k_P = number of classes under P). Then sum_{c in P} softmax(z')_c = softmax(z)_P for
   every voxel: the four-vessel collapse of the new network equals Janus 0 exactly at step 0.
2. Marginal (set-valued) cross-entropy. Target = a SET of allowed classes per voxel; loss = -log sum_{c in set} p_c.
   A singleton set is ordinary CE; the full set gives zero loss (= ignore); a parent set gives no pressure between
   that parent's children. Checked against PyTorch-free finite differences.
Usage: python3 head_surgery_check.py"""
import numpy as np

rng = np.random.default_rng(0)
FOUR = ['bg', 'LM', 'LAD', 'LCx', 'RCA']
CHILD = {'bg': ['bg'], 'LM': ['LM'], 'LAD': ['LAD', 'D1', 'D2', 'D3'], 'LCx': ['LCx', 'OM1', 'OM2', 'Ramus'],
         'RCA': ['RCA', 'PDA', 'PLB']}  # round-1 1-F head (13 outputs: background + 12 classes); S1-S3, SN, Conus, RMA join later the same way
NEW = [c for p in FOUR for c in CHILD[p]]
sm = lambda z: np.exp(z - z.max(-1, keepdims=True)) / np.exp(z - z.max(-1, keepdims=True)).sum(-1, keepdims=True)

W = rng.normal(size=(5, 32)); b = rng.normal(size=5); x = rng.normal(size=(10000, 32)) * 3
p4 = sm(x @ W.T + b)
W2 = np.stack([W[FOUR.index(p)] for p in FOUR for _ in CHILD[p]])
b2 = np.array([b[FOUR.index(p)] - np.log(len(CHILD[p])) for p in FOUR for _ in CHILD[p]])
p13 = sm(x @ W2.T + b2)
coll = np.stack([p13[:, [NEW.index(c) for c in CHILD[p]]].sum(1) for p in FOUR], 1)
err = np.abs(coll - p4).max()
print(f"1. head surgery: {len(NEW)} outputs (bg + {len(NEW)-1} classes); max |collapse(p_new) - p_Janus0| over 10000 voxels = {err:.2e}")
assert err < 1e-12


def mce(z, allowed):
    """marginal CE for one voxel: z logits, allowed boolean mask over classes."""
    p = sm(z); return -np.log(p[allowed].sum())


def grad(z, allowed):
    p = sm(z); q = np.where(allowed, p, 0) / p[allowed].sum(); return p - q  # d/dz of -log sum_allowed p


z = rng.normal(size=len(NEW))
for name, cls in [('singleton LAD', ['LAD']), ('parent set {LAD,D1,D2,D3}', CHILD['LAD']), ('all classes', NEW)]:
    a = np.isin(NEW, cls)
    num = np.array([(mce(z + e, a) - mce(z - e, a)) / 2e-6 for e in np.eye(len(NEW)) * 1e-6])
    g = grad(z, a)
    within = g[a]; ratio = within / sm(z)[a]
    print(f'2. {name:28s} loss {mce(z, a):.4f}  |grad - finite diff| {np.abs(num - g).max():.1e}  '
          f'grad/p inside the set constant: {np.ptp(ratio) < 1e-9}')
    assert np.abs(num - g).max() < 1e-6
print('   (a constant grad/p inside the set means the loss moves the set as a whole and never re-ranks its members)')
