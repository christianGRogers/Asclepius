"""The parent copy of Janus 0's output heads (F-A2; configs/janus1/j1f_parents.json), framework-free.

Delta's round-1 rule (experiments/Delta/j1f_r1/parent_copy.py): a class Janus 0 has keeps its row; a new class copies
its parent's row; every channel of a territory gets the parent's bias minus log(k). The trainer applies the same
`source_index` / `bias_offset` to torch tensors (segtrain.nnunet_ext.parent_copy).
"""
import json
import math

import numpy as np

from . import pins

# 1-F stage-1 channels and the F-decode groups (F-A4, F-A19)
STAGE1 = ['background', 'LM', 'LAD', 'LCx', 'RCA', 'D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']
F_GROUPS = {0: (0,), 1: (1,), 2: (2, 5, 6, 7), 3: (3, 8, 9, 10), 4: (4, 11, 12)}


def load(path=None):
    with open(path or pins.PARENTS) as f:
        p = json.load(f)
    src, tgt = p['source_classes'], p['target_classes']
    if tgt[:len(src)] != src or tgt != STAGE1:
        raise ValueError(f'j1f_parents.json: target classes must be {STAGE1} and extend the source')
    for c in tgt[len(src):]:
        if p['parent'].get(c) not in src:
            raise ValueError(f'j1f_parents.json: {c} has no parent among {src}')
    if p.get('ignore_label_on_disk') != len(tgt):
        raise ValueError('j1f_parents.json: ignore on disk must be 13 (F-A29)')
    return p


def source_index(p):
    """For each target channel, the source channel it copies."""
    src = p['source_classes']
    return [src.index(c) if c in src else src.index(p['parent'][c]) for c in p['target_classes']]


def bias_offset(p):
    """-log(k) for each target channel, k = number of target channels copying the same source channel."""
    idx = source_index(p)
    return [-math.log(idx.count(i)) for i in idx]


def copy_head(W, b, p):
    """numpy: W (C_src, ...), b (C_src,) -> (W13, b13)."""
    idx = np.asarray(source_index(p))
    return np.asarray(W)[idx].copy(), np.asarray(b, float)[idx] + np.asarray(bias_offset(p))


def territory_sums(prob):
    """(13, ...) probabilities -> (5, ...) territory masses in F's groups."""
    return np.stack([prob[list(g)].sum(0) for g in F_GROUPS.values()])
