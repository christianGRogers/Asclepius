"""`predict`'s input folders: the locked 100's CTs linked into 10 chunks of 10 (sorted ids), never into Dataset 719
(F-A29). Writes <work>/in_l100/chunk<k>/<case>_0000.nii.gz and chunk<k>.json; refuses any non-locked id in a chunk
folder, a missing CT, or chunks that are not 10 x 10.

  python -m janus1f.predict_inputs <work> <layout.json>
"""
import json
import os
import sys

from . import pins, split

CHUNK = 10


def chunks(locked):
    ids = sorted(locked)
    return [ids[i:i + CHUNK] for i in range(0, len(ids), CHUNK)]


def build(work, layout_json, sp=None):
    sp = sp or split.load()
    cases = pins.load_json(layout_json)['cases']
    root = os.path.join(work, 'in_l100')
    ch = chunks(sp['locked100'])
    if len(ch) != 10 or any(len(c) != CHUNK for c in ch):
        raise split.SplitError('the locked 100 must make 10 chunks of 10')
    miss = [c for c in sp['locked100'] if c not in cases or not os.path.exists(cases[c]['ct'])]
    if miss:
        raise split.SplitError(f'no CT for {len(miss)} locked case(s), e.g. {miss[:3]}; fetch with icx4\'s steps')
    for k, ids in enumerate(ch):
        d = os.path.join(root, f'chunk{k}')
        os.makedirs(d, exist_ok=True)
        for c in ids:
            p = os.path.join(d, f'{c}_0000.nii.gz')
            if not os.path.lexists(p):
                os.symlink(cases[c]['ct'], p)
        present = sorted(f[:-len('_0000.nii.gz')] for f in os.listdir(d))
        split.refuse_unlocked(present, sp, f'predict input chunk{k}')
        if present != ids:
            raise split.SplitError(f'chunk{k} holds {present[:3]}..., not its 10 locked ids')
        with open(os.path.join(root, f'chunk{k}.json'), 'w') as f:
            json.dump(ids, f)
    print(f'[janus1f] predict inputs: 10 chunks of 10 locked CTs in {root}', flush=True)
    return ch


if __name__ == '__main__':
    try:
        build(sys.argv[1], sys.argv[2])
    except (split.SplitError, pins.PinError) as e:
        sys.exit(f'[janus1f] REFUSE: {e}')
