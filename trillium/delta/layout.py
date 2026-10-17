"""Case-layout detection for Delta's Trillium experiment (no side effects; usable standalone:
`python layout.py <cases_dir>` prints the layout and the number of cases)."""
import glob
import os
import re
import sys


def find_cases(root):
    """Return (layout, {case_id: (ct, mask)}). Accepts
    - ImageCAS release: <n>.img.nii.gz + <n>.label.nii.gz anywhere under root (n = ImageCAS id)
    - Girder export:    <case>/ct.nii.gz + <case>/coronary_arteries.nii.gz
                        (or <case>/segmentations/coronary_arteries.nii.gz); <case> = c0000.. or n
    Tournament id: ImageCAS id n -> c{n-1:04d}."""
    out = {}
    imgs = glob.glob(os.path.join(root, '**', '*.img.nii.gz'), recursive=True)
    if imgs:
        for p in imgs:
            m = re.match(r'(\d+)\.img\.nii\.gz$', os.path.basename(p))
            lab = p.replace('.img.nii.gz', '.label.nii.gz')
            if m and os.path.exists(lab):
                out[f'c{int(m.group(1)) - 1:04d}'] = (p, lab)
        if out:
            return 'imagecas-release', out
    for ct in glob.glob(os.path.join(root, '**', 'ct.nii.gz'), recursive=True):
        d = os.path.dirname(ct)
        name = os.path.basename(d)
        mask = None
        for cand in (os.path.join(d, 'coronary_arteries.nii.gz'),
                     os.path.join(d, 'segmentations', 'coronary_arteries.nii.gz')):
            if os.path.exists(cand):
                mask = cand
        if mask is None:
            continue
        if re.fullmatch(r'c\d{4}', name):
            out[name] = (ct, mask)
        elif re.fullmatch(r'\d+', name):
            out[f'c{int(name) - 1:04d}'] = (ct, mask)
    if out:
        return 'girder-export', out
    return None, {}


if __name__ == '__main__':
    layout, cases = find_cases(sys.argv[1])
    if not cases:
        print(f'LAYOUT NOT RECOGNISED under {sys.argv[1]}. Expected either <n>.img.nii.gz + <n>.label.nii.gz '
              '(ImageCAS release) or <case>/ct.nii.gz + <case>/coronary_arteries.nii.gz (Girder export).')
        print('Found at top level:', sorted(os.listdir(sys.argv[1]))[:20])
        sys.exit(2)
    ids = sorted(cases)
    print(f'layout={layout} cases={len(cases)} first={ids[0]} last={ids[-1]}')
