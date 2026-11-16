"""Janus 1-F round 1 (Delta): parent-copy initialisation of the output layer, and its self-test.

Janus 0's output layer has 5 channels (background, LM, LAD, LCx, RCA). Janus 1-F stage 1 has 13 (background, LM, LAD,
LCx, RCA, D1, D2, D3, OM1, OM2, Ramus, PDA, PLB); stage 2 adds S1-S3, SN, Conus and RMA. Every new channel is a copy
of its parent's channel, and the k channels of a territory (the parent and its children) each get the parent's bias
minus log(k), as in MiB's classifier initialisation (Cermelli et al., CVPR 2020, arXiv:2002.00718, Sec. 3.3, which
splits the background this way).

Property (tested below): at step 0, for every voxel, the softmax mass of each territory equals Janus 0's probability
of that territory, so the 1-F model collapsed to four classes is exactly Janus 0. Training only has to break the
ties inside a territory; it never has to rediscover the territory, which is what icx14 spent 440 epochs on.

The same function adds stage 2's classes to a stage-1 model (parents then come from the stage-1 head).
The arrays are framework-free (numpy); in nnU-Net this applies to every `decoder.seg_layers.<i>` weight (C, F, 1, 1, 1)
and bias (C,) of the ResEnc U-Net (deep supervision included) after `-pretrained_weights` loads the rest; nnU-Net's
own loader skips the seg layers (`load_pretrained_weights`), so this replaces that skip.

Usage: python parent_copy.py     # self-test
"""
import numpy as np

JANUS0 = ['background', 'LM', 'LAD', 'LCx', 'RCA']
STAGE1 = JANUS0 + ['D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
STAGE2 = STAGE1 + ['S1', 'S2', 'S3', 'SN', 'Conus', 'RMA']
PARENT = {'D1': 'LAD', 'D2': 'LAD', 'D3': 'LAD', 'S1': 'LAD', 'S2': 'LAD', 'S3': 'LAD',
          'OM1': 'LCx', 'OM2': 'LCx', 'Ramus': 'LCx',
          'PDA': 'RCA', 'PLB': 'RCA', 'SN': 'RCA', 'Conus': 'RCA', 'RMA': 'RCA'}


def parent_copy(W, b, old, new):
    """W: (C_old, ...) weights, b: (C_old,) biases of a 1x1x1 conv; old/new: class-name lists (new extends old).
    Returns (W_new, b_new). A class already in `old` keeps its own row; a new class copies its parent's row; the
    biases of a territory are lowered by log(size of the territory in `new` / size in `old`), applied to every
    member, so the territory's total softmax mass is unchanged."""
    assert new[:len(old)] == old
    src = []
    for c in new:
        if c in old:
            src.append(old.index(c))
        else:
            p = PARENT[c]
            while p not in old:
                p = PARENT[p]
            src.append(old.index(p))
    src = np.array(src)
    W2, b2 = W[src].copy(), b[src].astype(float).copy()
    # territory of each new channel = the old channel it copies or is
    for j in range(len(old)):
        members = np.where(src == j)[0]
        b2[members] = b[j] - np.log(len(members))
    return W2, b2


def softmax(z, axis=0):
    z = z - z.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def collapse(p, names, to):
    """Sum channel probabilities into the `to` classes by parent."""
    out = np.zeros((len(to),) + p.shape[1:])
    for i, c in enumerate(names):
        t = c
        while t not in to:
            t = PARENT[t]
        out[to.index(t)] += p[i]
    return out


def selftest():
    rng = np.random.default_rng(0)
    F, V = 32, 10000
    W0, b0 = rng.normal(size=(5, F)), rng.normal(size=5)
    x = rng.normal(size=(F, V)) * 3
    p0 = softmax(W0 @ x + b0[:, None])
    W1, b1 = parent_copy(W0, b0, JANUS0, STAGE1)
    p1 = softmax(W1 @ x + b1[:, None])
    e1 = np.abs(collapse(p1, STAGE1, JANUS0) - p0).max()
    W2, b2 = parent_copy(W1, b1, STAGE1, STAGE2)
    p2 = softmax(W2 @ x + b2[:, None])
    e2 = np.abs(collapse(p2, STAGE2, JANUS0) - p0).max()
    e21 = np.abs(collapse(p2, STAGE2, STAGE1) - p1).max()
    # argmax of the collapsed output equals Janus 0's argmax (the four-class prediction is unchanged)
    same = (collapse(p1, STAGE1, JANUS0).argmax(0) == p0.argmax(0)).mean()
    # inside a territory the children start tied with the parent
    lad = [STAGE1.index(c) for c in ('LAD', 'D1', 'D2', 'D3')]
    tie = np.abs(p1[lad] - p1[lad].mean(0)).max()
    print(f'stage 1 collapse vs Janus 0: max |dp| {e1:.2e}; argmax agreement {same:.4f}; LAD-territory tie {tie:.2e}')
    print(f'stage 2 collapse vs Janus 0: max |dp| {e2:.2e}; stage 2 collapsed to stage 1 vs stage 1 (all 13 '
          f'channels): {e21:.2e}')
    assert e1 < 1e-9 and e2 < 1e-9 and e21 < 1e-9 and same == 1.0 and tie < 1e-12
    print('parent_copy self-test: PASS')


if __name__ == '__main__':
    selftest()
