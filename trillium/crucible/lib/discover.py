"""Find cases/ and map it to tournament case ids (ImageCAS id n -> c{n-1:04d}).

Layouts accepted (README contract):
  imagecas : <id>.img.nii.gz + <id>.label.nii.gz (any depth <= 3 under cases/)
  girder   : <case>/ct.nii.gz + <case>/coronary_arteries.nii.gz (or <case>/segmentations/coronary_arteries.nii.gz),
             <case> = c0000..c0999
Usage: python discover.py <start_dir> <out_manifest.json>   (prints the layout; exit 2 if not recognised)
"""
import json, os, re, sys


def find_cases_dir(start):
    if os.environ.get('CASES'):
        return os.path.abspath(os.environ['CASES'])
    d = os.path.abspath(start)
    while True:
        if os.path.isdir(os.path.join(d, 'cases')):
            return os.path.join(d, 'cases')
        parent = os.path.dirname(d)
        if parent == d:
            return None
        d = parent


def scan(root):
    imgcas, girder = {}, {}
    for dirpath, dirnames, files in os.walk(root):
        depth = dirpath[len(root):].count(os.sep)
        if depth > 3:
            dirnames[:] = []; continue
        for f in files:
            m = re.fullmatch(r'(\d+)\.img\.nii\.gz', f)
            if m:
                lab = os.path.join(dirpath, f'{m.group(1)}.label.nii.gz')
                if os.path.exists(lab):
                    n = int(m.group(1)); imgcas[f'c{n - 1:04d}'] = {'ct': os.path.join(dirpath, f), 'mask': lab, 'imagecas_id': n}
        base = os.path.basename(dirpath)
        if re.fullmatch(r'c\d{4}', base) and 'ct.nii.gz' in files:
            for cand in ('coronary_arteries.nii.gz', os.path.join('segmentations', 'coronary_arteries.nii.gz')):
                if os.path.exists(os.path.join(dirpath, cand)):
                    girder[base] = {'ct': os.path.join(dirpath, 'ct.nii.gz'), 'mask': os.path.join(dirpath, cand),
                                    'imagecas_id': int(base[1:]) + 1}
                    break
    return imgcas, girder


def main(start, out):
    root = find_cases_dir(start)
    if root is None:
        print(f'ERROR: no cases/ directory found walking up from {os.path.abspath(start)} (set CASES=/path to override)')
        sys.exit(2)
    imgcas, girder = scan(root)
    if len(imgcas) >= len(girder) and imgcas:
        layout, cases = 'imagecas', imgcas
    elif girder:
        layout, cases = 'girder', girder
    else:
        top = sorted(os.listdir(root))[:20]
        print(f'ERROR: layout not recognised in {root}. First entries: {top}\n'
              'Expected <id>.img.nii.gz + <id>.label.nii.gz, or c0000/ct.nii.gz + c0000/coronary_arteries.nii.gz')
        sys.exit(2)
    json.dump({'root': root, 'layout': layout, 'cases': cases}, open(out, 'w'), indent=0)
    print(f'cases: {root}\nlayout detected: {layout} ({len(cases)} cases; imagecas-style {len(imgcas)}, girder-style {len(girder)})')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
