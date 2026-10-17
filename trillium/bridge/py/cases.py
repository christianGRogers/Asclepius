"""Find the case data and map it to tournament case ids (ImageCAS id n  ->  c{n-1:04d}).

Accepted layouts (README contract):
  imagecas : <dir>/<n>.img.nii.gz + <dir>/<n>.label.nii.gz         (ImageCAS release; may sit in sub-folders)
  girder   : <dir>/<case>/ct.nii.gz + <dir>/<case>/coronary_arteries.nii.gz
             (<case> = c0042, or an ImageCAS-style name containing the number n, e.g. imagecas_0043 / 43)
usage: python cases.py [CASES_DIR]   -> prints layout, counts, writes nothing
"""
import os
import re
import sys


def find_cases_dir(start):
    if os.environ.get('CASES'):
        return os.path.abspath(os.environ['CASES']), 'env CASES'
    d = os.path.abspath(start)
    seen = []
    while True:
        cand = os.path.join(d, 'cases')
        seen.append(cand)
        if os.path.isdir(cand):
            return cand, 'walked up from ' + start
        parent = os.path.dirname(d)
        if parent == d:
            raise SystemExit('ERROR: no cases/ directory found walking up from %s; looked at:\n  %s\n'
                             'Set CASES=/path/to/cases to override.' % (start, '\n  '.join(seen)))
        d = parent


def _case_from_name(name):
    m = re.fullmatch(r'c(\d{4})', name)
    if m:
        return name
    nums = re.findall(r'\d+', name)
    if nums:
        return 'c%04d' % (int(nums[-1]) - 1)
    return None


def scan(cases_dir):
    """returns (layout, {case: (ct_path, mask_path)}, notes)"""
    imagecas, girder, notes = {}, {}, []
    for root, dirs, files in os.walk(cases_dir, followlinks=True):
        fs = set(files)
        for f in files:
            m = re.fullmatch(r'(\d+)\.img\.nii(\.gz)?', f)
            if m:
                lab = [x for x in (f'{m.group(1)}.label.nii.gz', f'{m.group(1)}.label.nii') if x in fs]
                if lab:
                    imagecas['c%04d' % (int(m.group(1)) - 1)] = (os.path.join(root, f), os.path.join(root, lab[0]))
                else:
                    notes.append(f'image without label: {os.path.join(root, f)}')
        if 'ct.nii.gz' in fs and 'coronary_arteries.nii.gz' in fs:
            c = _case_from_name(os.path.basename(root))
            if c:
                girder[c] = (os.path.join(root, 'ct.nii.gz'), os.path.join(root, 'coronary_arteries.nii.gz'))
            else:
                notes.append(f'girder-like folder with no case number: {root}')
        elif 'ct.nii.gz' in fs:
            seg = os.path.join(root, 'segmentations', 'coronary_arteries.nii.gz')
            if os.path.exists(seg):
                c = _case_from_name(os.path.basename(root))
                if c:
                    girder[c] = (os.path.join(root, 'ct.nii.gz'), seg)
    if not imagecas and not girder:
        listing = sorted(os.listdir(cases_dir))[:20]
        raise SystemExit('ERROR: no recognised case layout under %s.\nFirst entries: %s\n'
                         'Expected <n>.img.nii.gz + <n>.label.nii.gz, or <case>/ct.nii.gz + <case>/coronary_arteries.nii.gz'
                         % (cases_dir, listing))
    if len(imagecas) >= len(girder):
        return 'imagecas', imagecas, notes
    return 'girder', girder, notes


if __name__ == '__main__':
    d = sys.argv[1] if len(sys.argv) > 1 else find_cases_dir(os.getcwd())[0]
    layout, m, notes = scan(d)
    ks = sorted(m)
    print(f'layout={layout} cases={len(m)} first={ks[:3]} last={ks[-3:]}')
    for n in notes[:10]:
        print('note:', n)
