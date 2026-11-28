"""Every self-test `check` runs (Delta v3 §4.3 as amended; Atlas v3 §2.4; Foxtrot v3 §5.3; F-A36). Each one first
shows that a broken fixture fails, then that the real thing passes. Synthetic data only: no volume is read.

  python -m janus1f.selftest            # all; exit 1 on the first failure
  python -m janus1f.selftest <name>...  # some
"""
import copy
import datetime
import hashlib
import json
import os
import shutil
import sys
import tempfile
from fractions import Fraction

import numpy as np

from . import collect, dataset, decode, ledger, parents, pins, plans, sbatch, split, verdict


def _softmax(z):
    z = z - z.max(0, keepdims=True)
    e = np.exp(z)
    return e / e.sum(0, keepdims=True)


def _fails(fn, *a, **k):
    try:
        fn(*a, **k)
    except (AssertionError, ValueError, RuntimeError):
        return True
    return False


# ---------------------------------------------------------------------------- the tests
def t_parent_copy():
    """1. Parent copy: territory sums = Janus 0's softmax within 1e-5, decode F's territory = Janus 0's argmax;
    broken: OM2's head row left at random init."""
    rng = np.random.default_rng(0)
    p = parents.load()
    F_, n = 32, 20000
    W0, b0 = rng.normal(size=(5, F_)), rng.normal(size=5)
    x = rng.normal(size=(F_, n)) * 3
    p0 = _softmax(W0 @ x + b0[:, None])
    W1, b1 = parents.copy_head(W0, b0, p)
    W1b, b1b = W1.copy(), b1.copy()
    W1b[9], b1b[9] = rng.normal(size=F_), 0.0
    bad = _softmax(W1b @ x + b1b[:, None])
    assert np.abs(parents.territory_sums(bad) - p0).max() > 1e-5, 'broken fixture passed'
    p1 = _softmax(W1 @ x + b1[:, None])
    assert np.abs(parents.territory_sums(p1) - p0).max() < 1e-5
    assert np.array_equal(decode.collapse_by_group(decode.decode_f(p1)), np.argmax(p0, 0))
    return 'territory sums within 1e-5; F territory = Janus 0 argmax; an uncopied OM2 row fails'


def t_hierarchical_decode():
    """2. Decode F = argmax of summed group probabilities, then argmax inside; broken: a plain argmax."""
    rng = np.random.default_rng(1)
    prob = _softmax(rng.normal(size=(13, 24, 24, 24)) * 2)
    terr = decode.territory(prob)
    plain = np.argmax(prob, 0)
    assert not np.array_equal(decode.collapse_by_group(plain), terr), 'plain argmax passed the territory test'
    f = decode.decode_f(prob)
    assert np.array_equal(decode.collapse_by_group(f), terr)
    share = float((plain != f).mean())
    assert share > 0.01, share
    return f'F territory = summed-group argmax; plain argmax differs on {share:.1%} of random voxels (> 1 %)'


def t_fa19_T():
    """3. F-A19's T test: a PDA-most-likely voxel in Janus 0's LCx territory is named PDA, and in the RCA territory
    it stays PDA; broken: round 2's LCx set without PDA/PLB."""
    p = np.full((13, 1, 1, 3), 1e-3)
    p[3], p[11], p[4] = 0.30, 0.50, 0.15
    p /= p.sum(0, keepdims=True)
    lcx = np.full((1, 1, 3), 3, np.uint8)
    old = decode.decode_in_territory(lcx, decode.within_group(p, decode.OLD_T_SETS))
    assert not (old == 11).any(), 'the old LCx set named a left PDA'
    assert (decode.decode_t(lcx, decode.within_group(p)) == 11).all()
    assert (decode.decode_t(np.full((1, 1, 3), 4, np.uint8), decode.within_group(p)) == 11).all()
    return 'left PDA named PDA in the LCx territory; the old LCx set cannot name it'


def t_G_round_trip():
    """4. T's four classes are Janus 0's bit for bit; G decodes any later four-class map (T_L) the same way;
    broken: a corrupted G map, and a T that is not G selected by the map."""
    rng = np.random.default_rng(2)
    prob = _softmax(rng.normal(size=(13, 16, 16, 16)) * 2)
    g = decode.within_group(prob)
    for four in (rng.integers(0, 5, (16, 16, 16)).astype(np.uint8), decode.territory(prob)):
        t13 = decode.decode_t(four, g)
        assert decode.check_t(t13, four, g)
        # T's four classes are the map's (PDA/PLB in LCx territory count as LCx)
        back = np.where(t13 == 1, 1, 0)
        for t in (2, 3, 4):
            back[(four == t) & (t13 > 0)] = t
        assert np.array_equal(back, four)
    bad = dict(g)
    bad[3] = np.full_like(g[3], 2)                         # LAD names inside the LCx territory
    assert _fails(decode.check_t, t13, four, bad)
    t_bad = t13.copy()
    t_bad[four == 2] = 3
    assert _fails(decode.check_t, t_bad, four, g)
    return 'T = map territory for territory; T_L from G with no probabilities; corrupt G or T refused'


def t_fa20_val():
    """5. F-A20's val test: no locked id in splits_final.json; two identical entries; val = the fit-check 20;
    broken: a locked id as val, a locked id in train, one entry only, a sealed id."""
    sp = split.load()
    sf = split.splits_final(sp)
    locked = sp['locked100'][0]
    lv = copy.deepcopy(sf)
    for e in lv:
        e['val'][0] = locked
    assert _fails(split.check_splits_final, lv, sp)
    lt = copy.deepcopy(sf)
    for e in lt:
        e['train'].append(sp['locked100'][5])
    assert _fails(split.check_splits_final, lt, sp)
    assert _fails(split.check_splits_final, [sf[0]], sp)
    assert _fails(split.refuse_training, [sorted(sp['sealed'])[0]], sp)
    assert split.check_splits_final(sf, sp)
    h = hashlib.sha256('\n'.join(sf[0]['val']).encode()).hexdigest()
    assert h == pins.FITCHECK20_SHA256
    return f'splits_final: train 620, val fit-check 20 ({h[:8]}...); locked or sealed id refused'


class _NpyIO:
    """A stand-in for nnU-Net's reader/writer: .npy payloads under the same file names."""

    @staticmethod
    def load_case(npz, pkl):
        return np.load(npz)['probabilities'].astype(np.float32), {'pkl': open(pkl).read()}

    def read_seg(self, path):
        with open(path, 'rb') as f:
            return np.load(f), {}

    def write_seg(self, arr, path, props):
        with open(path, 'wb') as f:
            np.save(f, np.asarray(arr, np.uint8))


def t_chunk_hygiene():
    """6. Chunked decode deletes the npz, pkl, argmax export and sidecars, and writes F, T, G with a marker;
    collect refuses a map without its marker or one that changed; broken: a stray file left in the chunk."""
    rng = np.random.default_rng(3)
    tmp = tempfile.mkdtemp()
    try:
        pred, out, j0 = (os.path.join(tmp, d) for d in ('pred', 'maps', 'j0'))
        for d in (pred, j0):
            os.makedirs(d)
        cases = ['c%04d' % i for i in range(3)]

        def fill():
            for c in cases:
                pr = _softmax(rng.normal(size=(13, 6, 6, 6)))
                np.savez_compressed(os.path.join(pred, c + '.npz'), probabilities=pr.astype(np.float16))
                open(os.path.join(pred, c + '.pkl'), 'w').write('props')
                open(os.path.join(pred, c + '.nii.gz'), 'w').write('argmax')
                with open(os.path.join(j0, c + '.nii.gz'), 'wb') as f:
                    np.save(f, rng.integers(0, 5, (6, 6, 6)).astype(np.uint8))
            for s in decode.NNUNET_SIDECARS:
                open(os.path.join(pred, s), 'w').write('{}')
        fill()
        open(os.path.join(pred, 'stray.txt'), 'w').write('x')
        assert _fails(decode.decode_chunk, pred, out, j0, _NpyIO(), cases), 'a stray file passed'
        shutil.rmtree(pred)
        shutil.rmtree(out)
        os.makedirs(pred)
        fill()
        done = decode.decode_chunk(pred, out, j0, _NpyIO(), cases)
        assert done == cases and os.listdir(pred) == []
        got = decode.collect_inputs(out, cases)
        assert sorted(got) == cases and all(sorted(v) == sorted(decode.MAPS) for v in got.values())
        with open(got[cases[2]]['F'], 'ab') as f:
            f.write(b'\0')
        assert _fails(decode.collect_inputs, out, cases), 'a changed map passed'
        os.remove(os.path.join(out, cases[1] + decode.MARKER))
        assert _fails(decode.collect_inputs, out, cases[:2]), 'a missing marker passed'
    finally:
        shutil.rmtree(tmp)
    return 'npz, pkl, argmax export and sidecars deleted; marker required and checked; stray file refused'


def t_plans():
    """7. Plans: L-A21's check pinned to Step T (a changed percentile, batch_dice True, a non-Step-T plans file and a
    different fingerprint each refuse)."""
    import contextlib
    import io
    with contextlib.redirect_stdout(io.StringIO()):
        plans.selftest()
    return 'changed percentile, batch_dice True, non-Step-T plans, different fingerprint: each refused'


def t_scorer_and_gates():
    """8-10. The scorer of record's self-test (converter, collapse, detection, naming) and the judge's gate test
    (F-A27's edges); broken: a scorer copy whose sha256 differs, and the advocates' superseded gate file."""
    import contextlib
    import io
    sys.path.insert(0, pins.LIB)
    import j1f_scorer as S
    assert S.scorer_sha256() == pins.SCORER_SHA256
    with contextlib.redirect_stdout(io.StringIO()):
        S.selftest()
    g = S.load_gates(pins.GATES)
    fa27 = {'D1': (0.81, 0.93, 0.83), 'D2': (0.76, 0.84, 0.86), 'OM1': (0.75, 0.90, 0.78),
            'OM2': (0.60, 0.81, 0.78), 'PDA': (0.89, 0.97, 0.90), 'PLB': (0.90, 0.95, 0.92)}
    assert {k: (v['recall'], v['presence'], v['naming']) for k, v in g['lines'].items()} == fa27

    def on_lines():
        return {k: {m: Fraction(round(v[m] * 100), 100) for m in ('recall', 'presence', 'naming')}
                for k, v in g['lines'].items()}
    assert S.gate(on_lines(), g)['n_pass'] == 6
    for cls, stat, num, want in (('OM2', 'recall', 59, False), ('OM2', 'recall', 60, True),
                                 ('OM2', 'recall', 61, True), ('D1', 'presence', 92, False),
                                 ('D1', 'presence', 93, True), ('PLB', 'recall', 89, False),
                                 ('PLB', 'recall', 90, True), ('PLB', 'presence', 94, False),
                                 ('PLB', 'presence', 95, True)):
        a = on_lines()
        a[cls][stat] = Fraction(num, 100)
        assert S.gate(a, g)['classes'][cls]['pass'] is want, (cls, stat, num)
    a = on_lines()
    a['OM2']['recall'], a['D2']['naming'], a['PLB']['presence'] = Fraction(59, 100), Fraction(85, 100), \
        Fraction(94, 100)
    assert S.gate(a, g)['n_pass'] == 3 and not S.gate(a, g)['verdict_pass']
    a = on_lines()
    a['D1']['naming'] = None
    assert not S.gate(a, g)['classes']['D1']['pass']
    # broken: a scorer copy one byte different, and the superseded Atlas gate file
    tmp = tempfile.mkdtemp()
    try:
        bad = os.path.join(tmp, 'j1f_scorer.py')
        shutil.copyfile(pins.SCORER, bad)
        with open(bad, 'a') as f:
            f.write('\n')
        assert _fails(pins.check_four, {'scorer': bad}, {})
        old = os.path.join(pins.ROOT, 'experiments', 'Atlas', 'j1f_r3', 'j1f_gates.json')
        if os.path.exists(old):
            assert _fails(pins.check_four, {'gates': old}, {})
    finally:
        shutil.rmtree(tmp)
    return 'scorer self-test ok; F-A27 edges (OM2 59/60/61, D1 92/93, PLB 89/90, 94/95), 5 and 3 of 6; ' \
           'a changed scorer or a superseded gate file refused'


def t_ignore13():
    """11. Ignore on disk is 13: the converter's 255 is written as 13; a 255 left in a label refuses; "ignore": 255
    refuses; "ignore": 13 builds nnU-Net's LabelManager (where nnU-Net is installed)."""
    lab = np.array([[0, 5, 255], [12, 2, 255]], np.uint8)
    d = dataset.to_disk(lab)
    assert (d[lab == 255] == 13).all() and dataset.check_label_values(d) == [0, 2, 5, 12, 13]
    assert _fails(dataset.check_label_values, lab), 'a 255 on disk passed'
    dj = dataset.dataset_json(620)
    bad = copy.deepcopy(dj)
    bad['labels']['ignore'] = 255
    assert _fails(dataset.check_dataset_json, bad, False)
    msg = dataset.check_dataset_json(dj)
    return f'255 -> 13 on disk; 255 in a label or "ignore": 255 refused; {msg}'


def t_no_locked_in_719():
    """12. No locked (or sealed, or unknown) case in Dataset 719, raw or preprocessed; a used dataset id refuses;
    broken: one locked id linked into imagesTr, one in the preprocessed folder."""
    sp = split.load()
    tmp = tempfile.mkdtemp()
    try:
        p = dataset.paths(tmp)
        for sub in ('imagesTr', 'labelsTr'):
            os.makedirs(os.path.join(p['raw'], sub))
        for c in sp['train620'][:3]:
            open(os.path.join(p['raw'], 'imagesTr', c + '_0000.nii.gz'), 'w').close()
            open(os.path.join(p['raw'], 'labelsTr', c + '.nii.gz'), 'w').close()
        assert dataset.check_raw_dataset(tmp, sp) == (3, 3)
        assert _fails(dataset.refuse_used_id, tmp), 'a Dataset719 not made by the launcher passed'
        open(os.path.join(p['raw'], dataset.OWN), 'w').close()
        dataset.refuse_used_id(tmp)
        os.makedirs(os.path.join(p['raw_root'], 'Dataset719_Other'))
        assert _fails(dataset.refuse_used_id, tmp), 'a second Dataset719 passed'
        os.rmdir(os.path.join(p['raw_root'], 'Dataset719_Other'))
        lk = sp['locked100'][0]
        os.symlink('/dev/null', os.path.join(p['raw'], 'imagesTr', lk + '_0000.nii.gz'))
        assert _fails(dataset.check_raw_dataset, tmp, sp), 'a locked id in imagesTr passed'
        os.remove(os.path.join(p['raw'], 'imagesTr', lk + '_0000.nii.gz'))
        pp = os.path.join(p['pp'], 'nnUNetResEncUNetPlans_60G_iso05_3d_fullres')
        os.makedirs(pp)
        open(os.path.join(pp, sp['train620'][0] + '.b2nd'), 'w').close()
        assert dataset.check_preprocessed(tmp, sp) == 1
        open(os.path.join(pp, lk + '_seg.b2nd'), 'w').close()
        assert _fails(dataset.check_preprocessed, tmp, sp), 'a locked id in preprocessed passed'
        assert _fails(dataset.check_converter_line, dict(pins.CONVERTER_LINE, d3=46))
        assert dataset.check_converter_line(dict(pins.CONVERTER_LINE))
        os.makedirs(os.path.join(tmp, 'w'))
        open(os.path.join(tmp, 'w', 'ce_class_weights.json'), 'w').close()
        assert _fails(dataset.check_no_class_weights, os.path.join(tmp, 'w'))
    finally:
        shutil.rmtree(tmp)
    return 'locked id in imagesTr or preprocessed refused; used dataset id refused; converter line and class ' \
           'weights checked'


def t_verdict():
    """13. The verdict table (F-A6, F-A32), both Q-F2-3 answers, and V's clauses (FP 1.2 fails; a uniform -0.03
    LCx recall loss fires L3); broken: F-A32 without V_L."""
    import itertools
    B = (True, False)
    for q3 in ('no', None):
        for v, bf, bt, la in itertools.product(B, B, B, B):
            r = verdict.verdict(v, bf, bt, la, v_L=True, b_TL=True, q3=q3)
            assert r == ('F' if v and bf else 'T' if bt else 'not adopted')
    vv = verdict.verdict
    assert vv(True, True, True, False, q3='yes') == 'F' and vv(False, True, True, False, q3='yes') == 'T'
    assert vv(True, True, True, True, v_L=True, b_TL=True, q3='yes') == 'F'
    assert vv(True, True, True, True, v_L=False, b_TL=True, q3='yes') == 'T_L'
    assert vv(True, True, True, True, v_L=False, b_TL=False, q3='yes') == 'F'
    assert vv(False, True, True, True, v_L=False, b_TL=True, q3='yes') == 'T_L'
    assert vv(False, True, True, True, v_L=False, b_TL=False, q3='yes') == 'T'
    assert vv(True, False, False, True, v_L=True, b_TL=False, q3='yes') == 'not adopted'
    assert _fails(vv, True, True, True, True, q3='yes')

    def rows(n, d, seed, rec=0.0, fp=0.3, base=False):
        rng = np.random.default_rng(seed)
        out = []
        for i in range(n):
            b = 0.9 + 0.04 * np.random.default_rng(1000 + i).standard_normal()
            e = 0.0 if base else 0.02 * rng.standard_normal()
            out.append(dict(case=f'c{i:04d}', provisional=False, flagged_classes=[],
                            per_class={c: float(b + (0 if base else d) + e) for c in verdict.CLASSES},
                            recall={c: float(0.95 + (0 if base else (rec if c == 'LCx' else 0.0) + e))
                                    for c in verdict.CLASSES}, fp_components=fp))
        return out
    base = rows(100, 0, 0, base=True)
    assert not verdict.v_gate(base, rows(100, 0.0, 1, rec=-0.03))['parts']['L3']
    assert not verdict.v_gate(base, rows(100, 0.01, 3, fp=1.2))['parts']['fp']
    assert verdict.v_gate(base, rows(100, 0.0, 4))['passed']
    assert _fails(verdict.v_gate, base, rows(100, 0, 4)[:99], expect_cases=[r['case'] for r in base])
    return 'verdict table under Q-F2-3 yes and no; V: L3, FP and a missing case refused'


def t_ledger():
    """14. The looks ledger: opened once; a second J1F-A refuses; T_L is a reading only when F-A32 applies; a third
    look refuses."""
    tmp = tempfile.mkdtemp()
    try:
        p = os.path.join(tmp, 'results', 'looks.json')
        assert _fails(ledger.open_look, p, 'J1F-A', ['F', 'T', 'T_L'], False)
        e = ledger.open_look(p, 'J1F-A', ['F', 'T'], False, 'yes')
        assert e['look'] == 1
        assert _fails(ledger.open_look, p, 'J1F-A', ['F', 'T'], False), 'a second J1F-A passed'
        ledger.open_look(p, 'J1F-2', ['F', 'T'], False)
        with open(p) as f:
            looks = json.load(f)
        looks.append({'look': 3, 'candidate': 'X'})
        with open(p, 'w') as f:
            json.dump(looks, f)
        assert _fails(ledger.open_look, p, 'J1F-2', ['F', 'T'], False)
    finally:
        shutil.rmtree(tmp)
    return 'second J1F-A refused; T_L only under F-A32; third look refused'


def t_pins():
    """15. The four pins print and pass; an exported J1F_SCORER_SHA256 / J1F_GATES_SHA256 that is not the hash of
    record refuses."""
    lines = pins.check_four(env={})
    assert len(lines) == 4 and all(line.endswith('OK') for line in lines)
    assert _fails(pins.check_four, None, {'J1F_GATES_SHA256': '09ddb06f' + '0' * 56})
    assert _fails(pins.check_four, None, {'J1F_SCORER_SHA256': 'd615c7e7' + '0' * 56})
    return 'four pins OK; a superseded exported hash refused'


def t_sbatch():
    """16. The SBATCH headers are exactly F-A34's."""
    g = sbatch.header('train', 'x', 'l')
    for line in ('--account=def-aso22_gpu', '--gpus-per-node=h100:1', '--cpus-per-task=12', '--mem=280G',
                 '--time=23:50:00'):
        assert f'#SBATCH {line}\n' in g, line
    assert '#SBATCH --time=6:00:00\n' in sbatch.header('predict', 'x', 'l')
    c = sbatch.header('prep', 'x', 'l')
    for line in ('--account=def-aso22', '--cpus-per-task=16', '--mem=64G'):
        assert f'#SBATCH {line}\n' in c, line
    assert 'gpus' not in c and 'def-aso22_gpu' not in c
    assert _fails(sbatch.header, 'gpu', 'x', 'l')
    return 'GPU: def-aso22_gpu, h100:1, 12 cores, 280G, 23:50:00 / 6:00:00; CPU: def-aso22, 16 cores, 64G'


def t_collect_wait():
    """17. D55 Q-F3-1: collect waits only when Q-F2-3 is yes, 1-L is not adopted, and 1-L's collect was submitted
    when a1's predict ended; at most 14 days."""
    tmp = tempfile.mkdtemp()
    try:
        st = collect.env_state({'J1F_JANUS1L_COLLECT_SUBMITTED': '1'})
        assert _fails(collect.wait_gate, tmp, st), 'collect started before a1 predicted'
        open(os.path.join(tmp, '.predict_done_a1'), 'w').close()
        now = datetime.datetime.now(datetime.timezone.utc)
        assert collect.wait_gate(tmp, st, now)[0] == 'wait'
        assert collect.wait_gate(tmp, st, now + datetime.timedelta(days=15))[0] == 'go'
        assert collect.wait_gate(tmp, collect.env_state({'J1F_Q_F2_3': 'no'}), now)[0] == 'go'
        assert collect.wait_gate(tmp, collect.env_state({'J1F_JANUS1L_ADOPTED': '1', 'J1F_JANUS1L_MAPS': tmp}),
                                 now)[0] == 'go'
        os.remove(os.path.join(tmp, 'collect_wait.json'))
        assert collect.wait_gate(tmp, collect.env_state({}), now)[0] == 'go'
        assert _fails(collect.env_state, {'J1F_JANUS1L_ADOPTED': '1'})
    finally:
        shutil.rmtree(tmp)
    return 'waits only under Q-F2-3 yes with 1-L collect submitted; 14 days at most'


TESTS = [t_parent_copy, t_hierarchical_decode, t_fa19_T, t_G_round_trip, t_fa20_val, t_chunk_hygiene, t_plans,
         t_scorer_and_gates, t_ignore13, t_no_locked_in_719, t_verdict, t_ledger, t_pins, t_sbatch, t_collect_wait]


def run_all(names=None):
    fails = 0
    for t in TESTS:
        if names and t.__name__[2:] not in names:
            continue
        try:
            msg = t()
            print(f'selftest {t.__name__[2:]:20s} PASS  {msg}', flush=True)
        except Exception as e:  # noqa: BLE001 - every failure is printed, then check stops
            fails += 1
            print(f'selftest {t.__name__[2:]:20s} FAIL  {e!r}', flush=True)
    return fails


if __name__ == '__main__':
    sys.exit(1 if run_all(sys.argv[1:]) else 0)
