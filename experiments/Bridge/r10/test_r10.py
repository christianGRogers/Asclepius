"""Tests for Bridge's Round 10 scripts: counts, the D35 draw and its disjointness, the power re-run, rule C.
Run: python3 -m pytest -q experiments/Bridge/r10"""
import json
import os
import sys

import numpy as np
import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'src'))

import counts  # noqa: E402
import d35_power  # noqa: E402
import draw_d35  # noqa: E402
import extension_rule  # noqa: E402
import power_r10  # noqa: E402
from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402


def test_counts_reconcile_the_two_quoted_numbers():
    vols, seal = counts.load()
    t = counts.table(vols, seal)
    assert t['name_rule_patients'] - 150 - 20 == 347          # Atlas's figure on #43
    bs = t['by_stratum']
    assert t['real_patients'] - 170 - bs['primary']['reserved'] == 198   # the wave-1 note's figure
    assert bs['primary']['open'] + bs['primary']['reserved'] == 161
    assert bs['primary']['open'] + bs['primary']['reserved'] + bs['excluded']['open'] == 235


def test_draw_is_deterministic_and_matches_the_committed_proposal():
    d = draw_d35.build()
    committed = json.load(open(os.path.join(HERE, 'decision_set_proposal.json')))
    assert d['patients'] == committed['patients'] and d['salt'] == committed['salt']
    assert d['n_patients'] == 35 and d['n_eligible_patients'] == 111


def test_decision_set_is_disjoint_from_seal_and_both_extension_steps():
    d = draw_d35.build()
    guard = load_pool_seal()
    dec = set(d['patients'])
    step1 = d['reserve_200_step (extension_order[:50], unchanged)']
    step2 = d['reserve_250_step (extension_order[50:] skipping decision patients, then continued)']
    assert len(step1) == 50 and len(step2) == 50 and not (set(step1) & set(step2))
    assert not (dec & set(step1)) and not (dec & set(step2))
    assert not any(guard.is_sealed(v[:-len('.nii.gz')]) or guard.is_sealed(v) for v in d['volumes'])
    seal = json.load(open(counts.SEAL))
    assert step1 == seal['primary']['extension_order'][:50]
    # every volume of every decision patient is listed, and nothing else
    vols = [ln.strip() for ln in open(counts.POOL) if ln.strip() and not ln.startswith('#')]
    assert sorted(v for v in vols if ingest_patient(v[:-len('.nii.gz')]) in dec) == d['volumes']
    assert all(counts.stratum_of(p.split('__')[0]) == 'primary' for p in dec)


def test_power_reproduces_round9_on_run1_and_drops_on_janus0():
    p_run1, _ = power_r10.p_pass(power_r10.run1_base(), 1.0, 1.0, 150, sims=3000)
    assert p_run1 == pytest.approx(0.966, abs=0.02)
    p_j0, _ = power_r10.p_pass(power_r10.surrogate(), 1.0, 1.0, 150, sims=3000)
    assert 0.70 < p_j0 < 0.82


def test_surrogate_matches_janus0_moments():
    base = power_r10.surrogate()
    for c, v in base.items():
        assert np.mean(v) == pytest.approx(power_r10.JANUS0[c]['mean'], abs=0.005)
        sd = power_r10.sd_from_ci(power_r10.JANUS0[c]['ci'], power_r10.JANUS0[c]['n'])
        assert np.std(v, ddof=1) == pytest.approx(sd, rel=0.06)


def test_rule_c_keeps_150_when_reads_and_model_fail_together():
    r = extension_rule.simulate_c(1, 1, 0.5, 49, sims=500)
    assert r['share_chosen']['150'] > 0.95
    r = extension_rule.simulate_c(1.5, 1, 0, 49, sims=500)
    assert r['share_chosen']['250'] > 0.95


def test_sigma_run_bound():
    pt, up = d35_power.sigma_run_pooled([(0.0047, 0.0043), (-0.0027, 0.0046)])
    assert pt < 0.003 and 0.010 < up < 0.013
