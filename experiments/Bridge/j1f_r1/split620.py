"""D45's ImageCAS-X split for Janus 1 (1-L and 1-F), from the repository's sealed list and ImageCAS-X's file lists.
620 training = train 560 + dev-44 + the 16 open-36 cases NOT in the locked 20;
locked 100 = val 80 + the 20 open-36 cases with the smallest sha256('asclepius-janus1-locked100:' + id).
The 80 sealed test cases and 20 quality-0 cases are never listed. Standard library only.
Usage: split620.py <filelist_dir> <sealed_test.json> <out.json>
(filelist_dir holds ImageCAS-X's train.txt / val.txt / test.txt, 1-based ImageCAS ids.)"""
import hashlib, json, os, sys


def ids(d, name):
    return ['c%04d' % (int(x) - 1) for x in open(os.path.join(d, f'{name}.txt')).read().split()]


def build(fl, sealed_path):
    S = json.load(open(sealed_path))
    train, val, test = ids(fl, 'train'), ids(fl, 'val'), ids(fl, 'test')
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    open36, dev44 = list(S['open_icx_test']), list(S['excluded_dev_cases_in_test'])
    assert len(train) == 560 and len(val) == 80 and set(open36 + dev44) <= set(test)
    assert set(test) == set(open36) | set(dev44) | set(S['sealed_icx_test'])
    key = lambda c: hashlib.sha256(('asclepius-janus1-locked100:' + c).encode()).hexdigest()
    locked20 = sorted(open36, key=key)[:20]
    train620 = sorted(train + dev44 + [c for c in open36 if c not in locked20])
    locked100 = sorted(val + locked20)
    assert len(train620) == 620 and len(locked100) == 100 and not (set(train620) & set(locked100))
    assert not ((set(train620) | set(locked100)) & sealed)
    return dict(rule='D45', train620=train620, locked100=locked100, locked20_open36=sorted(locked20))


if __name__ == '__main__':
    out = build(sys.argv[1], sys.argv[2])
    json.dump(out, open(sys.argv[3], 'w'), indent=1)
    print({k: len(v) for k, v in out.items() if isinstance(v, list)})
