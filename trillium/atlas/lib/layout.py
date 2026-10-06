"""Find the cases/ directory and map its files to tournament case ids (c0000..c0999).

Accepted layouts (README contract):
  imagecas  cases/<n>.img.nii.gz + cases/<n>.label.nii.gz      (ImageCAS release; id n -> c{n-1:04d})
  girder    cases/<case>/ct.nii.gz + cases/<case>/coronary_arteries.nii.gz
            <case> = c0000 style (taken as is) or any name ending in digits (ImageCAS id -> c{n-1:04d})
Prints what it found and fails loudly if nothing matches.
"""
import os, re, sys, json

def find_cases_dir(start, override=None):
    if override:
        if not os.path.isdir(override):
            sys.exit(f'CASES={override} is not a directory')
        return os.path.abspath(override)
    d = os.path.abspath(start); tried = []
    while True:
        cand = os.path.join(d, 'cases')
        tried.append(cand)
        if os.path.isdir(cand):
            return cand
        parent = os.path.dirname(d)
        if parent == d:
            sys.exit('No cases/ directory found walking up from ' + start + '\nTried:\n  ' + '\n  '.join(tried)
                     + '\nPut the case data in <root>/cases or set CASES=/path.')
        d = parent

def _cid_from_name(name):
    m = re.fullmatch(r'c(\d{4})', name)
    if m:
        return name
    m = re.search(r'(\d+)$', name)
    if m and 1 <= int(m.group(1)) <= 1000:
        return 'c%04d' % (int(m.group(1)) - 1)
    return None

def scan(cases_dir):
    """Return (layout, {cid: {'ct': path, 'mask': path}})."""
    ent = sorted(os.listdir(cases_dir))
    imgs = {}
    for f in ent:
        m = re.fullmatch(r'(\d+)\.img\.nii\.gz', f)
        if m:
            lab = os.path.join(cases_dir, f'{m.group(1)}.label.nii.gz')
            if os.path.exists(lab):
                imgs['c%04d' % (int(m.group(1)) - 1)] = {'ct': os.path.join(cases_dir, f), 'mask': lab}
    gird = {}
    for f in ent:
        p = os.path.join(cases_dir, f)
        if os.path.isdir(p) and os.path.exists(os.path.join(p, 'ct.nii.gz')) and \
                os.path.exists(os.path.join(p, 'coronary_arteries.nii.gz')):
            cid = _cid_from_name(f)
            if cid:
                gird[cid] = {'ct': os.path.join(p, 'ct.nii.gz'), 'mask': os.path.join(p, 'coronary_arteries.nii.gz')}
    if imgs and gird:
        sys.exit(f'Both layouts present in {cases_dir} ({len(imgs)} imagecas, {len(gird)} girder); refusing to guess.')
    if imgs:
        return 'imagecas', imgs
    if gird:
        return 'girder', gird
    sample = ent[:15]
    sys.exit(f'Unrecognised layout in {cases_dir}. Expected <n>.img.nii.gz + <n>.label.nii.gz, or '
             f'<case>/ct.nii.gz + <case>/coronary_arteries.nii.gz. First entries: {sample}')

if __name__ == '__main__':
    d = find_cases_dir(sys.argv[1] if len(sys.argv) > 1 else os.getcwd(), os.environ.get('CASES'))
    layout, cases = scan(d)
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print(f'cases dir: {d}\nlayout: {layout}\ncases found: {len(cases)} (first {sorted(cases)[:3]}, last {sorted(cases)[-3:]})')
    if out:
        json.dump({'cases_dir': d, 'layout': layout, 'cases': cases}, open(out, 'w'))
