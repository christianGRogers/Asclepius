"""Janus 1-F round 3 (judge): re-run an advocate's per-case function on a few hash-chosen TRAINING cases and compare
each new row with the row the advocate committed. Together with the summarisers (re-run on the committed rows,
byte-identical), this checks the 620-case numbers the ruling quotes without a 620-case re-run of every script.

Usage: python rerun_rows.py <advocate_script.py> <committed_rows.jsonl[.gz]> <icx620_dir> <split_j1l.json> [n=8]
Cases: the n training cases with the smallest sha256('asclepius-j1f-r3-judge-rows:' + id). The split pin is asserted
and only those label files are opened."""
import gzip, hashlib, importlib.util, json, os, sys

PIN = '1350cb1f50b0080f985835eee0c65b4c8fd1b3b071efadd914c1928863891152'


def diff(a, b, path=''):
    """List of (path, a, b) where the two JSON values differ; floats compared exactly."""
    out = []
    if isinstance(a, dict) and isinstance(b, dict):
        for k in sorted(set(a) | set(b)):
            out += diff(a.get(k), b.get(k), f'{path}/{k}')
    elif isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        for i, (x, y) in enumerate(zip(a, b)):
            out += diff(x, y, f'{path}[{i}]')
    elif a != b:
        out.append((path, a, b))
    return out


def main(script, rows, d, split, n=8):
    sp = json.load(open(split))
    train = sorted(sp['train620'])
    assert hashlib.sha256('\n'.join(train).encode()).hexdigest() == PIN
    pick = sorted(train, key=lambda c: hashlib.sha256(('asclepius-j1f-r3-judge-rows:' + c).encode()).hexdigest())[:n]
    op = gzip.open if rows.endswith('.gz') else open
    old = {}
    for line in op(rows, 'rt'):
        r = json.loads(line)
        old[r.get('case') or r.get('id')] = r
    sys.path.insert(0, os.path.dirname(os.path.abspath(script)))
    spec = importlib.util.spec_from_file_location('adv', script)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    res = {'script': script, 'cases': pick, 'rows_equal': 0, 'diffs': {}}
    for c in pick:
        new = json.loads(json.dumps(m.one(os.path.join(d, f'{int(c[1:]) + 1}.coronary.nii.gz'))))
        dd = diff(old[c], new)
        if dd:
            res['diffs'][c] = dd[:10]
        else:
            res['rows_equal'] += 1
    print(json.dumps(res))


if __name__ == '__main__':
    a = sys.argv[1:]
    main(a[0], a[1], a[2], a[3], int(a[4]) if len(a) > 4 else 8)
