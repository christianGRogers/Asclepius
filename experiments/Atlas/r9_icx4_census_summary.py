"""Summarise r9_icx4_census.py's JSON into the tables of the vault note. Usage: python r9_icx4_census_summary.py <census.json>"""
import json, sys, statistics as st

rows = json.load(open(sys.argv[1]))
N = ['LM', 'LAD', 'LCx', 'RCA']


def q(xs, p):
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None


print(f'cases: {len(rows)}; by split:', {s: sum(r["split"] == s for r in rows) for s in ("train", "val", "test")})
print('\n| Class | cases with it | median mm³ | side-branch share of class volume (median, p90) | cases with > 1 component ≥ 20 vox | voxels outside largest component (mean %) |')
print('|---|---|---|---|---|---|')
for n in N:
    pres = [r['cls'][n] for r in rows if r['cls'][n]['vox']]
    print(f"| {n} | {len(pres)} / {len(rows)} | {st.median(d['mm3'] for d in pres):.0f} | "
          f"{st.median(d['side_share'] for d in pres):.2f}, {q([d['side_share'] for d in pres], 0.9):.2f} | "
          f"{sum(d['components_ge20'] > 1 for d in pres)} | {100 * st.mean(d['outside_largest_share'] for d in pres):.2f} |")
tot = [sum(r['cls'][n]['vox'] for n in N) for r in rows]
print('\nclass share of tree voxels (mean over cases):',
      {n: round(st.mean(r['cls'][n]['vox'] / t for r, t in zip(rows, tot) if t), 4) for n in N})
print('tree components (26-conn) per case:', {k: sum(r['tree_components'] == k for r in rows) for k in sorted({r['tree_components'] for r in rows})})
oth = [r for r in rows if r['other_vox']]
print(f'Other (14) present: {len(oth)} cases; mean share of tree voxels where present: '
      f'{st.mean(r["other_vox"] / t for r, t in zip(rows, tot) if r["other_vox"] and t):.4f}')
im = [r for r in rows if r['im_present']]
print(f'ramus (IM) present: {len(im)} cases; IM a separate LCx-class component (not touching LCx main): '
      f'{sum(r.get("im_separate_from_lcx_main", False) for r in im)}')
lm0 = [r['case'] for r in rows if not r['cls']['LM']['vox']]
print(f'no LM: {len(lm0)} cases', lm0[:10])
for n in ('LAD', 'LCx', 'RCA'):
    z = [r['case'] for r in rows if not r['cls'][n]['vox']]
    print(f'no {n}: {len(z)}', z[:10])
