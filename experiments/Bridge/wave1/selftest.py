"""End-to-end self-test of the wave-1 tools on synthetic pool reads (no real read exists yet).

Two waves of N open (non-sealed, non-reserved) pool volumes:
  independent  each reader trims the seed's distal ends on their own, and both drop the seed's vein;
  anchored     both reads are the seed minus its vein (D26's worst case: readers keep the seed's extent).
Expected: the seed flag stays off for 'independent' and fires in every class for 'anchored'.
Also checks that a sealed volume in the export stops the scorer before anything is opened.
Usage: selftest.py <workdir> [N] [--val <per-case val file>]
"""
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import common as C  # noqa: E402
import synth  # noqa: E402


def run(*args):
    r = subprocess.run([sys.executable, *args], capture_output=True, text=True, cwd=HERE)
    return r.returncode, r.stdout, r.stderr


def wave(work, name, volumes, anchored, val):
    root = os.path.join(work, name)
    rng = np.random.default_rng(7 if anchored else 3)
    for v in volumes:
        dirs = synth.write(root, v, rng, anchored=anchored)
    rows = os.path.join(root, 'rows.jsonl')
    if os.path.exists(rows):
        os.remove(rows)
    code, out, err = run('score_wave1.py', '--reads', dirs['reads'], '--seeds', dirs['seeds'], '--pred',
                         dirs['pred'], '--aorta', dirs['aorta'], '--out', rows, '--nproc', '4')
    assert code == 0, err
    code, out, err = run('report_wave1.py', rows, '--val', val, '--out', os.path.join(root, 'report'))
    assert code == 0, err
    return json.load(open(os.path.join(root, 'report', 'wave1_report.json'))), dirs


def main():
    work = sys.argv[1]
    n = int(sys.argv[2]) if len(sys.argv) > 2 and not sys.argv[2].startswith('-') else 24
    val = sys.argv[sys.argv.index('--val') + 1] if '--val' in sys.argv else os.path.join(
        C.REPO, 'trillium-results', 'round6', 'atlas2', 'results', 'per_case_run1.json')
    seal = C.Seal()
    open_vols = [v for v in sorted(seal.pool) if not seal.reason(v)]
    # one volume per patient, primary sources, spread over sources
    by_p = {}
    for v in open_vols:
        if C.corrected_key(v) not in by_p and C.source_of(v) not in ('ImageCHD', 'ImageALCAPA', 'HOCMvalvesSeg',
                                                                   'CCA200-HF'):
            by_p[C.corrected_key(v)] = v
    vols = list(by_p.values())[::max(1, len(by_p) // n)][:n]
    res = {}
    for name, anchored in (('independent', False), ('anchored', True)):
        r, dirs = wave(work, name, vols, anchored, val)
        res[name] = {'seed_anchored_classes': r['seed_anchored_classes'],
                     'seed': {k: (v['seed_vs_read'][0], v['inter_read'][0]) for k, v in r['seed'].items()},
                     'f_k': {k: (v['f'], v['k']) for k, v in r['f_k'].items()},
                     'extension': r['extension'], 'n_primary_patients': r['n_primary_patients'],
                     'power_n150': (r['power'] or {}).get('n150_delta+0.00')}
    assert res['independent']['seed_anchored_classes'] == [], res['independent']
    assert set(res['anchored']['seed_anchored_classes']) == {'LM', 'LAD', 'LCx', 'RCA'}, res['anchored']
    # refusal: plant a sealed volume's folder in the export; the scorer must stop before opening anything
    sealed_vol = sorted(seal.sealed_volumes)[0]
    os.makedirs(os.path.join(dirs['reads'], sealed_vol[:-7], 'segmentations'), exist_ok=True)
    code, out, err = run('score_wave1.py', '--reads', dirs['reads'], '--out', os.path.join(work, 'refused.jsonl'))
    assert code != 0 and 'SealedVolumeError' in err, (code, err[-400:])
    res['refusal'] = 'a sealed folder in the export stopped the scorer (exit %d)' % code
    os.rmdir(os.path.join(dirs['reads'], sealed_vol[:-7], 'segmentations'))
    os.rmdir(os.path.join(dirs['reads'], sealed_vol[:-7]))
    json.dump(res, open(os.path.join(work, 'selftest.json'), 'w'), indent=1)
    print(json.dumps(res, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
