"""Self-test of fuse_reads.py on real projected-proxy labels with simulated second reads (not evidence about real
annotators; it checks that the A10/A11 code does what the rules say). Usage: fuse_reads_selftest.py <label.nii.gz> ..."""
import sys, json
import numpy as np, nibabel as nib
from scipy import ndimage as ndi
sys.path.insert(0, '/home/user/Asclepius/experiments/Atlas')
import fuse_reads as F

def crop(A):
    idx = np.nonzero(A); lo = np.maximum([i.min() - 8 for i in idx], 0); hi = [i.max() + 9 for i in idx]
    return A[lo[0]:hi[0], lo[1]:hi[1], lo[2]:hi[2]]

for p in sys.argv[1:]:
    im = nib.load(p); sp = np.array(im.header.get_zooms()[:3], float); A = crop(np.asarray(im.dataobj).astype(np.uint8))
    car = F._carina(A, sp); out = dict(case=p.split('/')[-1])
    if car is None:
        print(json.dumps(dict(case=out['case'], skipped='no LM')), flush=True); continue
    g = np.indices(A.shape).reshape(3, -1).T
    dist = np.linalg.norm((g - car) * sp, axis=1).reshape(A.shape)
    sims = {}
    B = A.copy(); B[(A == 3) & (dist <= 5)] = 2; sims['carina_shift_5mm'] = B
    B = A.copy(); rz = np.nonzero(A == 4)[2]
    if len(rz):
        cut = np.percentile(rz, 15); B[(A == 4) & (np.indices(A.shape)[2] < cut)] = 0
    sims['rca_distal_truncation'] = B
    B = A.copy(); B[(A == 3) & (dist <= 12)] = 2; sims['carina_branch_12mm'] = B
    B = A.copy(); B[A == 2] = 3; B[A == 3] = 2; sims['lad_lcx_swapped'] = B
    for k, B in sims.items():
        a, b = F.a11_samples(A, B); ag = F.agree_or_ignore(A, B)
        adj = F.adjudication(A, B, sp)
        out[k] = dict(ignore_frac_a11=float((a == F.IGNORE).sum() / max((A > 0).sum(), 1)),
                      ignore_frac_agree=float((ag == F.IGNORE).sum() / max((A > 0).sum(), 1)),
                      extent_kept=int(((A > 0) != (B > 0)).sum()), needed=adj['needed'], ramus_only=adj['ramus_only'],
                      triggers=adj['triggers'], inter_read_tf1=round(adj['inter_read_tf1'], 3), swap=round(adj['ladlcx_swap'], 3))
        if k == 'carina_shift_5mm':
            s = F.case_score(A, A, B, sp); out[k]['score_pred_eq_A'] = round(s['tf1'], 3)
    print(json.dumps(out), flush=True)
# acceptance on synthetic per-case values
rng = np.random.default_rng(1)
inter = [{c: 0.85 + 0.05 * rng.standard_normal() for c in (1, 2, 3, 4)} for _ in range(100)]
good = [{c: v + 0.01 for c, v in i.items()} for i in inter]; bad = [{c: v - 0.05 for c, v in i.items()} for i in inter]
print('acceptance good', {c: r['passed'] for c, r in F.acceptance(good, inter).items()},
      'bad', {c: r['passed'] for c, r in F.acceptance(bad, inter).items()})
