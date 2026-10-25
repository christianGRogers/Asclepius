"""Foxtrot Round 10 checks: the D35 candidate is disjoint from everything held out, reproducible from the pinned
seal, and the power model reproduces Round 9 before it is used on Janus 0's spread. Names only; no image."""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
sys.path.insert(0, HERE)


def _proposal():
    subprocess.run([sys.executable, os.path.join(HERE, 'd35_proposal.py')], check=True, capture_output=True)
    return json.load(open(os.path.join(HERE, 'd35_proposal.json')))


def test_d35_disjoint_and_unsealed():
    from segtrain.pool_seal import load_pool_seal, ingest_patient
    p = _proposal()
    guard = load_pool_seal(os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json'))
    d35 = set(p['proposed_d35']['patients'])
    assert len(d35) == 50
    assert not d35 & set(p['seal_extension_to_200']['patients'])
    for b in p['trainable_now'].values():
        assert not d35 & set(b['patients'])
    for v in p['proposed_d35']['volumes'] + p['janus0_may_predict_now']['volumes']:
        assert not guard.is_sealed(v), v
    assert {ingest_patient(v[:-7]) for v in p['proposed_d35']['volumes']} == d35


def test_d35_is_the_extension_tail_and_reproducible():
    seal = json.load(open(os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')))
    a = _proposal()
    b = _proposal()
    assert a == b
    assert a['proposed_d35']['patients'] == sorted(seal['primary']['extension_order'][50:100])


def test_frame_counts():
    p = _proposal()
    t = p['trainable_now']
    assert t['primary_open']['n_patients'] == 61
    assert t['report_only_open (ImageCHD)']['n_patients'] == 63
    assert t['excluded_open (suspect spacing; train only once re-gridded)']['n_patients'] == 74


def test_power_model_reproduces_round9():
    sys.path.insert(0, os.path.join(REPO, 'experiments', 'Bridge', 'wave1'))
    import repower
    from power import p_pass
    base = repower.run1_base()
    one = {c: 1.0 for c in base}
    keep = {'LM': 0.85, 'LAD': 0.95, 'LCx': 0.95, 'RCA': 0.95}
    assert abs(p_pass(base, one, one, keep, 150)[0] - 0.966) < 0.01
