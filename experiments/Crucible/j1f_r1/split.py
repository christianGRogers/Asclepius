"""D45's ImageCAS-X split for Janus 1 (1-L and 1-F), built only from id lists, never from label files.

620 training = train 560 + dev-44 + the 16 open-36 cases not locked; locked 100 = val 80 + the 20 open-36 cases with
the smallest sha256('asclepius-janus1-locked100:' + id), id in the c0000 form used by sealed_test.json. The 80 sealed
test cases and the 20 sealed quality-0 cases are in neither list, and nothing here opens a label file.
Usage: split.py <icx_filelist_dir> -> prints JSON {train620, locked100, locked20}."""
import hashlib, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
SEALED = os.path.join(HERE, '..', '..', '..', 'trillium', 'icx4', 'sealed_test.json')
SALT = 'asclepius-janus1-locked100:'


def ids(path):
    return ['c%04d' % (int(x) - 1) for x in open(path).read().split()]


def build(icx_dir):
    S = json.load(open(SEALED))
    train, val = ids(os.path.join(icx_dir, 'train.txt')), ids(os.path.join(icx_dir, 'val.txt'))
    open36, dev44 = sorted(S['open_icx_test']), sorted(S['excluded_dev_cases_in_test'])
    locked20 = sorted(open36, key=lambda c: hashlib.sha256((SALT + c).encode()).hexdigest())[:20]
    train620 = sorted(set(train) | set(dev44) | (set(open36) - set(locked20)))
    locked100 = sorted(set(val) | set(locked20))
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    assert len(train620) == 620 and len(locked100) == 100 and not set(train620) & set(locked100)
    assert not (set(train620) | set(locked100)) & sealed
    return {'train620': train620, 'locked100': locked100, 'locked20': sorted(locked20)}


if __name__ == '__main__':
    print(json.dumps(build(sys.argv[1]), indent=1))
