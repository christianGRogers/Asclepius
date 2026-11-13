"""Self-tests for Bridge's Janus 1-F Round 1 code (synthetic data only; no ImageCAS-X file needed)."""
import hashlib, json, os, sys, tempfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import split620


def test_split620_synthetic():
    d = tempfile.mkdtemp()
    ids = list(range(1, 801))                     # 1-based ImageCAS ids
    train, val, test = ids[:560], ids[560:640], ids[640:800]
    for n, v in (('train', train), ('val', val), ('test', test)):
        open(f'{d}/{n}.txt', 'w').write('\n'.join(map(str, v)))
    tc = ['c%04d' % (i - 1) for i in test]
    S = dict(sealed_icx_test=tc[:80], open_icx_test=tc[80:116], excluded_dev_cases_in_test=tc[116:160],
             sealed_quality0=['c%04d' % i for i in range(900, 920)])
    json.dump(S, open(f'{d}/s.json', 'w'))
    out = split620.build(d, f'{d}/s.json')
    assert len(out['train620']) == 620 and len(out['locked100']) == 100
    key = lambda c: hashlib.sha256(('asclepius-janus1-locked100:' + c).encode()).hexdigest()
    assert out['locked20_open36'] == sorted(sorted(S['open_icx_test'], key=key)[:20])
    assert not set(out['train620']) & set(S['sealed_icx_test'])


def test_committed_split_matches_rule():
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'split_d45.json')
    sp = json.load(open(p))
    root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    S = json.load(open(os.path.join(root, 'trillium', 'sealed_test.json')))
    key = lambda c: hashlib.sha256(('asclepius-janus1-locked100:' + c).encode()).hexdigest()
    assert sp['locked20_open36'] == sorted(sorted(S['open_icx_test'], key=key)[:20])
    sealed = set(S['sealed_icx_test']) | set(S['sealed_quality0'])
    assert not (set(sp['train620']) | set(sp['locked100'])) & sealed
    assert set(S['excluded_dev_cases_in_test']) <= set(sp['train620'])


if __name__ == '__main__':
    test_split620_synthetic(); test_committed_split_matches_rule(); print('ok')
