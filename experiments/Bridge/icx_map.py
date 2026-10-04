"""Map ImageCAS-X ids to our case ids. Hypothesis: cNNNN = ImageCAS id NNNN+1 (upload order).
Check: shape, in-plane spacing and x/y origin must match exactly (z origin differs on ingest)."""
import sys, os, glob, json, nibabel as nib, numpy as np
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
dirs = sys.argv[1].split(','); out = sys.argv[2]
files = {}
for d in dirs:
    for p in glob.glob(os.path.join(d, '**', '*.coronary.nii.gz'), recursive=True):
        if os.path.getsize(p) > 1000:
            files.setdefault(int(os.path.basename(p).split('.')[0]), p)
ok, bad, res = 0, [], {}
for k, p in sorted(files.items()):
    c = f'c{k-1:04d}'
    try:
        a = nib.load(p); b = nib.load(mask_path(c)); a.header.get_zooms()
    except Exception:
        continue
    same = a.shape == b.shape and np.allclose(a.affine[:2], b.affine[:2], atol=1e-3) and np.allclose(a.header.get_zooms(), b.header.get_zooms())
    if same:
        ok += 1; res[c] = [k, p]
    else:
        bad.append((k, c, a.shape, b.shape))
json.dump(res, open(out, 'w'))
print('icx files', len(files), 'header-consistent', ok, 'mismatch', len(bad), bad[:5])
