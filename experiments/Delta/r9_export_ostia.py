"""Round 9: export ImageCAS-X's released centreline start points (the ostia) for every non-sealed case, to a small
JSON the Fir scoring job reads (so Fir needs no VTK reader), and check them against a simple label rule.

ImageCAS-X (arXiv:2608.30404, "Postprocessing"): "start points were assigned to centerline vertices with a degree of
1 lying within 5 mm of the aorta" (TotalSegmentator heart-chambers model). They are the `start_points` attribute of
each VTK. A side can have several (separate LAD/LCx ostia, a conus branch); all are kept.
Check rule (no aorta): the free end of the LM line (left) and of the RCA line (right; the one nearest the left
ostium if several).
Coordinates are LPS world mm as in the VTK (nibabel RAS: negate x and y). Sealed cases are refused.

Usage: r9_export_ostia.py <data_dir> <out.json> <repo_root>
"""
import json, os, sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from r9_vtkcl import read, endpoint_degree  # noqa: E402

data, out, root = sys.argv[1:4]
sealed = {int(c[1:]) + 1 for c in json.load(open(f'{root}/trillium/sealed_test.json'))['sealed_icx_test']}
res, stats = {}, {'n_starts': {}, 'leaf_vs_start_mm': {'left': [], 'right': []}, 'start_labels': {}}
ids = sorted(int(f.split('.')[0]) for f in os.listdir(data) if f.endswith('_right_centerline.vtk')
             and os.path.exists(f'{data}/{f.split(".")[0]}.coronary_left_centerline.vtk'))
for i in ids:
    if i in sealed:
        sys.exit(f'refusing sealed case {i}')
    row, left_leaf = {}, None
    for side, lab_root in (('left', 1), ('right', 9)):
        pts, lab, _, lines, starts = read(f'{data}/{i}.coronary_{side}_centerline.vtk')
        row[side] = [[round(float(v), 3) for v in pts[k]] for k in starts]
        key = f'{side}:{len(starts)}'
        stats['n_starts'][key] = stats['n_starts'].get(key, 0) + 1
        for k in starts:
            stats['start_labels'][f'{side}:{int(lab[k])}'] = stats['start_labels'].get(f'{side}:{int(lab[k])}', 0) + 1
        deg = endpoint_degree(lines)
        leaves = [e for e, d in deg.items() if d == 1 and lab[e] == lab_root]
        if side == 'right' and len(leaves) > 1 and left_leaf is not None:
            leaves.sort(key=lambda e: float(np.linalg.norm(pts[e] - left_leaf)))
        if leaves:
            if side == 'left':
                left_leaf = pts[leaves[0]]
            if starts:
                stats['leaf_vs_start_mm'][side].append(
                    round(min(float(np.linalg.norm(pts[leaves[0]] - pts[k])) for k in starts), 2))
    res[f'c{i - 1:04d}'] = row
s = {k: (len(v), float(np.median(v)) if v else None, sum(x > 2 for x in v)) for k, v in stats['leaf_vs_start_mm'].items()}
json.dump({'source': 'ImageCAS-X centerlines (Zenodo 10.5281/zenodo.21887809, CC BY 4.0), attribute start_points',
           'frame': 'LPS world mm (nibabel RAS: negate x and y)', 'n_cases': len(res),
           'check': {'starts_per_side': stats['n_starts'], 'start_point_labels (side:ImageCAS-X class)':
                     stats['start_labels'], 'label_rule_vs_start (n, median mm, n > 2 mm)': s},
           'ostia': res}, open(out, 'w'), indent=0)
print(f'{len(res)} cases; starts per side {stats["n_starts"]}; label rule vs start: {s}')
print('start point labels:', stats['start_labels'])
