"""Rebuild atlas2's projected-proxy reference (trillium/atlas2/lib/proxy.make_label, read-only import) for given
cases into OUTDIR. ImageCAS-X file N.coronary.nii.gz is case c(N-1). Usage: build_ref.py OUTDIR case ..."""
import sys, os, numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, '/home/user/Asclepius/trillium/atlas2/lib'); sys.path.insert(0, SCR + '/tools')
from proxy import make_label
from girder import mask_path
out = sys.argv[1]; os.makedirs(out, exist_ok=True)
for c in sys.argv[2:]:
    n = int(c[1:]) + 1
    lab, aff, st = make_label(mask_path(c), f'{SCR}/work/Bridge/icx/segmentations/{n}.coronary.nii.gz')
    nib.save(nib.Nifti1Image(lab, aff), f'{out}/{c}.nii.gz'); print(c, st.get('class_vox'), flush=True)
