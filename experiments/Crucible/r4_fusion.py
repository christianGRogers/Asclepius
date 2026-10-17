# Round 4: what does each way of using TWO reads per case teach a model, and how should the reference be defined?
# Uses the r4_reads.py noise model (calibration in the note). For each case:
#   - two "real" reads A, B (as the team would deliver) and K extra reads from the same noise model;
#   - the label a well-trained model converges to under each training scheme, estimated as the per-voxel MODE of the
#     scheme's target over many draws (CE's population optimum is the mode of the target distribution):
#       single/both  : target = one read            -> mode over K reads (both reads = same optimum, 2x samples)
#       union        : target = either-read vessel; class conflict -> ignore -> mode over K/2 pair-unions
#       agree        : target = voxels where the pair agrees, else ignore      -> mode over agreeing pairs only
#   - scored with tF1@1.5 (r2_eval.score, D3 tolerance) against: truth T, each read (mean of vs-A and vs-B),
#     and the inter-rater ceiling (B scored against A).
# Usage: python r4_fusion.py K MAXCASES
import sys, json, os, numpy as np
from scipy import ndimage as ndi
from skimage.morphology import skeletonize
sys.path.insert(0, '/home/user/Asclepius/experiments/Crucible')
_argv = sys.argv; sys.argv = ['x']
exec(open('/home/user/Asclepius/experiments/Crucible/r4_reads.py').read().split("if __name__")[0])
import r2_eval as E  # noqa: E402  (module-level code in r2_eval only defines helpers + reads meta)
sys.argv = _argv
K, NMAX = int(sys.argv[1]), int(sys.argv[2])
OUT = SCR + '/work/Crucible/r4fusion'; os.makedirs(OUT, exist_ok=True)


def mode(stack):  # stack: (n, ...) uint8 with 255 = ignore; per-voxel most frequent non-ignore label (0 if none)
    cnt = np.stack([(stack == k).sum(0) for k in range(5)])
    tot = cnt.sum(0); m = cnt.argmax(0).astype(np.uint8); m[tot == 0] = 0; return m


def union(a, b):
    u = np.where(a == b, a, 0).astype(np.uint8)
    one = (a == 0) ^ (b == 0); u[one & (a > 0)] = a[one & (a > 0)]; u[one & (b > 0)] = b[one & (b > 0)]
    u[(a > 0) & (b > 0) & (a != b)] = 255; return u


def agree(a, b): return np.where(a == b, a, 255).astype(np.uint8)


def tf1(ref, pred, sp, rts):
    sk = skeletonize(ref > 0); s = E.score(ref, pred, sp, sk, rts, 1.5)
    return float(np.mean([v['tf1'] for v in s.values()])), {k: round(v['tf1'], 3) for k, v in s.items()}


rows = []
for c in sorted(meta)[:NMAX]:
    if os.path.exists(f'{OUT}/{c}.json'): rows.append(json.load(open(f'{OUT}/{c}.json'))); continue
    lab = np.load(f'{D}/{c}_lab.npy'); sp = np.array(meta[c]['spacing'])
    T = ((lab >> 4) & 7).astype(np.uint8); m = T > 0; L14 = lab & 15
    u = np.argwhere(m); lo = np.maximum(u.min(0) - 3, 0); hi = u.max(0) + 4
    sl = tuple(slice(a, b) for a, b in zip(lo, hi)); T = T[sl]; m = m[sl]; L14 = L14[sl]
    _, ind = ndi.distance_transform_edt(L14 == 0, return_indices=True); near14 = L14[tuple(ind)]
    rad = ndi.distance_transform_edt(m, sampling=sp); sk = skeletonize(m)
    _, ind2 = ndi.distance_transform_edt(~sk, return_indices=True); rad_local = rad[tuple(ind2)] * m
    roots = ostia(T, sp); rng = np.random.default_rng(1000 + int(c[1:]))
    reads = [make_read(T, near14, sp, rad_local, roots, rng)[0] for _ in range(K + 2)]
    A, B = reads[0], reads[1]; extra = np.stack(reads[2:])
    pairs = [(extra[i], extra[i + 1]) for i in range(0, K - 1, 2)]
    P = {'single_or_both': mode(extra),
         'union': mode(np.stack([union(a, b) for a, b in pairs])),
         'agree': mode(np.stack([agree(a, b) for a, b in pairs])),
         'truth_T': T}
    rts = [np.array(r) for r in roots]
    r = {'case': c}
    r['inter_rater_B_vs_A'], r['inter_pc'] = tf1(A, B, sp, rts)
    for name, p in P.items():
        r[f'{name}_vs_T'], _ = tf1(T, p, sp, rts)
        a1, _ = tf1(A, p, sp, rts); b1, _ = tf1(B, p, sp, rts); r[f'{name}_vs_reads'] = (a1 + b1) / 2
        r[f'{name}_fg_vs_T'] = float((p > 0).sum() / m.sum())
    r['A_fg_vs_T'] = float((A > 0).sum() / m.sum())
    json.dump(r, open(f'{OUT}/{c}.json', 'w')); rows.append(r); print(json.dumps(r), flush=True)
json.dump(rows, open(OUT + '/all.json', 'w'))
