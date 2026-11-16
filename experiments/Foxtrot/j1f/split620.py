"""D45's ImageCAS-X split for Janus 1-L / 1-F, computed from the released file lists and trillium/icx4/sealed_test.json.

620 training = ImageCAS-X train (560) + the 44 declared dev cases in test + the 16 open-36 cases NOT in the locked 20.
Locked 100 = ImageCAS-X val (80) + the 20 open-36 cases with the smallest sha256('asclepius-janus1-locked100:' + id).
The 80 sealed test cases and the 20 sealed quality-0 cases are never in either list.
Usage: python3 split620.py <dir with train.txt val.txt test.txt> <sealed_test.json> <out.json>"""
import hashlib, json, os, sys

SALT = 'asclepius-janus1-locked100:'


def key(c, form):
    # form 'c': the project's case id (c0068); form 'n': ImageCAS-X's own file number (69)
    return c if form == 'c' else str(int(c[1:]) + 1)


def split(filelist_dir, sealed_json, form='c'):
    # ImageCAS-X file lists hold ImageCAS numbers (1-based); the project's case ids are c%04d of number - 1
    rd = lambda n: ['c%04d' % (int(x) - 1) for x in open(os.path.join(filelist_dir, n)).read().split()]
    train, val, test = rd('train.txt'), rd('val.txt'), rd('test.txt')
    s = json.load(open(sealed_json))
    sealed = set(s['sealed_icx_test']) | set(s['sealed_quality0'])
    open36, dev44 = s['open_icx_test'], s['excluded_dev_cases_in_test']
    assert len(train) == 560 and len(val) == 80 and len(test) == 160 and len(open36) == 36 and len(dev44) == 44
    assert set(open36) | set(dev44) | set(s['sealed_icx_test']) == set(test)
    ranked = sorted(open36, key=lambda c: hashlib.sha256((SALT + key(c, form)).encode()).hexdigest())
    locked20 = sorted(ranked[:20]); open16 = sorted(ranked[20:])
    train620 = sorted(set(train) | set(dev44) | set(open16))
    locked100 = sorted(set(val) | set(locked20))
    assert len(train620) == 620 and len(locked100) == 100 and not set(train620) & set(locked100)
    assert not (set(train620) | set(locked100)) & sealed
    return {'train620': train620, 'locked100': locked100, 'locked20_from_open36': locked20,
            'open16_trained': open16, 'salt': SALT, 'id_form': form}


if __name__ == '__main__':
    out = split(sys.argv[1], sys.argv[2], 'c')
    alt = split(sys.argv[1], sys.argv[2], 'n')
    out['locked20_if_salted_on_imagecas_number'] = alt['locked20_from_open36']
    out['locked20_forms_agree'] = alt['locked20_from_open36'] == out['locked20_from_open36']
    print('locked-20 overlap between id forms:', len(set(alt['locked20_from_open36']) & set(out['locked20_from_open36'])))
    json.dump(out, open(sys.argv[3], 'w'), indent=1)
    print({k: len(v) for k, v in out.items() if isinstance(v, list)})
