"""Janus 1-F round 2 (Atlas): summarise census_r2.jsonl (the 620) into the numbers the candidate quotes.
Usage: python summarise_r2.py <census_r2.jsonl> <Descriptors.xlsx> <out.json>"""
import json
import sys
from collections import Counter

import numpy as np

CLS = ['D1', 'D2', 'D3', 'OM1', 'OM2', 'Ramus', 'PDA', 'PLB']


def q(a, ps=(10, 50, 90)):
    a = np.asarray(a, float)
    return [round(float(np.percentile(a, p)), 2) for p in ps] if len(a) else None


def dominance_xlsx(path):
    try:
        import openpyxl
    except ImportError:
        return {}
    wb = openpyxl.load_workbook(path, read_only=True)
    ws = wb.active
    rows = list(ws.iter_rows(values_only=True))
    hdr = [str(h).strip().lower() if h is not None else '' for h in rows[0]]
    ic = next(i for i, h in enumerate(hdr) if h in ('id', 'case', 'scan', 'patient', 'filename', 'name') or 'id' in h)
    idom = next(i for i, h in enumerate(hdr) if 'domin' in h)
    out = {}
    for r in rows[1:]:
        if r[ic] is None:
            continue
        try:
            k = int(str(r[ic]).split('.')[0])
        except ValueError:
            continue
        out['c%04d' % (k - 1)] = str(r[idom]).strip()
    return out


def main(cen, desc, outp):
    rows = [json.loads(l) for l in open(cen)]
    n = len(rows)
    S = {'n_cases': n}
    # labels / collapse
    S['collapse_mismatch_cases'] = sum(r['collapse_mismatch_vox'] > 0 for r in rows)
    S['collapse_mismatch_vox_total'] = sum(r['collapse_mismatch_vox'] for r in rows)
    mm = Counter()
    for r in rows:
        for k, v in r['collapse_mismatch_by_icx'].items():
            mm[k] += v
    S['collapse_mismatch_by_icx_value'] = dict(mm)
    S['other'] = {k: sum(r['other'][k] for r in rows) for k in rows[0]['other']}
    S['ignore_cases'] = sum(r['ignore_vox'] > 0 for r in rows)
    # pieces
    P = {}
    for c in CLS:
        per = [r['pieces'][c] for r in rows]
        lens = [p['len'] for v in per for p in v]
        tot = [sum(p['len'] for p in v) for v in per]
        P[c] = {'cases_any_piece': sum(len(v) > 0 for v in per),
                'cases_present_5mm': sum(t >= 5 for t in tot), 'cases_present_3mm': sum(t >= 3 for t in tot),
                'pieces': len(lens), 'pieces_per_case': dict(Counter(len(v) for v in per if v)),
                'piece_len_p10_50_90': q(lens), 'pieces_lt5mm': sum(l < 5 for l in lens)}
    S['pieces'] = P
    # band
    B = {}
    for b in rows[0]['band']:
        v = [r['band'][b]['mm3'] for r in rows]
        share = {t: round(float(np.sum([r['band'][b][t] for r in rows]) / np.sum(v)), 3)
                 for t in ('LM', 'LAD', 'LCx', 'RCA')}
        B[b] = {'mm3_p10_50_90': q(v), 'x_tree_volume_median': round(float(np.median(
            [r['band'][b]['mm3'] / r['tree_mm3'] for r in rows])), 1), 'share_by_nearest_territory': share}
    S['band'] = B
    S['tree_mm3_median'] = round(float(np.median([r['tree_mm3'] for r in rows])), 1)
    # side-branch distance from parent: share of traced side-branch centreline (by piece p90/max) inside a band
    D = {}
    for c in CLS:
        v = [x for r in rows for x in r['branch_from_parent'][c]]
        if not v:
            continue
        a = np.asarray(v)
        D[c] = {'pieces': len(a), 'p50_of_piece_median': round(float(np.median(a[:, 0])), 1),
                'p50_of_piece_p90': round(float(np.median(a[:, 1])), 1),
                'p50_of_piece_max': round(float(np.median(a[:, 2])), 1),
                **{f'share_pieces_max_within_{b}mm': round(float((a[:, 2] <= b).mean()), 3) for b in (4, 8, 15)},
                **{f'share_pieces_median_within_{b}mm': round(float((a[:, 0] <= b).mean()), 3) for b in (4, 8, 15)}}
    allv = np.asarray([x for r in rows for c in CLS for x in r['branch_from_parent'][c]])
    D['all'] = {'pieces': len(allv), **{f'share_max_within_{b}mm': round(float((allv[:, 2] <= b).mean()), 3)
                                         for b in (4, 8, 15)},
                **{f'share_p90_within_{b}mm': round(float((allv[:, 1] <= b).mean()), 3) for b in (4, 8, 15)},
                **{f'share_median_within_{b}mm': round(float((allv[:, 0] <= b).mean()), 3) for b in (4, 8, 15)}}
    S['branch_from_parent'] = D
    # trunk twigs: spurs other than the two longest
    T = {}
    for t in ('LAD', 'LCx', 'RCA'):
        tw = [r['trunk_spurs'][t][2:] for r in rows]
        T[t] = {f'cases_with_twig_ge_{L}mm': sum(any(s >= L for s in x) for x in tw) for L in (3, 5, 10)}
        T[t].update({f'twigs_ge_{L}mm': sum(sum(s >= L for s in x) for x in tw) for L in (3, 5, 10)})
    S['trunk_twigs'] = T
    # dominance
    lab = Counter()
    for r in rows:
        p = r['icx_posterior']
        left = p['L-PDA'] or p['L-PLA']
        right = p['R-PDA'] or p['R-PLA']
        lab['left_only' if left and not right else 'right_only' if right and not left else
            'both' if left and right else 'none'] += 1
    S['posterior_by_labels'] = dict(lab)
    S['cases_with_left_pda_or_pla'] = lab['left_only'] + lab['both']
    dx = dominance_xlsx(desc) if desc and desc != '-' else {}
    if dx:
        S['dominance_xlsx'] = dict(Counter(dx.get(r['case'], 'missing') for r in rows))
        cross = Counter()
        for r in rows:
            p = r['icx_posterior']
            cross[(dx.get(r['case'], 'missing'), bool(p['L-PDA'] or p['L-PLA']))] += 1
        S['dominance_xlsx_x_left_posterior'] = {f'{a}|left_posterior={b}': v for (a, b), v in sorted(cross.items())}
    json.dump(S, open(outp, 'w'), indent=1)
    print(json.dumps(S, indent=1)[:6000])


if __name__ == '__main__':
    main(*sys.argv[1:4])
