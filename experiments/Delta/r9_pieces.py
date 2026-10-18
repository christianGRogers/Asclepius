"""Round 9: what the second piece of a multi-piece class is (ImageCAS-X collapsed by territory). For each case and
class with more than one 26-connected piece: piece sizes, and the ImageCAS-X classes in the smaller piece.
Usage: r9_pieces.py <data_dir> <case ids (c0123,...)>"""
import os, sys
import nibabel as nib
import numpy as np
from scipy import ndimage
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'trillium', 'icx4', 'lib'))
from territory import to_four  # noqa: E402
NAMES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}
ICX = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'D1', 5: 'D2', 6: 'OM1', 7: 'OM2', 8: 'IM', 9: 'RCA', 10: 'R-PDA', 11: 'R-PLA',
       12: 'L-PDA', 13: 'L-PLA', 14: 'Other'}
for c in sys.argv[2].split(','):
    img = nib.load(f'{sys.argv[1]}/{int(c[1:]) + 1}.coronary.nii.gz')
    raw = np.asarray(img.dataobj).astype(np.int64)
    four = to_four(raw, img.header.get_zooms()[:3])
    for k, n in NAMES.items():
        lab, m = ndimage.label(four == k, structure=np.ones((3, 3, 3)))
        if m < 2:
            continue
        sizes = np.bincount(lab.ravel())[1:]
        small = np.argsort(sizes)[:-1] + 1
        src = {ICX[int(v)]: int(cnt) for v, cnt in zip(*np.unique(raw[np.isin(lab, small)], return_counts=True))}
        big = {ICX[int(v)] for v in np.unique(raw[lab == (np.argmax(sizes) + 1)])}
        print(c, n, 'sizes', sorted(sizes.tolist(), reverse=True), 'smaller piece is', src, '| main piece has', sorted(big))
