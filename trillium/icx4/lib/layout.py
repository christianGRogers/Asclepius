"""Find the cases/ directory and map its files to tournament case ids (c0000..c0999).

Accepted layouts (README contract):
  imagecas  cases/<n>.img.nii.gz + cases/<n>.label.nii.gz      (ImageCAS release; id n -> c{n-1:04d})
  girder    cases/<case>/ct.nii.gz + cases/<case>/coronary_arteries.nii.gz
            <case> = c0000 style (taken as is) or any name ending in digits (ImageCAS id -> c{n-1:04d})
  girder-ct cases/<case>/ct.nii.gz only (trillium/fetch_cases.py without --masks; icx4 never reads the masks):
            'mask' is None
A directory holding more than one of these (e.g. some case folders with a mask and some without) is refused.
Prints what it found and fails loudly if nothing matches. A case folder without a finished ct.nii.gz (missing, or
still ct.nii.gz.part from an interrupted fetch) is listed as incomplete (#82), never silently dropped.

    python layout.py <start> [layout.json]          # find cases/, print the layout, write layout.json
    python layout.py check <layout.json> <icx dir>  # refuse unless all 1000 cases and every ImageCAS-X
                                                    # train/val/test case are present (#82)
ICX4_ALLOW_PARTIAL=1 turns the check's refusal into a warning, for a deliberate partial run only.
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

N_CASES = 1000
FETCH_HINT = 'python3 <repo>/trillium/fetch_cases.py {d}   (resumable: re-run until it says 1000 of 1000 CTs complete)'


def incomplete(cases_dir):
    """{cid: 'partial' | 'missing'} for case folders without a finished ct.nii.gz (an interrupted fetch)."""
    out = {}
    for f in sorted(os.listdir(cases_dir)):
        p = os.path.join(cases_dir, f)
        cid = _cid_from_name(f)
        if cid and os.path.isdir(p) and not os.path.exists(os.path.join(p, 'ct.nii.gz')):
            out[cid] = 'partial' if os.path.exists(os.path.join(p, 'ct.nii.gz.part')) else 'missing'
    return out


def check(layout_json, icx, allow_partial=False):
    """0 if all 1000 cases and every ImageCAS-X train/val/test case have a CT; else 1 (or 0 with allow_partial)."""
    L = json.load(open(layout_json))
    cases, d = L['cases'], L['cases_dir']
    gone = sorted(c for c, e in cases.items() if not os.path.exists(e['ct']))   # removed since the scan
    have = set(cases) - set(gone)
    problems = []
    every = ['c%04d' % i for i in range(N_CASES)]
    miss = [c for c in every if c not in have]
    print(f'[icx4] cases with a CT: {len(have)} of {N_CASES}')
    if miss:
        problems.append(f'{len(miss)} of {N_CASES} cases have no CT, e.g. {miss[:10]}')
    for s in ('train', 'val', 'test'):
        ids = ['c%04d' % (int(x) - 1) for x in open(os.path.join(icx, f'{s}.txt')).read().split()]
        absent = [c for c in ids if c not in have]
        print(f'[icx4] ImageCAS-X {s}: {len(ids)} listed, {len(ids) - len(absent)} present in cases/')
        if absent:
            problems.append(f'ImageCAS-X {s}: {len(absent)} of {len(ids)} cases missing, e.g. {absent[:10]}')
    inc = L.get('incomplete', {})
    if inc:
        problems.append(f'{len(inc)} case folder(s) without a finished ct.nii.gz '
                        f'({sum(v == "partial" for v in inc.values())} still .part), e.g. {sorted(inc)[:10]}')
    if not problems:
        print('[icx4] cases complete: all 1000 CTs, every ImageCAS-X train/val/test case present')
        return 0
    for p in problems:
        print(f'[icx4] MISSING: {p}')
    print('[icx4] resume the fetch: ' + FETCH_HINT.format(d=d))
    if allow_partial:
        print('[icx4] WARNING: ICX4_ALLOW_PARTIAL=1: continuing with an incomplete cases/ (a deliberate partial run)')
        return 0
    print('[icx4] REFUSING: cases/ is incomplete (set ICX4_ALLOW_PARTIAL=1 only for a deliberate partial run)')
    return 1


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
    gird, ctonly = {}, {}
    for f in ent:
        p = os.path.join(cases_dir, f)
        ct, mask = os.path.join(p, 'ct.nii.gz'), os.path.join(p, 'coronary_arteries.nii.gz')
        if not (os.path.isdir(p) and os.path.exists(ct)):
            continue
        cid = _cid_from_name(f)
        if not cid:
            continue
        if cid in gird or cid in ctonly:
            sys.exit(f'Two case folders in {cases_dir} map to {cid} (one is {f}); refusing to guess.')
        if os.path.exists(mask):
            gird[cid] = {'ct': ct, 'mask': mask}
        else:
            ctonly[cid] = {'ct': ct, 'mask': None}
    found = [(n, d) for n, d in (('imagecas', imgs), ('girder', gird), ('girder-ct', ctonly)) if d]
    if len(found) > 1:
        sys.exit(f'More than one layout in {cases_dir} (' + ', '.join(f'{len(d)} {n}' for n, d in found)
                 + '); refusing to guess. (girder-ct = case folders with ct.nii.gz but no coronary_arteries.nii.gz)')
    if found:
        return found[0]
    sample = ent[:15]
    sys.exit(f'Unrecognised layout in {cases_dir}. Expected <n>.img.nii.gz + <n>.label.nii.gz, or '
             f'<case>/ct.nii.gz [+ <case>/coronary_arteries.nii.gz]. First entries: {sample}')

if __name__ == '__main__':
    if sys.argv[1:2] == ['check']:
        sys.exit(check(sys.argv[2], sys.argv[3], os.environ.get('ICX4_ALLOW_PARTIAL') == '1'))
    d = find_cases_dir(sys.argv[1] if len(sys.argv) > 1 else os.getcwd(), os.environ.get('CASES'))
    layout, cases = scan(d)
    inc = incomplete(d) if layout != 'imagecas' else {}
    out = sys.argv[2] if len(sys.argv) > 2 else None
    print(f'cases dir: {d}\nlayout: {layout}\ncases found: {len(cases)} (first {sorted(cases)[:3]}, last {sorted(cases)[-3:]})')
    if inc:
        print(f'incomplete: {len(inc)} case folder(s) without a finished ct.nii.gz '
              f'({sum(v == "partial" for v in inc.values())} still .part), e.g. {sorted(inc)[:5]}')
    if out:
        json.dump({'cases_dir': d, 'layout': layout, 'cases': cases, 'incomplete': inc}, open(out, 'w'))
