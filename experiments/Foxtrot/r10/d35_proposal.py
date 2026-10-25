"""Foxtrot, Round 10: a candidate D35 decision set, frozen from names only (no image, no read, no prediction).

Proposal (Foxtrot v6 §3): the D35 decision set is positions 51-100 of the seal's pre-registered extension order
(configs/segqueue14/sealed-pool-2026-10.json, primary.extension_order). That order is already a salted sha256 rank
within source (salt 'asclepius-sealed-round9-pool:', round-robin across sources, D32 real patients), it was fixed
on 2026-10-19 before any read existed, and the wave-1 tools refuse it (experiments/Bridge/wave1/common.py,
EXTENSION_RESERVED = 100). So no new draw and no new salt choice is made here: the list is a deterministic function
of the pinned seal file, and anyone can recompute it. Positions 1-50 stay the seal's extension to 200.

Also written, for the judge's comparison (not proposed): the alternative draw from the 61 open primary patients
(new salt 'asclepius-d35-round10:', patient-level, proportional within source, n = 30), and the volume lists the
plan's Fir jobs use (what Janus 0 may predict now; what Janus 1 may train on).
Output: d35_proposal.json (this folder). Usage: python experiments/Foxtrot/r10/d35_proposal.py
"""
import hashlib, json, os, sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient, load_pool_seal  # noqa: E402

POOL = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
SEAL_SHA = 'e71141b4'          # the D32 pin's prefix (vault/Plans/Experiments/Wave 1 - measurement plan and tools.md)
ALT_SALT = 'asclepius-d35-round10:'
REPORT_ONLY = {'ImageCHD', 'ImageALCAPA'}
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def stratum(src):
    return 'excluded' if src in SPACING_SUSPECT else 'report_only' if src in REPORT_ONLY else 'primary'


def main():
    seal_sha = sha(SEAL)
    if not seal_sha.startswith(SEAL_SHA):
        raise SystemExit(f'seal file sha256 {seal_sha} is not the D32 pin {SEAL_SHA}...: refusing')
    seal = json.load(open(SEAL))
    guard = load_pool_seal(SEAL)
    vols = [l.strip() for l in open(POOL) if l.strip() and not l.startswith('#')]
    by_pat = defaultdict(list)
    for v in vols:
        by_pat[ingest_patient(v[:-len('.nii.gz')])].append(v)
    ext = list(seal['primary']['extension_order'])
    sealed = set(seal['primary']['patients']) | set(seal['report_only']['patients'])
    ext200, d35 = ext[:50], ext[50:100]
    assert not (set(d35) & sealed) and not (set(ext200) & set(d35))
    for p in d35:
        assert not any(guard.is_sealed(v) for v in by_pat[p]), p
    held = sealed | set(ext[:100])
    open_pats = sorted(p for p in by_pat if p not in held)
    src = lambda p: p.split('__')[0]
    open_primary = [p for p in open_pats if stratum(src(p)) == 'primary']

    # the alternative (not proposed): 30 of the open primary patients, proportional within source
    by_src = defaultdict(list)
    for p in open_primary:
        by_src[src(p)].append(p)
    rank = lambda p: hashlib.sha256((ALT_SALT + p).encode()).hexdigest()
    n_alt, tot = 30, len(open_primary)
    quota = {s: n_alt * len(v) / tot for s, v in by_src.items()}
    alloc = {s: int(q) for s, q in quota.items()}
    for s in sorted(quota, key=lambda s: -(quota[s] - int(quota[s])))[: n_alt - sum(alloc.values())]:
        alloc[s] += 1
    alt = sorted(p for s, v in by_src.items() for p in sorted(v, key=rank)[:alloc[s]])

    def block(pats):
        return {'n_patients': len(pats), 'n_volumes': sum(len(by_pat[p]) for p in pats),
                'by_source': {s: sum(1 for p in pats if src(p) == s) for s in sorted({src(p) for p in pats})},
                'patients': sorted(pats), 'volumes': sorted(v for p in pats for v in by_pat[p])}

    out = {
        'what': 'Foxtrot v6 candidate D35 decision set (Round 10). Not binding until the judge and the lead adopt it.',
        'derived_from': {'seal_file': 'configs/segqueue14/sealed-pool-2026-10.json', 'seal_sha256': seal_sha,
                         'rule': 'primary.extension_order[50:100]', 'salt_of_that_order': seal['salt']},
        'proposed_d35': block(d35),
        'seal_extension_to_200': block(ext200),
        'trainable_now': {'primary_open': block(open_primary),
                          'report_only_open (ImageCHD)': block([p for p in open_pats if stratum(src(p)) == 'report_only']),
                          'excluded_open (suspect spacing; train only once re-gridded)':
                              block([p for p in open_pats if stratum(src(p)) == 'excluded'])},
        'extension_tail_101': block(ext[100:]),
        'alternative_not_proposed_open_draw_30': dict(block(alt), salt=ALT_SALT, allocation=alloc),
    }
    pred = sorted(set(out['proposed_d35']['volumes']) |
                  {v for b in out['trainable_now'].values() for v in b['volumes']} |
                  set(out['extension_tail_101']['volumes']))
    out['janus0_may_predict_now'] = {'n_volumes': len(pred), 'rule': 'every pool volume of a patient that is neither '
                                     'sealed nor in the extension to 200', 'volumes': pred}
    path = os.path.join(HERE, 'd35_proposal.json')
    json.dump(out, open(path, 'w'), indent=1)
    print('written', path, 'sha256', sha(path))
    for k in ('proposed_d35', 'seal_extension_to_200', 'extension_tail_101', 'alternative_not_proposed_open_draw_30'):
        print(k, out[k]['n_patients'], 'patients', out[k]['n_volumes'], 'volumes', out[k]['by_source'])
    for k, b in out['trainable_now'].items():
        print('trainable', k, b['n_patients'], 'patients', b['n_volumes'], 'volumes')
    print('janus0_may_predict_now', len(pred))


if __name__ == '__main__':
    main()
