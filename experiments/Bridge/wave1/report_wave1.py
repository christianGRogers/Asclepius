"""Wave-1 report (Round 9 A31): f and k with the A10 power re-run and the pre-registered seal extension;
seed-vs-read against inter-read per class; model-vs-read per source. CPU, from score_wave1.py's rows.

Pre-registered rules applied as written (Round 9 A31, Bridge v8 §5; nothing here is tuned on wave-1 data):

* **f** (per class) = SD over patients of model-vs-read tF1 on the pool / SD over cases of the model's tF1 on
  ImageCAS-X val (icx4's own per-case val, ``--val``). **k** (per class) = SD over patients of inter-read tF1 /
  SD over patients of model-vs-read tF1. Both on the **primary** stratum only (the A10 population, D29).
* **Extension:** if f or k > 1.2 in any class, the seal extends along its pre-registered order **before any
  sealed read is scored**: to 200 patients, or to 250 if the re-run power at 200 is below 0.8 (δ = 0). If 250
  is still below 0.8, that is reported for the lead; the seal does not grow further by rule.
* **Seed flag (A31.2):** per class, mean seed-vs-read ≥ mean inter-read − 0.02 → the reads are seed-anchored in
  that class: the A23 diagnostic is reported first beside A10 and the question goes to the lead (Round 9 L5).
* **Per source (A31.3):** model-vs-read tF1 with patient-bootstrap CIs. A report only; it decides nothing.

Decisive numbers use non-provisional rows (TotalSegmentator aorta present, A1a) and unflagged classes (A1b).
``--allow-provisional`` exists for the synthetic self-test only; every number it produces is marked provisional.

Usage: report_wave1.py <per_volume.jsonl> --val <icx4 val per_case.jsonl> --out <dir> [--allow-provisional]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import power  # noqa: E402

NAMES = list(C.CLASSES.values())
THRESH_FK = 1.2
SEED_MARGIN = 0.02
POWER_OK = 0.8
NS = (150, 200, 250)
# trigger_false_alarm.py: P(the rule fires) when truly f = k = 1, by number of primary patients
FALSE_ALARM = {20: 0.817, 30: 0.71, 50: 0.542, 75: 0.395, 100: 0.286, 150: 0.183}
# D29: own stratum (anomalous anatomy) and out of A10 until re-gridded (header spacing suspect)
ANOMALOUS = {'ImageCHD', 'ImageALCAPA'}
SPACING_SUSPECT = {'ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF'}


def stratum(source):
    if source in ANOMALOUS:
        return 'anomalous'
    if source in SPACING_SUSPECT:
        return 'spacing_suspect'
    return 'primary'


def load_val(path):
    """icx4 val per-case tF1 per class (unflagged). Accepts Delta's per_case.jsonl (split, tf1_<class>,
    flagged_classes) or atlas2's per_case list (per_class {1..4}, flagged_classes [ints])."""
    txt = open(path).read().strip()
    rows = json.loads(txt) if txt.startswith('[') else [json.loads(l) for l in txt.splitlines() if l.strip()]
    out = {n: [] for n in NAMES}
    for r in rows:
        if r.get('split', 'val') != 'val':
            continue
        fl = {C.CLASSES[x] if isinstance(x, int) else x for x in r.get('flagged_classes', [])}
        for c, n in C.CLASSES.items():
            v = r.get(f'tf1_{n}', (r.get('per_class') or {}).get(str(c)))
            if v is not None and n not in fl and np.isfinite(v):
                out[n].append(float(v))
    return {n: np.array(v) for n, v in out.items()}


def per_patient(rows, comp):
    """patient -> class -> mean over that patient's volumes of the unflagged value."""
    acc = defaultdict(lambda: defaultdict(list))
    for r in rows:
        c = r.get(comp)
        if not c:
            continue
        for n, v in c['per_class'].items():
            if n not in c['flagged']:
                acc[r['patient']][n].append(v)
    return {p: {n: float(np.mean(v)) for n, v in d.items()} for p, d in acc.items()}


def vec(pp, n, patients=None):
    return [d[n] for p, d in pp.items() if n in d and (patients is None or p in patients)]


def ratio_ci(num_pp, den, n, patients, den_pp=None, n_boot=2000, seed=0):
    """f (den = val SD, a number) or k (den_pp = model per patient). Point estimate and a patient bootstrap."""
    pts = sorted(p for p in patients if n in num_pp.get(p, {}) and (den_pp is None or n in den_pp.get(p, {})))
    if len(pts) < 3:
        return None, None, len(pts)
    def est(sample):
        a = [num_pp[p][n] for p in sample]
        s = C.sd(a)
        d = C.sd([den_pp[p][n] for p in sample]) if den_pp is not None else den
        return None if not s or not d else s / d
    e = est(pts)
    rng = np.random.default_rng(seed)
    b = [est([pts[i] for i in rng.integers(0, len(pts), len(pts))]) for _ in range(n_boot)]
    b = [x for x in b if x is not None]
    ci = [round(float(np.percentile(b, 2.5)), 3), round(float(np.percentile(b, 97.5)), 3)] if b else None
    return (round(e, 3) if e is not None else None), ci, len(pts)


def build(rows, val, seal, allow_prov=False):
    n_err = sum('error' in r for r in rows)
    ok = [r for r in rows if 'error' not in r]
    n_prov = sum(r.get('provisional', True) for r in ok)
    if not allow_prov:
        ok = [r for r in ok if not r.get('provisional', True)]
    for r in ok:   # defence in depth: the scorer refuses these already
        if seal.reason(r['volume']):
            raise C.SealedVolumeError(f"{r['volume']}: {seal.reason(r['volume'])}")
    pp = {comp: per_patient(ok, comp) for comp in ('inter', 'model', 'seed')}
    src_of = {r['patient']: r['source'] for r in ok}
    primary = {p for p, s in src_of.items() if stratum(s) == 'primary'}
    out = {'provisional': bool(allow_prov and n_prov), 'n_rows': len(rows), 'n_errors': n_err,
           'n_provisional_rows': n_prov, 'n_patients': len(src_of), 'n_primary_patients': len(primary),
           'patients_by_stratum': {s: sum(stratum(v) == s for v in src_of.values())
                                   for s in ('primary', 'anomalous', 'spacing_suspect')}}
    val_sd = {n: C.sd(val[n]) for n in NAMES}
    out['val'] = {n: {'n': int(len(val[n])), 'mean': round(float(val[n].mean()), 4) if len(val[n]) else None,
                      'sd': round(val_sd[n], 4) if val_sd[n] else None} for n in NAMES}
    # ---- A31.1 f and k --------------------------------------------------------------------------------------
    fk = {}
    for n in NAMES:
        f, fci, fn = ratio_ci(pp['model'], val_sd[n], n, primary)
        k, kci, kn = ratio_ci(pp['inter'], None, n, primary, den_pp=pp['model'])
        n_any = sum(1 for p in primary if p in pp['model'] or p in pp['inter'])
        keep = (sum(1 for p in primary if n in pp['model'].get(p, {})) / n_any) if n_any else None
        fk[n] = {'f': f, 'f_ci': fci, 'f_n': fn, 'k': k, 'k_ci': kci, 'k_n': kn,
                 'scorable_share': round(keep, 3) if keep is not None else None}
    out['f_k'] = fk
    measurable = all(fk[n]['f'] is not None and fk[n]['k'] is not None for n in NAMES)
    trig = [f'{n} {x}={fk[n][x]}' for n in NAMES for x in ('f', 'k') if fk[n][x] is not None and fk[n][x] > THRESH_FK]
    ext = {'triggered': bool(trig), 'because': trig, 'measurable': measurable}
    if measurable and all(len(val[n]) >= 5 for n in NAMES):
        base = {n: val[n] for n in NAMES}
        f = {n: fk[n]['f'] for n in NAMES}
        k = {n: fk[n]['k'] for n in NAMES}
        keep = {n: fk[n]['scorable_share'] or 0.0 for n in NAMES}
        table = {}
        for nn in NS:
            for delta in (0.0, -0.02):
                pa, per = power.p_pass(base, f, k, keep, nn, delta)
                table[f'n{nn}_delta{delta:+.2f}'] = {'p_all4': pa, 'per_class': per}
        out['power'] = table
        if trig:
            size = next((nn for nn in (200, 250) if table[f'n{nn}_delta+0.00']['p_all4'] >= POWER_OK), 250)
            ext['extend_to'] = size
            ext['underpowered_at_250'] = table['n250_delta+0.00']['p_all4'] < POWER_OK
            ext['added_patients'] = seal.extension_order[:size - 150]
        else:
            ext['extend_to'] = 150
    else:
        out['power'] = None
        ext['note'] = 'f or k not measurable in every class (fewer than 3 primary patients with values)'
    out['extension'] = ext
    # ---- Round 10 (Bridge v9): rule C on s_d = SD over patients of (model-vs-read - inter-read) -------------
    # A10's power depends only on s_d per class and the scorable share; s_d already contains f, k and rho.
    # Rule C: the smallest of 150 / 200 / 250 whose re-powered P(all four pass, delta = 0) >= 0.80 (else 250).
    # It replaces the f/k ratio trigger above if the judge adopts it; the f/k columns stay as a report.
    sd_d, rho, keep_c = {}, {}, {}
    for n in NAMES:
        pts = [p for p in primary if n in pp['model'].get(p, {}) and n in pp['inter'].get(p, {})]
        d = [pp['model'][p][n] - pp['inter'][p][n] for p in pts]
        sd_d[n] = C.sd(d)
        if len(pts) >= 3:
            a = np.array([pp['model'][p][n] for p in pts]); b = np.array([pp['inter'][p][n] for p in pts])
            rho[n] = round(float(np.corrcoef(a, b)[0, 1]), 3) if a.std() > 0 and b.std() > 0 else None
        else:
            rho[n] = None
        keep_c[n] = fk[n]['scorable_share']
    rc = {'s_d': {n: (round(v, 4) if v else None) for n, v in sd_d.items()}, 'rho_model_inter': rho,
          'scorable_share': keep_c, 'n_patients': {n: fk[n]['k_n'] for n in NAMES}}
    if all(sd_d[n] and keep_c[n] for n in NAMES):
        from math import erf, sqrt
        phi = lambda x: 0.5 * (1 + erf(x / sqrt(2)))  # noqa: E731
        pw = {nn: float(np.prod([phi(0.05 * sqrt(max(5, round(nn * keep_c[n]))) / sd_d[n] - 1.96) for n in NAMES]))
              for nn in (150, 200, 250)}
        rc['power'] = {str(k): round(v, 3) for k, v in pw.items()}
        rc['seal_size'] = next((nn for nn in (150, 200, 250) if pw[nn] >= POWER_OK), 250)
        rc['underpowered_at_250'] = pw[250] < POWER_OK
    else:
        rc['note'] = 's_d not measurable in every class'
    out['rule_c'] = rc
    # ---- A31.2 seed-vs-read ----------------------------------------------------------------------------------
    seed = {}
    for n in NAMES:
        s = C.boot_ci(vec(pp['seed'], n, primary))
        i = C.boot_ci(vec(pp['inter'], n, primary))
        flag = None if s[0] is None or i[0] is None else bool(s[0] >= i[0] - SEED_MARGIN)
        seed[n] = {'seed_vs_read': s, 'inter_read': i, 'seed_anchored': flag}
    out['seed'] = seed
    # report only: the flag cannot tell "reads kept the seed" from "seed, reads and truth agree"; the edit sizes say
    # how much readers actually changed (D26: every class starts as the whole seed)
    ed = [e for r in ok if r.get('patient') in primary for e in r.get('seed_edit', [])]
    out['seed_edit'] = {'added_share_of_read': C.boot_ci([e['added_share_of_read'] for e in ed]),
                        'removed_share_of_seed': C.boot_ci([e['removed_share_of_seed'] for e in ed]),
                        'reads_unchanged_from_seed_extent': sum(e['added_share_of_read'] == 0 for e in ed),
                        'n_reads': len(ed)}
    out['seed_anchored_classes'] = [n for n in NAMES if seed[n]['seed_anchored']]
    # ---- A31.3 per source (report only) ----------------------------------------------------------------------
    by_src = defaultdict(set)
    for p, s in src_of.items():
        by_src[s].add(p)
    src = {}
    for s, pts in sorted(by_src.items()):
        macro = [np.mean(list(pp['model'][p].values())) for p in pts if pp['model'].get(p)]
        src[s] = {'stratum': stratum(s), 'n_patients': len(pts),
                  'model_vs_read_macro': C.boot_ci(macro),
                  'model_vs_read': {n: C.boot_ci(vec(pp['model'], n, pts)) for n in NAMES},
                  'inter_read': {n: C.boot_ci(vec(pp['inter'], n, pts)) for n in NAMES}}
    out['per_source'] = src
    return out


def markdown(r):
    P = ' **(PROVISIONAL: rows without an aorta; decides nothing)**' if r['provisional'] else ''
    L = [f'# Wave-1 report (Round 9 A31){P}', '',
         f"{r['n_rows']} volumes scored, {r['n_errors']} errors, {r['n_provisional_rows']} without an aorta; "
         f"{r['n_patients']} patients ({r['patients_by_stratum']}).", '',
         '## A31.1 f and k (primary stratum)', '',
         '| Class | val SD (n) | f [95 % CI] (n) | k [95 % CI] (n) | scorable share |', '|---|---|---|---|---|']
    for n in NAMES:
        v, x = r['val'][n], r['f_k'][n]
        L.append(f"| {n} | {v['sd']} ({v['n']}) | {x['f']} {x['f_ci']} ({x['f_n']}) | {x['k']} {x['k_ci']} "
                 f"({x['k_n']}) | {x['scorable_share']} |")
    e = r['extension']
    L += ['', f"**Extension rule (f or k > {THRESH_FK}):** "
          + (('triggered by ' + ', '.join(e['because']) + f" → **extend the seal to {e.get('extend_to')} patients** "
              'along the pre-registered order, before any sealed read is scored.'
              + (' Even 250 is under 0.8 power: report to the lead.' if e.get('underpowered_at_250') else ''))
             if e['triggered'] else f"not triggered; the seal stays at {e.get('extend_to', 150)}.")]
    nf = min(FALSE_ALARM, key=lambda x: abs(x - r['n_primary_patients'])) if r['n_primary_patients'] else None
    if nf:
        L.append(f"- Read with care: at {r['n_primary_patients']} primary patients this pre-registered rule fires by "
                 f"chance about {FALSE_ALARM[nf]:.0%} of the time even when f = k = 1 (trigger_false_alarm.py, n = {nf}). "
                 'Its error is the cautious one (a larger seal), so it is applied as written; the CIs above show '
                 'whether the trigger is clear of noise.')
    if e.get('note'):
        L.append(f"- {e['note']}")
    if r['power']:
        L += ['', '| n | P(all 4 pass), δ = 0 | per class | P(all 4), δ = −0.02 |', '|---|---|---|---|']
        for nn in NS:
            a, b = r['power'][f'n{nn}_delta+0.00'], r['power'][f'n{nn}_delta-0.02']
            L.append(f"| {nn} | {a['p_all4']} | {a['per_class']} | {b['p_all4']} |")
    L += ['', '## A31.2 Seed-vs-read against inter-read', '',
          '| Class | seed-vs-read [CI] (n) | inter-read [CI] (n) | seed-anchored (≥ inter − 0.02) |', '|---|---|---|---|']
    for n in NAMES:
        s = r['seed'][n]
        L.append(f"| {n} | {s['seed_vs_read'][0]} {s['seed_vs_read'][1]} ({s['seed_vs_read'][2]}) | "
                 f"{s['inter_read'][0]} {s['inter_read'][1]} ({s['inter_read'][2]}) | {s['seed_anchored']} |")
    e = r['seed_edit']
    L += ['', f"Seed edits (report only): reads add {e['added_share_of_read'][0]} {e['added_share_of_read'][1]} of their "
          f"voxels beyond the seed and remove {e['removed_share_of_seed'][0]} {e['removed_share_of_seed'][1]} of the seed; "
          f"{e['reads_unchanged_from_seed_extent']} of {e['n_reads']} reads add nothing to it."]
    if r['seed_anchored_classes']:
        L += ['', f"**Seed-anchored in {', '.join(r['seed_anchored_classes'])}.** A10 would compare the model with a "
              'seed-anchored pair: report the A23 diagnostic first beside A10, and put Round 9 L5 to the lead.']
    L += ['', '## A31.3 Model-vs-read per source (report only)', '',
          '| Source | stratum | patients | macro [CI] | LM | LAD | LCx | RCA |', '|---|---|---|---|---|---|---|---|']
    for s, x in r['per_source'].items():
        m = x['model_vs_read_macro']
        L.append(f"| {s} | {x['stratum']} | {x['n_patients']} | {m[0]} {m[1]} | "
                 + ' | '.join(str(x['model_vs_read'][n][0]) for n in NAMES) + ' |')
    return '\n'.join(L) + '\n'


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('rows')
    ap.add_argument('--val', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--seal')
    ap.add_argument('--pool-list', default=C.POOL_LIST)
    ap.add_argument('--allow-provisional', action='store_true')
    a = ap.parse_args(argv)
    seal = C.Seal(a.seal, a.pool_list)
    rows = [json.loads(l) for l in open(a.rows) if l.strip()]
    r = build(rows, load_val(a.val), seal, a.allow_provisional)
    r['seal'] = os.path.relpath(seal.path, C.REPO)
    os.makedirs(a.out, exist_ok=True)
    json.dump(r, open(os.path.join(a.out, 'wave1_report.json'), 'w'), indent=1)
    open(os.path.join(a.out, 'WAVE1.md'), 'w').write(markdown(r))
    print(markdown(r))
    return 0


if __name__ == '__main__':
    sys.exit(main())
