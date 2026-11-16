"""Summarise census.jsonl (620 Janus 1 training cases) into the numbers Bridge v1 (Janus 1-F, Round 1) uses.

  1. Class census: cases with each ImageCAS-X class, volume, centreline length, lumen diameter.
  2. "Other": which parent each component touches; how many cases hold a third LAD-side branch (a D3) in "Other".
  3. Ordinals: is D1's origin proximal to D2's along the LAD, and OM1's to OM2's along the LCx? If yes, D1/D2/D3 and
     OM1/OM2 are a function of branch TYPE + origin order, and a namer can assign them from a typed segmentation.
  4. Re-derivation: collapse D1, D2 and LAD-side "Other" to one DIAG type (OM1, OM2 and LCx-side "Other" to OM),
     re-assign ordinals by origin, and score the result against ImageCAS-X's own names (branches and voxels).
  5. Dominance as ImageCAS-X defines it (L-PDA from the LCx), for the PDA/PLB mapping question.
  6. Wilson 95 % half-widths for a detection rate at n reads, for the reads-per-class rule.
Usage: analyse.py <census.jsonl> <out.json>"""
import json, math, sys
from collections import Counter, defaultdict
import numpy as np

rows = [json.loads(l) for l in open(sys.argv[1])]
N = len(rows)
CL = ['LM', 'LAD', 'LCx', 'D1', 'D2', 'OM1', 'OM2', 'IM', 'RCA', 'R-PDA', 'R-PLA', 'L-PDA', 'L-PLA', 'Other']
out = dict(n_cases=N)

# 1. census
cen = {}
for c in CL:
    v = [r['classes'][c] for r in rows if c in r['classes']]
    if not v:
        cen[c] = dict(cases=0)
        continue
    f = lambda k: [x[k] for x in v if x.get(k) is not None]
    cen[c] = dict(cases=len(v), share=round(len(v) / N, 3),
                  mm3_median=round(float(np.median(f('mm3'))), 1),
                  len_mm_median=round(float(np.median(f('len_mm'))), 1),
                  diam_median_mm=round(float(np.median(f('d_med'))), 2) if f('d_med') else None,
                  diam_p10_median_mm=round(float(np.median(f('d_p10'))), 2) if f('d_p10') else None,
                  comps_gt1=sum(x['comps'] > 1 for x in v))
out['census'] = cen
sp = [r['spacing'] for r in rows]
out['spacing'] = dict(inplane_min=min(s[0] for s in sp), inplane_max=max(s[0] for s in sp),
                      slice_min=min(s[2] for s in sp), slice_max=max(s[2] for s in sp))

# 2. Other: parent side
LADSIDE, LCXSIDE = {'LAD', 'D1', 'D2'}, {'LCx', 'OM1', 'OM2', 'L-PDA', 'L-PLA'}


def side(b):
    t = b['touch']
    lad = sum(t.get(k, 0) for k in LADSIDE)
    lcx = sum(t.get(k, 0) for k in LCXSIDE)
    other = sum(v for k, v in t.items() if k not in LADSIDE | LCXSIDE)
    if lad == lcx == other == 0:
        return 'none'
    if lad >= max(lcx, other):
        return 'LAD'
    if lcx >= other:
        return 'LCx'
    return 'other:' + max((k for k in t if k not in LADSIDE | LCXSIDE), key=lambda k: t[k])


oth = Counter()
lad_other_per_case = Counter()
for r in rows:
    k = 0
    for b in r['branches']:
        if b['cls'] == 'Other':
            s = side(b)
            oth[s] += 1
            k += s == 'LAD'
    lad_other_per_case[k] += 1
out['other_components_by_side'] = dict(oth)
out['cases_by_LAD_side_other_count'] = {str(k): v for k, v in sorted(lad_other_per_case.items())}
out['cases_with_a_D3_in_Other'] = sum(v for k, v in lad_other_per_case.items() if k >= 1)
out['cases_with_a_D4_in_Other'] = sum(v for k, v in lad_other_per_case.items() if k >= 2)


# 3./4. ordinals and re-derivation
def ordinal_check(rows, names, parent, side_name):
    pair = dict(n=0, ordered=0, tie=0, reversed=0, no_origin=0)
    br_agree = br_total = 0
    vox_agree = vox_total = 0
    rev_cases = []
    per_name = defaultdict(lambda: [0, 0])
    for r in rows:
        bs = [b for b in r['branches'] if b['cls'] in names and b['parent'] == parent]
        bs += [b for b in r['branches'] if b['cls'] == 'Other' and side(b) == side_name and b['parent'] == parent]
        byname = {b['cls']: b for b in bs if b['cls'] != 'Other'}
        a, bb = (byname.get(names[0]), byname.get(names[1]))
        if a and bb:
            pair['n'] += 1
            if a['origin_mm'] is None or bb['origin_mm'] is None:
                pair['no_origin'] += 1
            elif a['origin_mm'] < bb['origin_mm'] - 1.0:
                pair['ordered'] += 1
            elif abs(a['origin_mm'] - bb['origin_mm']) <= 1.0:
                pair['tie'] += 1
            else:
                pair['reversed'] += 1
                rev_cases.append(r['case'])
        # re-derive ordinals from origin order (ties keep the larger branch first, as the protocol does)
        ok = [b for b in bs if b['origin_mm'] is not None]
        ok.sort(key=lambda b: (b['origin_mm'], -b['vox']))
        ref_names = [b['cls'] if b['cls'] != 'Other' else 'Other' for b in ok]
        derived = [names[i] if i < len(names) else 'Other' for i in range(len(ok))]
        for b, d, ref in zip(ok, derived, ref_names):
            br_total += 1
            br_agree += d == ref
            vox_total += b['vox']
            vox_agree += b['vox'] * (d == ref)
            per_name[ref][1] += 1
            per_name[ref][0] += d == ref
    return dict(pair=pair, reversed_cases=rev_cases[:20],
                rederive_branch_agreement=round(br_agree / max(br_total, 1), 4), branches=br_total,
                rederive_voxel_agreement=round(vox_agree / max(vox_total, 1), 4),
                per_reference_name={k: dict(n=v[1], agree=round(v[0] / v[1], 3)) for k, v in per_name.items()})


out['diagonals'] = ordinal_check(rows, ['D1', 'D2'], 'LAD', 'LAD')
out['marginals'] = ordinal_check(rows, ['OM1', 'OM2'], 'LCx', 'LCx')

# parents of the side-branch classes (does each class touch the parent ImageCAS-X implies?)
par = defaultdict(Counter)
for r in rows:
    for b in r['branches']:
        if b['cls'] != 'Other':
            par[b['cls']][b['parent'] or 'none'] += 1
out['branch_parent'] = {k: dict(v) for k, v in par.items()}

# 5. dominance (ImageCAS-X's definitions, from the classes present)
dom = Counter()
for r in rows:
    c = r['classes']
    rp, rl, lp, ll = ('R-PDA' in c), ('R-PLA' in c), ('L-PDA' in c), ('L-PLA' in c)
    if (rp or rl) and (lp or ll):
        dom['co'] += 1
    elif lp:
        dom['left'] += 1
    elif rp and rl:
        dom['right'] += 1
    elif rp and not rl:
        dom['co (R-PDA without R-PLA)'] += 1
    elif ll:
        dom['left (L-PLA only)'] += 1
    else:
        dom['none labelled'] += 1
out['dominance'] = dict(dom)
out['pda_plb_cases'] = dict(PDA_right=cen['R-PDA'].get('cases', 0), PDA_left=cen['L-PDA'].get('cases', 0),
                            PLB_right=cen['R-PLA'].get('cases', 0), PLB_left=cen['L-PLA'].get('cases', 0))


# 6. Wilson half-widths
def wilson_hw(p, n, z=1.96):
    d = 1 + z * z / n
    return z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d


out['wilson_halfwidth'] = {str(n): {str(p): round(wilson_hw(p, n), 3) for p in (0.5, 0.7, 0.85, 0.95)}
                           for n in (10, 20, 30, 50, 80, 120)}
json.dump(out, open(sys.argv[2], 'w'), indent=1)
print(json.dumps(out, indent=1))
