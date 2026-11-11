"""Foxtrot, track 1-L round 1: pin D45's locked 100 and the 620 training cases from the files in the repo.

D45: locked 100 = Janus 0's val 80 + the 20 open-36 cases whose sha256('asclepius-janus1-locked100:' + id) is
smallest, ids as in vault/Plans/Sealed test.md (c0NNN). Training 620 = ImageCAS-X train 560 + dev-44 + the other 16
of open-36. The val-80 and train-560 lists are ImageCAS-X's own split, which is not in the repo (icx4 writes it to
$SCRATCH/icx4/splits.json on Fir), so this script pins the open-36 part exactly and checks the rest by count.
Reads only trillium/sealed_test.json (ids, no image or label). Output: results/locked100.json.
"""
import hashlib, json, os

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
SALT = 'asclepius-janus1-locked100:'


def key(c):
    return hashlib.sha256((SALT + c).encode()).hexdigest()


def main():
    S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
    open36 = sorted(S['open_icx_test']); dev44 = sorted(S['excluded_dev_cases_in_test'])
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    assert len(open36) == 36 and len(dev44) == 44 and len(S['sealed_icx_test']) == 80
    ranked = sorted(open36, key=key)
    locked20, train16 = sorted(ranked[:20]), sorted(ranked[20:])
    assert not (set(open36) | set(dev44)) & sealed
    out = {'salt': SALT, 'rule': 'D45: the 20 open-36 ids with the smallest sha256(salt + id)',
           'locked20_from_open36': locked20, 'train16_from_open36': train16, 'train_dev44': dev44,
           'ranking': [[c, key(c)] for c in ranked],
           'counts': {'locked': '80 (ImageCAS-X val, from $SCRATCH/icx4/splits.json) + 20', 'train': '560 + 44 + 16 = 620'},
           'sha256_of_locked20_list': hashlib.sha256(','.join(locked20).encode()).hexdigest()}
    json.dump(out, open(os.path.join(HERE, 'results', 'locked100.json'), 'w'), indent=1)
    print('locked 20:', ', '.join(locked20)); print('train 16:', ', '.join(train16))
    print('sha256(locked20 joined by commas):', out['sha256_of_locked20_list'])


if __name__ == '__main__':
    main()
