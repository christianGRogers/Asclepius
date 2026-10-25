"""Fast tests of the wave-1 tools (run: pytest experiments/Bridge/wave1). The slow end-to-end check is selftest.py."""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import power  # noqa: E402
import report_wave1 as R  # noqa: E402
import score_wave1 as S  # noqa: E402
import synth  # noqa: E402

SEAL = C.Seal()
D = json.load(open(SEAL.path))


def test_tf1_pin():
    assert C.check_tf1_pin() == C.TF1_PIN


def test_real_patients_reproduce_the_seal_file():
    """D32: the seal is keyed by real patient (segtrain.pool_seal.ingest_patient), every volume listed."""
    groups = {}
    for v in SEAL.pool:
        groups.setdefault(C.corrected_key(v), []).append(v)
    multi = {k: sorted(v) for k, v in groups.items() if len(v) > 1}
    assert multi == {k: sorted(v) for k, v in D['multi_volume_patients'].items()}
    prim = set(D['primary']['patients'])
    assert {C.corrected_key(v) for v in D['primary']['volumes']} == prim and len(prim) == 150
    assert sorted(v for p in prim for v in groups[p]) == sorted(D['primary']['volumes'])


def test_volume_name_normalises_export_names():
    assert C.volume_name('Taiwan-AICUP-CardiacCT__patient0001__r2') == 'Taiwan-AICUP-CardiacCT__patient0001.nii.gz'
    assert C.volume_name('/x/VMR-Coronary__0066_H_CORO_H.nii.gz') == 'VMR-Coronary__0066_H_CORO_H.nii.gz'
    assert C.volume_name('Kaggle-HeartSR__P01__totalseg-coronary.nii.gz') == 'Kaggle-HeartSR__P01.nii.gz'


def test_seal_refuses_sealed_reserved_leaked_and_unknown():
    sealed = sorted(D['primary']['volumes'])[0]
    chd = sorted(D['report_only']['volumes'])[0]
    reserved = next(v for v in sorted(SEAL.pool) if C.corrected_key(v) == D['primary']['extension_order'][0])
    assert 'sealed' in SEAL.reason(sealed)
    assert 'sealed' in SEAL.reason(chd)
    assert 'reserved' in SEAL.reason(reserved)
    assert 'pool list' in SEAL.reason('Nowhere__x.nii.gz')
    # A30/D32: a volume the name rule split off a sealed one-patient SDN record is in the file now, and a new
    # series of that record (not in any list) is still refused, by real patient
    assert 'Mendeley-SDN-spb25zt2c4__s009.nii.gz' in SEAL.sealed_volumes
    assert SEAL.guard.is_sealed('Mendeley-SDN-spb25zt2c4__s999.nii.gz')
    open_ = [v for v in SEAL.pool if not SEAL.reason(v)]
    assert len(open_) > 150 and not any(C.corrected_key(v) in SEAL.sealed for v in open_)


def test_corrected_grouping_counts():
    keys = {C.corrected_key(v) for v in SEAL.pool}
    assert len(keys) == 468          # 469 by the ingest code, minus D33's RIDER merge
    assert C.corrected_key('Slicer-SampleData__TruncalValve_4DCT_f09.nii.gz') == 'Slicer-SampleData__TruncalValve_4DCT'
    assert C.corrected_key('Figshare-23057000__PA0.nii.gz') != C.corrected_key('Figshare-23057000__PA1.nii.gz')


def test_collect_refuses_before_opening(tmp_path):
    sealed = sorted(SEAL.sealed_volumes)[0][:-7]
    (tmp_path / sealed / 'segmentations').mkdir(parents=True)   # empty: opening anything would fail differently
    with pytest.raises(C.SealedVolumeError):
        S.collect(str(tmp_path), SEAL, skip=False)
    groups, refused = S.collect(str(tmp_path), SEAL, skip=True)
    assert groups == {} and len(refused) == 1


def test_seed_named_from_the_read_scores_one_when_the_read_is_the_seed():
    rng = np.random.default_rng(0)
    truth, aorta = synth.tree(rng)
    vein = np.zeros(truth.shape, np.uint8)
    synth._tube(vein, [(81, 95, 45), (89, 81, 81)], 2.4, 1)
    seed = (truth > 0) | (vein > 0)
    sp = np.array(synth.SP)
    named = S.name_seed(seed, truth, sp)
    assert not named[vein > 0].any()                       # a component the reader deleted whole is left out
    per, fl, prov = S.pair(truth, named, sp, aorta)
    assert not prov and set(per) == {1, 2, 3, 4} and all(v == pytest.approx(1.0) for v in per.values())
    short, _ = synth.tree(rng, lad_len=0.3)                 # a read that cut the LAD short
    per2, _, _ = S.pair(short, S.name_seed(seed, short, sp), sp, aorta)
    assert per2[2] < 0.95 and per2[4] == pytest.approx(1.0)


def test_power_reproduces_round9():
    rows = json.load(open(os.path.join(C.REPO, 'trillium-results/round6/atlas2/results/per_case_run1.json')))
    base = {n: [] for n in C.CLASSES.values()}
    for r in rows:
        for c, n in C.CLASSES.items():
            v = r['per_class'].get(str(c))
            if v is not None and c not in r['flagged_classes']:
                base[n].append(v)
    keep = {'LM': 0.85, 'LAD': 0.95, 'LCx': 0.95, 'RCA': 0.95}
    one = {n: 1.0 for n in base}
    assert power.p_pass(base, one, one, keep, 150)[0] == pytest.approx(0.966, abs=0.02)
    assert power.p_pass(base, {n: 1.5 for n in base}, one, keep, 150)[0] == pytest.approx(0.582, abs=0.03)


def _rows(model_sd, inter_sd, seed_mean, n=40, seed=0):
    """Rows for n primary open patients with chosen spreads (tF1 around 0.9)."""
    rng = np.random.default_rng(seed)
    vols = []
    for v in sorted(SEAL.pool):
        if not SEAL.reason(v) and R.stratum(C.source_of(v)) == 'primary' and \
                C.corrected_key(v) not in {C.corrected_key(x) for x in vols}:
            vols.append(v)
    rows = []
    for v in vols[:n]:
        cl = lambda m, s: {k: float(np.clip(m + rng.normal(0, s), 0, 1)) for k in C.CLASSES.values()}  # noqa: E731
        rows.append({'volume': v, 'patient': C.corrected_key(v), 'source': C.source_of(v), 'provisional': False,
                     'inter': {'per_class': cl(0.9, inter_sd), 'flagged': []},
                     'model': {'per_class': cl(0.88, model_sd), 'flagged': []},
                     'seed': {'per_class': cl(seed_mean, 0.03), 'flagged': []},
                     'seed_edit': [{'added_share_of_read': 0.1, 'removed_share_of_seed': 0.2}]})
    return rows


def _val(sd, n=80, seed=1):
    rng = np.random.default_rng(seed)
    return {k: np.clip(0.9 + rng.normal(0, sd, n), 0, 1) for k in C.CLASSES.values()}


def test_report_no_trigger_and_no_seed_flag():
    # f about 0.6 and k about 0.67: well under 1.2 (at f = k = 1 and 40 patients the rule fires by chance about
    # 60 % of the time, trigger_false_alarm.py, so the no-trigger case is tested away from the line)
    r = R.build(_rows(0.03, 0.02, 0.80), _val(0.05), SEAL)
    assert not r['extension']['triggered'] and r['extension']['extend_to'] == 150
    assert r['seed_anchored_classes'] == []
    assert all(0.4 < r['f_k'][n]['f'] < 0.9 for n in R.NAMES)


def test_report_triggers_extension_and_seed_flag():
    r = R.build(_rows(0.10, 0.10, 0.92), _val(0.05), SEAL)   # f about 2: the pool is twice as spread
    assert r['extension']['triggered'] and r['extension']['extend_to'] in (200, 250)
    assert len(r['extension']['added_patients']) == r['extension']['extend_to'] - 150
    assert r['extension']['added_patients'] == D['primary']['extension_order'][:r['extension']['extend_to'] - 150]
    assert set(r['seed_anchored_classes']) == set(R.NAMES)   # seed 0.92 >= inter 0.90 - 0.02


def test_report_refuses_a_sealed_row_and_drops_provisional():
    rows = _rows(0.05, 0.05, 0.8, n=5)
    bad = dict(rows[0], volume=sorted(SEAL.sealed_volumes)[0])
    with pytest.raises(C.SealedVolumeError):
        R.build(rows + [bad], _val(0.05), SEAL)
    rows[0]['provisional'] = True
    assert R.build(rows, _val(0.05), SEAL)['n_patients'] == 4


def test_rule_c_sizes_the_seal_from_s_d():
    # Round 10 (Bridge v9): small per-patient differences keep 150; wide independent spreads (0.15 each, clipped
    # at tF1 = 1, so s_d about 0.17-0.2) grow the seal.
    small = R.build(_rows(0.03, 0.02, 0.80), _val(0.05), SEAL)['rule_c']
    assert small['seal_size'] == 150 and small['power']['150'] >= 0.8
    big = R.build(_rows(0.15, 0.15, 0.80, n=60), _val(0.05), SEAL)['rule_c']
    assert big['seal_size'] in (200, 250) and all(0.13 < big['s_d'][n] < 0.26 for n in R.NAMES)
    assert big['power']['150'] < 0.8 <= big['power'][str(big['seal_size'])] or big['seal_size'] == 250
    assert all(v is None or -1 <= v <= 1 for v in big['rho_model_inter'].values())
