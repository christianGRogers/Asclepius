"""The D45 split (pinned, #306 §1), the guards on it, the fit-check 20 (F-A5) and `splits_final.json` (F-A20).

  configs/janus1/split-2026-11.json   sha256 19b832fe...4dd3 (byte copy of experiments/Delta/j1l_r1/...proposal.json)
  train620                            sha256 of the sorted ids 1350cb1f...1152 (F0-r2 line 1)
  locked100                           bbd9c687...d5895 (F0-r2 line 2)

`rederive` recomputes the split from ImageCAS-X's own file lists and the sealed list, as F0-r2 does on Fir
(experiments/Foxtrot/j1f/split620.py), so `check` can re-print F0-r2's first two lines from the copy `prep` uses.
"""
import hashlib
import json
import os

from . import pins

FITCHECK_SALT = 'asclepius-j1f-fitcheck:'
LOCKED_SALT = 'asclepius-janus1-locked100:'


class SplitError(RuntimeError):
    """A locked, sealed or unknown id where it may not be; or a split that is not the pinned one."""


def load(path=None, sealed_path=None):
    """The pinned split as {'train620': [...], 'locked100': [...], 'sealed': set}. Refuses on any pin mismatch."""
    path = path or pins.SPLIT
    if path == pins.SPLIT:
        pins.check_file(path, pins.SPLIT_SHA256, 'the D45 split')
    d = pins.load_json(path)
    train, locked = sorted(d['train620']), sorted(d['locked100'])
    if len(train) != 620 or len(set(train)) != 620 or len(locked) != 100 or len(set(locked)) != 100:
        raise SplitError('the split must hold 620 training and 100 locked ids')
    if pins.ids_sha256(train) != pins.TRAIN620_SHA256:
        raise SplitError(f'train620 sha256 {pins.ids_sha256(train)} != {pins.TRAIN620_SHA256}')
    if pins.ids_sha256(locked) != pins.LOCKED100_SHA256:
        raise SplitError(f'locked100 sha256 {pins.ids_sha256(locked)} != {pins.LOCKED100_SHA256}')
    if set(train) & set(locked):
        raise SplitError('train620 and locked100 overlap')
    sealed = load_sealed(sealed_path)
    hit = (set(train) | set(locked)) & sealed
    if hit:
        raise SplitError(f'sealed id in the split: {sorted(hit)[:3]}')
    return {'train620': train, 'locked100': locked, 'sealed': sealed}


def load_sealed(path=None):
    """The 80 sealed ImageCAS-X test cases and the 20 sealed quality-0 cases (A14). Missing = refuse."""
    path = path or pins.SEALED
    try:
        s = pins.load_json(path)
    except (OSError, ValueError) as e:
        raise SplitError(f'sealed list {path} is missing or unreadable ({e!r}); refusing') from e
    a, b = s.get('sealed_icx_test'), s.get('sealed_quality0')
    if not isinstance(a, list) or len(set(a)) != 80 or not isinstance(b, list) or len(set(b)) != 20:
        raise SplitError(f'sealed list {path}: expected 80 sealed test and 20 quality-0 ids')
    return set(a) | set(b)


def refuse_training(ids, sp, what='training'):
    """Raise SplitError unless every id is one of the 620 (so: no locked, no sealed, no unknown id)."""
    ids = list(ids)
    train, locked, sealed = set(sp['train620']), set(sp['locked100']), sp['sealed']
    bad_sealed = sorted(set(ids) & sealed)
    bad_locked = sorted(set(ids) & locked)
    unknown = sorted(set(ids) - train - locked - sealed)
    if bad_sealed:
        raise SplitError(f'refusing: sealed id(s) in {what}: {bad_sealed[:3]}')
    if bad_locked:
        raise SplitError(f'refusing: locked-100 id(s) in {what}: {bad_locked[:3]}')
    if unknown:
        raise SplitError(f'refusing: id(s) outside the D45 620 in {what}: {unknown[:3]}')
    return len(ids)


def refuse_unlocked(ids, sp, what='the locked predict input'):
    """Raise unless every id is a locked-100 id (predict's input folder holds exactly those)."""
    bad = sorted(set(ids) - set(sp['locked100']))
    if bad:
        raise SplitError(f'refusing: non-locked id(s) in {what}: {bad[:3]}')
    return len(ids)


def fitcheck_ids(train620):
    """F-A5: the 20 training cases with the smallest sha256('asclepius-j1f-fitcheck:' + id), sorted."""
    ranked = sorted(train620, key=lambda c: hashlib.sha256((FITCHECK_SALT + c).encode()).hexdigest())
    return sorted(ranked[:20])


def splits_final(sp):
    """F-A20: two identical entries, train = the 620, val = the 20 fit-check cases (inside the 620)."""
    tr = sorted(sp['train620'])
    val = fitcheck_ids(tr)
    if hashlib.sha256('\n'.join(val).encode()).hexdigest() != pins.FITCHECK20_SHA256:
        raise SplitError('the fit-check 20 do not hash to F-A5 / Delta v3 3f3b696c...1330')
    entry = {'train': tr, 'val': val}
    return [entry, json.loads(json.dumps(entry))]


def check_splits_final(splits, sp):
    """Refuse a splits_final.json with any locked or sealed id, or not of F-A20's shape (F-A20's val test)."""
    if not isinstance(splits, list) or len(splits) != 2 or splits[0] != splits[1]:
        raise SplitError('splits_final.json must hold two identical entries (a1 = fold 0, a2 = fold 1)')
    for e in splits:
        refuse_training(list(e['train']) + list(e['val']), sp, 'splits_final.json')
        if sorted(e['train']) != sorted(sp['train620']):
            raise SplitError('splits_final.json train must be the 620')
        if sorted(e['val']) != fitcheck_ids(sp['train620']):
            raise SplitError('splits_final.json val must be the 20 fit-check training cases (F-A5)')
    return True


def rederive(icx_dir, sealed_path=None):
    """F0-r2's split from ImageCAS-X's train.txt / val.txt / test.txt and the sealed list (split620.py's rule)."""
    def rd(n):
        with open(os.path.join(icx_dir, n)) as f:
            return ['c%04d' % (int(x) - 1) for x in f.read().split()]
    train, val, test = rd('train.txt'), rd('val.txt'), rd('test.txt')
    s = pins.load_json(sealed_path or pins.SEALED)
    open36, dev44 = s['open_icx_test'], s['excluded_dev_cases_in_test']
    if not (len(train) == 560 and len(val) == 80 and len(test) == 160 and len(open36) == 36 and len(dev44) == 44):
        raise SplitError('ImageCAS-X file lists are not 560 / 80 / 160 with 36 open and 44 dev test cases')
    if set(open36) | set(dev44) | set(s['sealed_icx_test']) != set(test):
        raise SplitError('the sealed list does not partition ImageCAS-X test')
    ranked = sorted(open36, key=lambda c: hashlib.sha256((LOCKED_SALT + c).encode()).hexdigest())
    train620 = sorted(set(train) | set(dev44) | set(ranked[20:]))
    locked100 = sorted(set(val) | set(ranked[:20]))
    return {'train620': train620, 'locked100': locked100}


def f0r2_lines(icx_dir, sealed_path=None):
    """F0-r2's first two lines, re-derived on the copy `prep` will read; raises if they differ from the pins."""
    d = rederive(icx_dir, sealed_path)
    t, lk = pins.ids_sha256(d['train620']), pins.ids_sha256(d['locked100'])
    lines = [f'train620 {t}', f'locked100 {lk}']
    if t != pins.TRAIN620_SHA256 or lk != pins.LOCKED100_SHA256:
        raise SplitError('F0-r2 differs on this copy of ImageCAS-X: ' + '; '.join(lines) + ' (stop; tell the PM)')
    return lines
