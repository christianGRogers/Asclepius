"""Run census14.one on the 7 cases re-admitted after track 1-L's L-A1 and merge them into census14_per_case.json.
Usage: python3 census7.py <label_dir> <split620.json> <results_dir>"""
import json, os, sys
from multiprocessing import Pool
import census14
lab, sj, res = sys.argv[1:4]
seven = json.load(open(sj))['ambiguous_7_excluded_from_census']
files = [os.path.join(lab, f'{int(c[1:]) + 1}.coronary.nii.gz') for c in seven]
with Pool(4) as p:
    new = p.map(census14.one, files)
pc = os.path.join(res, 'census14_per_case.json')
allr = [r for r in json.load(open(pc)) if r['case'] not in seven] + new
assert len(allr) == 620, len(allr)
json.dump(sorted(allr, key=lambda r: r['case']), open(pc, 'w'))
print('merged', len(allr))
