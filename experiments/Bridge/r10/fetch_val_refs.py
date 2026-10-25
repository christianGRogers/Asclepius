"""Fetch the ImageCAS-X segmentations of the val 80 only (fold 0; atlas2's val list), by HTTP range requests.

ImageCAS-X (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) stores per-case 14-class masks as
``segmentations/<id>.coronary.nii.gz``; our case ``cNNNN`` is ImageCAS-X id NNNN + 1
([[Crucible - ImageCAS-X is real and its 800 cases are our cases c(id-1)]]). The val list is checked against
``trillium/sealed_test.json`` before anything is downloaded, and no other case is fetched.

Usage: python3 experiments/Bridge/r10/fetch_val_refs.py OUT_DIR    (about 6 MB; needs `pip install remotezip`)
"""
import json
import os
import sys

import remotezip

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
out = sys.argv[1]
os.makedirs(out, exist_ok=True)
val = [r['case'] for r in json.load(open(os.path.join(
    REPO, 'trillium-results', 'round6', 'atlas2', 'results', 'per_case_run1.json')))]
s = json.load(open(os.path.join(REPO, 'trillium', 'sealed_test.json')))
sealed = set(s['sealed_icx_test']) | set(s['sealed_quality0'])
if set(val) & sealed:
    sys.exit('refusing: the val list contains a sealed case')
with remotezip.RemoteZip(URL) as z:
    names = set(z.namelist())
    for c in val:
        n = f'ImageCAS-X_dataset/segmentations/{int(c[1:]) + 1}.coronary.nii.gz'
        dest = os.path.join(out, f'{c}.nii.gz')
        if n in names and not os.path.exists(dest):
            open(dest, 'wb').write(z.read(n))
print('done:', len(os.listdir(out)), 'files in', out)
