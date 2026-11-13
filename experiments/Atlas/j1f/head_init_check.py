"""Janus 1-F round 1 (Atlas): the 'parent-copy' warm start for new branch-type outputs, checked numerically.

Janus 0's last 1x1x1 conv gives 5 logits (bg, LM, LAD, LCx, RCA). Janus 1-F's head has 10 (phase 1: + D, OM, Ramus,
PDA, PLB) or 14 (phase 2: + S, SN, Conus, RMA). Each new type copies its parent's weights and bias, and every member of
a decode group (the parent and its k-1 types) gets bias - log(k). Then for every voxel the summed probability of each
group equals Janus 0's probability of the parent.

A plain argmax over the outputs does NOT reproduce Janus 0 (a group split k ways loses log k against background), so
1-F decodes hierarchically: group = argmax of summed group probabilities (identical to Janus 0 at init), then the type
= argmax within the group (the parent at init: equal logits, lowest index wins).

Decode groups are an initialisation device only. PDA, PLB and SN sit in the RCA group at init; after training an
LCx-origin PDA is still decoded as PDA (its mass makes the RCA group win). The four-class collapse used for scoring is
by origin (D25), done on the decoded label map, not by decode group.
Random features and Janus 0-like weights; exact up to float error. numpy only. Usage: python head_init_check.py"""
import numpy as np

# 0 bg, 1 LM, 2 LAD, 3 LCx, 4 RCA, then the types
PHASES = {
    'phase 1 (10 outputs)': {5: 2, 6: 3, 7: 3, 8: 4, 9: 4},                    # D, OM, Ramus, PDA, PLB
    'phase 2 (14 outputs)': {5: 2, 6: 3, 7: 3, 8: 4, 9: 4, 10: 2, 11: 4, 12: 4, 13: 4},  # + S, SN, Conus, RMA
}
rng = np.random.default_rng(0)
C_FEAT, NVOX = 32, 200_000
W0, b0 = rng.normal(size=(5, C_FEAT)), rng.normal(size=5)
x = rng.normal(size=(NVOX, C_FEAT)) * 3
z0 = x @ W0.T + b0
p0 = np.exp(z0 - z0.max(1, keepdims=True)); p0 /= p0.sum(1, keepdims=True)
lab0 = z0.argmax(1)
for name, PARENT in PHASES.items():
    K = 5 + len(PARENT)
    W1, b1 = np.zeros((K, C_FEAT)), np.zeros(K)
    W1[:5], b1[:5] = W0, b0
    for t, par in PARENT.items():
        W1[t], b1[t] = W0[par], b0[par]
    members = {par: [par] + [t for t, q in PARENT.items() if q == par] for par in range(1, 5)}
    for par, mem in members.items():
        b1[mem] -= np.log(len(mem))
    z1 = x @ W1.T + b1
    p1 = np.exp(z1 - z1.max(1, keepdims=True)); p1 /= p1.sum(1, keepdims=True)
    grp = np.zeros((NVOX, 5)); grp[:, 0] = p1[:, 0]
    for c in range(1, K):
        grp[:, PARENT.get(c, c)] += p1[:, c]
    plain = np.array([PARENT.get(c, c) for c in range(K)])[z1.argmax(1)]
    g_lab = grp.argmax(1)
    typ = g_lab.copy()
    for par, mem in members.items():
        sel = g_lab == par
        typ[sel] = np.array(mem)[p1[sel][:, mem].argmax(1)]
    print(f'{name}: group sizes {[len(m) for m in members.values()]}')
    print(f'  max |group prob - Janus 0 prob| = {np.abs(grp - p0).max():.2e}')
    print(f'  plain argmax: voxels whose group differs from Janus 0: {int((plain != lab0).sum())} of {NVOX} '
          f'({100 * (plain != lab0).mean():.1f} %)')
    print(f'  hierarchical: voxels whose group differs from Janus 0: {int((g_lab != lab0).sum())}; '
          f'voxels given a branch type at init: {int((typ >= 5).sum())}')
    assert np.abs(grp - p0).max() < 1e-9 and (g_lab == lab0).all() and not (typ >= 5).any()
print('OK')
