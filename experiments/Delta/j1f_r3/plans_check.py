"""Janus 1-F round 3 (Delta): L-A21's plans check, carried into 1-F (F-A20), pinned to Step T's posted hashes (#302).

  plans_check.py <janus0_plans.json> <dataset719_plans.json> [<janus0_fingerprint.json> <placed_fingerprint.json>]

Refuses (exit 2) unless:
  * Janus 0's plans.json has Step T's sha256 (b7178bbc...3cc2) and its fingerprint e41c772f...7e05;
  * Dataset 719's plans equal Janus 0's once `dataset_name` and `image_reader_writer` are removed (what
    `nnUNetv2_move_plans_between_datasets -sp X -tp X` rewrites; `plans_name` is unchanged when -tp equals -sp);
  * 3d_fullres `batch_dice` is False (Step T posted False; F-A21's leaf-Dice per sample relies on it);
  * the placed fingerprint is byte-identical to Janus 0's.
Self-test: python plans_check.py selftest
"""
import copy, hashlib, json, sys

PLANS_SHA256 = 'b7178bbc6d86e658e449b72cef7621f06de222c107083a2622792d346bd93cc2'
FINGERPRINT_SHA256 = 'e41c772faf5e58a31d44cfc948031354dde6d0070a900a1ebfdb14691f937e05'
REWRITTEN = ('dataset_name', 'image_reader_writer')


def _strip(p):
    q = copy.deepcopy(p)
    for k in REWRITTEN:
        q.pop(k, None)
    return q


def check(j0_bytes, t_bytes, fp0_bytes=None, fp_bytes=None, pins=True):
    errs = []
    if pins and hashlib.sha256(j0_bytes).hexdigest() != PLANS_SHA256:
        errs.append("Janus 0's plans.json is not Step T's (sha256)")
    j0, t = json.loads(j0_bytes), json.loads(t_bytes)
    if _strip(j0) != _strip(t):
        diff = sorted(k for k in set(j0) | set(t) if k not in REWRITTEN and j0.get(k) != t.get(k))
        errs.append(f'plans differ beyond {REWRITTEN}: {diff}')
    if t.get('configurations', {}).get('3d_fullres', {}).get('batch_dice') is not False:
        errs.append('3d_fullres batch_dice is not False')
    if fp0_bytes is not None:
        if pins and hashlib.sha256(fp0_bytes).hexdigest() != FINGERPRINT_SHA256:
            errs.append("Janus 0's dataset_fingerprint.json is not Step T's (sha256)")
        if fp_bytes != fp0_bytes:
            errs.append('placed dataset_fingerprint.json differs from Janus 0s')
    return errs


def selftest():
    j0 = {'dataset_name': 'Dataset715_ICX4', 'plans_name': 'nnUNetResEncUNetPlans_60G_iso05',
          'image_reader_writer': 'SimpleITKIO', 'configurations': {'3d_fullres': {'batch_dice': False,
          'spacing': [0.5, 0.5, 0.5], 'patch_size': [256, 256, 256]}},
          'foreground_intensity_properties_per_channel': {'0': {'percentile_00_5': -100.0}}}
    b0 = json.dumps(j0).encode()
    t = dict(j0, dataset_name='Dataset719_J1F', image_reader_writer='NibabelIOWithReorient')
    assert check(b0, json.dumps(t).encode(), pins=False) == []
    bad = copy.deepcopy(t); bad['foreground_intensity_properties_per_channel']['0']['percentile_00_5'] = -99.0
    assert check(b0, json.dumps(bad).encode(), pins=False), 'a changed percentile must refuse'
    bd = copy.deepcopy(t); bd['configurations']['3d_fullres']['batch_dice'] = True
    assert check(b0, json.dumps(bd).encode(), pins=False)
    assert check(b0, json.dumps(t).encode(), pins=True), 'pins: a plans file that is not Step T s must refuse'
    assert check(b0, json.dumps(t).encode(), b'{}', b'{ }', pins=False)
    print('plans_check selftest ok')


if __name__ == '__main__':
    if sys.argv[1:] == ['selftest']:
        selftest()
    else:
        a = [open(p, 'rb').read() for p in sys.argv[1:]]
        e = check(*a)
        print('\n'.join(e) if e else 'plans check OK')
        sys.exit(2 if e else 0)
