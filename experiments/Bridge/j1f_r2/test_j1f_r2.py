"""Self-tests for Bridge's Janus 1-F round-2 scripts (CPU, seconds): python3 test_j1f_r2.py"""
import numpy as np

import census_r2
import gate_sim


def test_q_fit_recovers_planted_mixture():
    rng = np.random.default_rng(0)
    q, mu, sg = 0.12, 0.88, 0.08
    x = np.where(rng.random(400_000) < q, 0.0, rng.normal(mu, sg, 400_000))
    got = gate_sim.fit_q(x.mean(), x.std(), sg)
    assert abs(got - q) < 0.005, got


def test_miss_rate_modes():
    assert abs(gate_sim.miss_rate(0.9, 0.5, 'symmetric') - 0.1) < 1e-12          # 0.05 / 0.5
    assert abs(gate_sim.miss_rate(0.9, 0.5, 'misses_only') - 0.2) < 1e-12
    # extra calls capped by the 2 % negatives: d = 0.04, extra 0.02, miss 0.02 / 0.98
    assert abs(gate_sim.miss_rate(0.96, 0.98, 'symmetric') - 0.02 / 0.98) < 1e-12


def test_twig_on_synthetic_trunk():
    m = np.zeros((20, 20, 80), bool)
    m[9:12, 9:12, 5:75] = True              # trunk, 70 voxels long
    m[10, 12:19, 40] = True                 # one side twig, 7 voxels long, leaving the trunk at z = 40
    tw = census_r2.twigs(m, np.array([0.5, 0.5, 0.5]))
    assert len([t for t in tw if t >= 2.0]) == 1, tw


if __name__ == '__main__':
    for name, f in list(globals().items()):
        if name.startswith('test_'):
            f()
            print('ok', name)
