"""Reorganise Girder (project lead, 2026-10-14):

1. New private collection `ImageCAS-X`: the 800 ImageCAS cases that ImageCAS-X already labels (their CT and old
   ImageCAS mask, moved out of SegQueue/cases) in `cases/`, and the ImageCAS-X labels/centrelines/split lists
   (the folder SegQueue/imagecas-x, moved whole) as `labels/`.
2. SegQueue/cases keeps the 200 ImageCAS cases ImageCAS-X does not cover, and gets a copy of every CCTA-Pool CT
   volume (CT only; one item per volume; several volumes of one patient are separate items). CCTA-Pool stays
   intact as the archive (labels, original non-HU files, full metadata).
3. Every volume gets a structured, human-readable name:  <Source>__<Case>[__<Part>].<ext>
     ImageCAS__0001.nii.gz, ImageCAS__0001__mask.nii.gz, ImageCAS-X__0001__labels14.nii.gz,
     ImageCAS-X__0001__centerline-left.vtk, ImageCHD__1001.nii.gz, Mendeley-SDN-cy54ttk3fj__P01_diast.nii.gz
   (Source = the CCTA-Pool dataset folder name; ImageCAS ids are the 1-based ImageCAS numbers).
The live SegQueue's case records are not touched: it loads files by id (force=True), not by folder or name.
Idempotent. Usage: GIRDER_TOKEN_FILE=... reorganise_girder.py <ImageCAS-X filelist dir> <cases.json> [--apply]"""
import json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest

FILELIST, CASES_JSON = sys.argv[1], sys.argv[2]
APPLY = '--apply' in sys.argv
p = ccta_ingest.Pool()
log = lambda *a: print(*a, flush=True)


def coll(name, desc=''):
    for c in p.req('GET', 'collection', {'text': name, 'limit': 50}):
        if c['name'] == name:
            return c
    if not APPLY:
        return {'_id': f'dry-{name}', 'name': name}
    return p.req('POST', 'collection', {'name': name, 'public': 'false', 'description': desc})


def subfolder(parent, ptype, name, desc=''):
    if not APPLY and str(parent).startswith('dry'):
        return {'_id': f'dry-{name}'}
    for f in p.req('GET', 'folder', {'parentType': ptype, 'parentId': parent, 'name': name}):
        return f
    if not APPLY:
        return {'_id': f'dry-{name}'}
    return p.req('POST', 'folder', {'parentType': ptype, 'parentId': parent, 'name': name, 'description': desc})


def items(fid):
    out, off = [], 0
    while True:
        page = p.req('GET', 'item', {'folderId': fid, 'limit': 1000, 'offset': off})
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def rename(item, name, meta=None):
    have = item.get('meta') or {}
    if item['name'] == name and (not meta or all(have.get(k) == v for k, v in meta.items())):
        return                                   # already done (re-runs skip finished items)
    if APPLY:
        p.req('PUT', f"item/{item['_id']}", {'name': name})
        for f in p.req('GET', f"item/{item['_id']}/files"):
            if f['name'] != name:
                p.req('PUT', f"file/{f['_id']}", {'name': name})
        if meta:
            p.req('PUT', f"item/{item['_id']}/metadata", body=json.dumps(meta).encode(), ctype='application/json')


def move(item, folder_id, name, meta=None):
    if APPLY and item.get('folderId') != folder_id:
        p.req('PUT', f"item/{item['_id']}", {'folderId': folder_id})
    rename(item, name, meta)


def safe(s):
    return re.sub(r'[^A-Za-z0-9._-]+', '-', str(s)).strip('-')


# ------------------------------------------------------------------ the ImageCAS split
split = {}
for s in ('train', 'val', 'test', 'exclude'):
    for x in open(os.path.join(FILELIST, f'{s}.txt')).read().split():
        split[int(x)] = s
labelled = {n for n, s in split.items() if s != 'exclude'}
assert len(labelled) == 800, len(labelled)
cases = {c['case']: c for c in json.load(open(CASES_JSON))}          # cNNNN -> ct_id / mask_id (item ids)

sq = coll('SegQueue')
sq_cases = subfolder(sq['_id'], 'collection', 'cases')
icx = coll('ImageCAS-X', 'The 800 ImageCAS cases that ImageCAS-X (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) '
                          'already labels with 14 coronary segments, moved out of SegQueue because they need no '
                          'annotation. cases/: CT and the old ImageCAS mask; labels/: ImageCAS-X segmentations, '
                          'centrelines and split lists.')
icx_cases = subfolder(icx['_id'], 'collection', 'cases', 'ImageCAS CT + old ImageCAS mask for the 800 labelled cases')

# ------------------------------------------------------------------ 1+3. ImageCAS cases
moved = kept = 0
for cid, c in sorted(cases.items()):
    n = int(cid[1:]) + 1
    base = f'ImageCAS__{n:04d}'
    meta = {'source': 'ImageCAS', 'imagecas_id': n, 'segqueue_case': f'imagecas_{n:04d}', 'tournament_case': cid,
            'icx_split': split.get(n, 'unlisted')}
    ct = p.req('GET', f"item/{c['ct_id']}"); mk = p.req('GET', f"item/{c['mask_id']}")
    if n in labelled:
        move(ct, icx_cases['_id'], f'{base}.nii.gz', dict(meta, role='CT'))
        move(mk, icx_cases['_id'], f'{base}__mask.nii.gz', dict(meta, role='old ImageCAS binary mask'))
        moved += 1
    else:
        rename(ct, f'{base}.nii.gz', dict(meta, role='CT'))
        rename(mk, f'{base}__mask.nii.gz', dict(meta, role='old ImageCAS binary mask (live SegQueue seed)'))
        kept += 1
log(f'ImageCAS: {moved} labelled cases -> ImageCAS-X/cases, {kept} stay in SegQueue/cases (renamed)')

# ------------------------------------------------------------------ 1. ImageCAS-X labels folder
old = [f for f in p.req('GET', 'folder', {'parentType': 'collection', 'parentId': sq['_id']})
       if f['name'] == 'imagecas-x']
lab = None
if old:
    lab = old[0]
    if APPLY:
        p.req('PUT', f"folder/{lab['_id']}", {'parentType': 'collection', 'parentId': icx['_id'], 'name': 'labels'})
    log('moved SegQueue/imagecas-x -> ImageCAS-X/labels')
else:
    lab = subfolder(icx['_id'], 'collection', 'labels')
if APPLY or not str(lab['_id']).startswith('dry'):
    n_ren = 0
    for sub in p.req('GET', 'folder', {'parentType': 'folder', 'parentId': lab['_id']}):
        for it in items(sub['_id']):
            m = re.fullmatch(r'(\d+)\.coronary\.nii\.gz', it['name'])
            if m:
                rename(it, f'ImageCAS-X__{int(m.group(1)):04d}__labels14.nii.gz'); n_ren += 1; continue
            m = re.fullmatch(r'(\d+)\.coronary_(left|right)_centerline\.vtk', it['name'])
            if m:
                rename(it, f'ImageCAS-X__{int(m.group(1)):04d}__centerline-{m.group(2)}.vtk'); n_ren += 1
    log(f'ImageCAS-X labels/centrelines renamed: {n_ren}')

# ------------------------------------------------------------------ 2+3. CCTA-Pool CT copies into SegQueue/cases
existing = {it['name'] for it in items(sq_cases['_id'])}
copied = skipped = 0
for ds in p.req('GET', 'folder', {'parentType': 'collection', 'parentId': p.coll['_id'], 'limit': 0}):
    if ds['name'].startswith('_'):
        continue
    for case in p.req('GET', 'folder', {'parentType': 'folder', 'parentId': ds['_id'], 'limit': 0}):
        ct = [it for it in p.req('GET', 'item', {'folderId': case['_id']}) if it['name'] == 'ct.nii.gz']
        if not ct:
            continue
        name = f"{safe(ds['name'])}__{safe(case['name'])}.nii.gz"
        if name in existing:
            skipped += 1; continue
        if APPLY:
            new = p.req('POST', f"item/{ct[0]['_id']}/copy", {'folderId': sq_cases['_id'], 'name': name})
            for f in p.req('GET', f"item/{new['_id']}/files"):
                p.req('PUT', f"file/{f['_id']}", {'name': name})
            meta = dict(ct[0].get('meta') or {}, source=ds['name'], ccta_pool_item=ct[0]['_id'], role='CT')
            p.req('PUT', f"item/{new['_id']}/metadata", body=json.dumps(meta).encode(), ctype='application/json')
        existing.add(name); copied += 1
        if copied % 100 == 0:
            log(f'  copied {copied}')
log(f'CCTA-Pool -> SegQueue/cases: {copied} copied, {skipped} already there; apply={APPLY}')
