"""Janus 1-F round 1 (Atlas): the D45 ImageCAS-X split, rebuilt from ImageCAS-X's filelists and
trillium/sealed_test.json. Prints the counts and writes split.json (case ids cNNNN = ImageCAS id - 1).

D45 hashes "sha256('asclepius-janus1-locked100:' + ImageCAS-X id)". The id is ambiguous: the project's
case id (c0068) or ImageCAS-X's own file number (69). Both readings are computed; they pick different
cases, so the string must be pinned before any job runs.
Usage: python split.py <icx_filelist_dir> <repo_root> <out.json>"""
import os, sys, json, hashlib

FL, ROOT, OUT = sys.argv[1], sys.argv[2], sys.argv[3]
S = json.load(open(os.path.join(ROOT, 'trillium', 'sealed_test.json')))
ids = lambda f: ['c%04d' % (int(x) - 1) for x in open(os.path.join(FL, f)).read().split()]
train, val, test, excl = ids('train.txt'), ids('val.txt'), ids('test.txt'), ids('exclude.txt')
assert len(train) == 560 and len(val) == 80 and len(test) == 160 and len(excl) == 200
sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
open36, dev44 = S['open_icx_test'], S['excluded_dev_cases_in_test']
assert set(open36) | set(dev44) | set(S['sealed_icx_test']) == set(test)
assert not sealed & (set(train) | set(val))


def pick(key):
    h = lambda c: hashlib.sha256(('asclepius-janus1-locked100:' + key(c)).encode()).hexdigest()
    return sorted(sorted(open36, key=h)[:20])


readings = {'case_id': pick(lambda c: c), 'imagecas_number': pick(lambda c: str(int(c[1:]) + 1))}
out = {}
for name, lock20 in readings.items():
    train16 = sorted(set(open36) - set(lock20))
    training = sorted(set(train) | set(dev44) | set(train16))
    locked = sorted(set(val) | set(lock20))
    assert len(training) == 620 and len(locked) == 100 and not (set(training) & set(locked)) and not (sealed & (set(training) | set(locked)))
    out[name] = {'training_620': training, 'locked_100': locked, 'open36_locked20': lock20, 'open36_train16': train16}
    print(f'{name}: locked-20 of open-36 = {lock20}')
both = set(readings['case_id']) & set(readings['imagecas_number'])
print(f'the two readings share {len(both)} of 20 locked open-36 cases')
out['note'] = 'Experiments in round 1 use only cases in the 620 under BOTH readings (the intersection).'
out['training_620_both'] = sorted(set(out['case_id']['training_620']) & set(out['imagecas_number']['training_620']))
print('training cases under both readings:', len(out['training_620_both']))
json.dump(out, open(OUT, 'w'), indent=1)
