"""MIP-style views of namer output vs reference on the e2e crop (anterior + superior), for failure inspection."""
import sys, os, json, numpy as np, nibabel as nib
import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
sys.path.insert(0, '/home/user/Asclepius/experiments/Delta')
from analyse_preds import CropGT, remove_small
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from namer import name_mask, load_ostium
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import mask_path
COL = np.array([[0, 0, 0], [230, 184, 0], [230, 40, 40], [40, 120, 255], [40, 200, 80]], np.uint8)
def proj(L, ax):
    nz = L > 0; f = np.argmax(nz, axis=ax); img = np.take_along_axis(L, np.expand_dims(f, ax), ax).squeeze(ax); img[~nz.any(ax)] = 0
    return COL[img]
out, ostw, pdir, which = sys.argv[1:5]
load_ostium(ostw)
for case in sys.argv[5:]:
    meta = json.load(open(f'{pdir}/{case}_meta.json')); lo = np.array(meta['lo']); hi = np.array(meta['hi'])
    gt = CropGT(case, lo, hi); img = nib.load(mask_path(case))
    m = gt.m if which == 'ref' else remove_small(np.load(f'{pdir}/{case}_prob.npy').astype(np.float32) >= 0.5)
    lab, res, _ = name_mask(m, img.affine, gt.sp, lo, img.shape, bridge=4.0)
    fig, ax = plt.subplots(2, 2, figsize=(10, 9))
    for i, L in enumerate((lab, np.where(gt.m, gt.lab, 0))):
        ax[i, 0].imshow(np.rot90(proj(L[:, ::-1, :], 1))); ax[i, 1].imshow(np.rot90(proj(L[:, :, ::-1], 2)))
        ax[i, 0].set_title(f'{case} {"namer" if i == 0 else "reference"} anterior'); ax[i, 1].set_title('superior (anterior up)')
        for a in ax[i]: a.axis('off')
    plt.tight_layout(); plt.savefig(f'{out}/{case}_{which}.png', dpi=55); plt.close()
    print(case, res.get('L_lm_len'), res.get('tree_lens'))
