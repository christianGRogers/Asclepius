"""Re-run the origin-collapse check (labels_r2.collapse4 vs territory.to_four) on every case pass 1 flagged or that
has a left PDA/PLA. pass 1 ran an earlier collapse4 that judged PDA and PLB pieces separately. Usage:
python3 recheck_collapse.py <label_dir> <pass1.jsonl> <out.json>"""
import json, os, sys
import numpy as np, nibabel as nb
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path[:0] = [HERE, f'{HERE}/../../../trillium/icx4/lib']
import labels_r2 as L, territory  # noqa
from pass1 import TRAIN  # noqa
rows = [json.loads(l) for l in open(sys.argv[2])]
todo = [r['case'] for r in rows if r['collapse_mismatch'] or r['post']['L-PDA'] or r['post']['L-PLA']]
res = {}
for c in todo:
    assert c in TRAIN
    im = nb.load(os.path.join(sys.argv[1], f'{int(c[1:]) + 1}.coronary.nii.gz')); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8); raw = raw[L.crop(raw, 4)]
    lab, _ = L.map13(raw, z)
    mm = (L.collapse4(lab, z) != territory.to_four(raw, z)) & (lab != 255)
    res[c] = {'mismatch': int(mm.sum()), 'mismatch_other_voxels': int((mm & (raw == 14)).sum()),
              'mismatch_left_posterior': int((mm & np.isin(raw, [12, 13])).sum())}
tot = {k: sum(v[k] for v in res.values()) for k in ('mismatch', 'mismatch_other_voxels', 'mismatch_left_posterior')}
json.dump({'cases': res, 'n_rechecked': len(res), 'total': tot, 'cases_with_mismatch': sum(v['mismatch'] > 0 for v in res.values())},
          open(sys.argv[3], 'w'), indent=1)
print(len(res), tot)
