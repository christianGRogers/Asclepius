"""D45's ImageCAS-X split for Janus 1-L/1-F, computed from ids only (no image, label or score of any case is read).

locked 100 = Janus 0's val 80 + the 20 open-36 cases with the smallest sha256('asclepius-janus1-locked100:' + id)
train 620  = ImageCAS-X train 560 + the 44 dev cases (excluded_dev_cases_in_test) + the other 16 of open-36
Sealed (80 ImageCAS-X test + 20 quality-0) must be in neither.

Inputs: trillium/sealed_test.json (A14 groups), experiments/Atlas/r9_icx4_census.json (ImageCAS-X train/val ids).
Output: experiments/Delta/j1l_r1/janus1_split_proposal.json and its sha256 on stdout.
"""
import hashlib, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
SALT = 'asclepius-janus1-locked100:'


def h(c):
    return hashlib.sha256((SALT + c).encode()).hexdigest()


def main():
    s = json.load(open(os.path.join(ROOT, 'trillium/sealed_test.json')))
    census = json.load(open(os.path.join(ROOT, 'experiments/Atlas/r9_icx4_census.json')))
    train560 = sorted(x['case'] for x in census if x['split'] == 'train')
    val80 = sorted(x['case'] for x in census if x['split'] == 'val')
    open36, dev44 = sorted(s['open_icx_test']), sorted(s['excluded_dev_cases_in_test'])
    sealed = set(s['sealed_icx_test']) | set(s['sealed_quality0'])
    ranked = sorted(open36, key=h)
    lock20, train16 = sorted(ranked[:20]), sorted(ranked[20:])
    locked = sorted(val80 + lock20)
    train = sorted(train560 + dev44 + train16)
    dev_any = set().union(*s['declared_dev_cases'].values())
    checks = {
        'n_train560': len(train560), 'n_val80': len(val80), 'n_open36': len(open36), 'n_dev44': len(dev44),
        'n_locked': len(locked), 'n_train': len(train), 'locked_train_overlap': len(set(locked) & set(train)),
        'sealed_in_locked': len(sealed & set(locked)), 'sealed_in_train': len(sealed & set(train)),
        'duplicates': len(train) + len(locked) - len(set(train) | set(locked)),
        'locked_cases_in_an_advocate_dev_list': sorted(set(locked) & dev_any),
    }
    assert checks['n_locked'] == 100 and checks['n_train'] == 620, checks
    assert not (checks['locked_train_overlap'] or checks['sealed_in_locked'] or checks['sealed_in_train']
                or checks['duplicates']), checks
    out = {
        'rule': "D45: locked 100 = ImageCAS-X val 80 + the 20 open-36 ids with the smallest "
                "sha256('asclepius-janus1-locked100:' + id); train 620 = train 560 + dev 44 + the other 16 of open-36",
        'salt': SALT,
        'open36_ranked': [{'case': c, 'sha256': h(c), 'locked': c in lock20} for c in ranked],
        'locked100': locked, 'locked20_from_open36': lock20, 'train620': train,
        'train16_from_open36': train16, 'checks': checks,
    }
    path = os.path.join(os.path.dirname(__file__), 'janus1_split_proposal.json')
    txt = json.dumps(out, indent=1, sort_keys=True) + '\n'
    open(path, 'w').write(txt)
    print(json.dumps(checks, indent=1))
    print('locked 20 from open-36:', ' '.join(lock20))
    print('train 16 from open-36: ', ' '.join(train16))
    print('sha256', hashlib.sha256(txt.encode()).hexdigest(), os.path.relpath(path, ROOT))


if __name__ == '__main__':
    sys.exit(main())
