"""TotalSegmentator `coronary_arteries` seed masks for the SegQueue volumes, on CPU, straight into Girder
(project lead, 2026-10-15: the annotators need something to work on before the Trillium jobs run).

For each volume of trillium/totalseg/inputs.json, in its priority order (QC annotatable, then limited, then the
three sets whose header spacing is suspect): download the CT, run TotalSegmentator 2.18.0 `coronary_arteries`
(binary; crops to the heart with the 6 mm `total` model first), keep the mask as uint8 0/1 in the CT's own grid,
upload it to SegQueue/seeds-totalseg/<CT name without .nii.gz>__totalseg-coronary.nii.gz with metadata, delete
the local files. SegQueue/cases stays CT-only (D22). The live SegQueue is not touched.

Before the batch: N_CHECK ImageCAS-X test cases (CT from the ImageCAS-X collection) are segmented and scored
against the ImageCAS-X labels (> 0) as binary Dice / precision / recall; logged, not uploaded.

Resumable: volumes whose mask is already in the seeds folder are skipped; one JSON line per volume goes to
<work>/log.jsonl. One volume at a time (the container has 4 cores; TotalSegmentator uses them all).
Usage: GIRDER_TOKEN_FILE=... TOTALSEG_HOME_DIR=... totalseg_cpu.py <inputs.json> <work dir> [--check N]"""
import json, os, shutil, subprocess, sys, tempfile, time
import numpy as np, nibabel as nib
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest

INPUTS, WORK = sys.argv[1], sys.argv[2]
N_CHECK = int(sys.argv[sys.argv.index('--check') + 1]) if '--check' in sys.argv else 5
TS = ['TotalSegmentator', '-ta', 'coronary_arteries', '--ml', '-d', 'cpu', '-nr', '4', '-ns', '4', '-q']
os.makedirs(WORK, exist_ok=True)
p = ccta_ingest.Pool()
log = lambda *a: print(time.strftime('%H:%M:%S'), *a, flush=True)


def coll(name):
    return [c for c in p.req('GET', 'collection', {'text': name, 'limit': 50}) if c['name'] == name][0]


def subfolder(parent, ptype, name, desc=''):
    for f in p.req('GET', 'folder', {'parentType': ptype, 'parentId': parent, 'name': name}):
        return f
    return p.req('POST', 'folder', {'parentType': ptype, 'parentId': parent, 'name': name, 'description': desc})


def items(fid):
    out, off = [], 0
    while True:
        page = p.req('GET', 'item', {'folderId': fid, 'limit': 1000, 'offset': off})
        out += page
        if len(page) < 1000:
            return out
        off += 1000


def segment(item_id, tmp):
    src, out = os.path.join(tmp, 'ct.nii.gz'), os.path.join(tmp, 'seg.nii.gz')
    open(src, 'wb').write(p.req('GET', f'item/{item_id}/download', raw=True))
    t0 = time.time()
    r = subprocess.run(TS + ['-i', src, '-o', out], capture_output=True, text=True, timeout=3 * 3600)
    if r.returncode != 0 or not os.path.exists(out):
        raise RuntimeError(((r.stderr or '') + (r.stdout or '')).strip()[-400:])
    im = nib.load(out)
    m = (np.asarray(im.dataobj) > 0).astype(np.uint8)
    hdr = im.header.copy(); hdr.set_data_dtype(np.uint8)
    nib.save(nib.Nifti1Image(m, im.affine, hdr), out)
    return out, m, float(np.prod(im.header.get_zooms()[:3])), time.time() - t0


def stats(m, vox):
    lab, n = ndimage.label(m, structure=np.ones((3, 3, 3)))
    sizes = np.sort(np.bincount(lab.ravel())[1:])[::-1] if n else np.zeros(0)
    ml = float(m.sum()) * vox / 1000
    two = float(sizes[:2].sum()) / max(float(m.sum()), 1)
    return dict(volume_ml=round(ml, 3), components=int(n), largest_two_fraction=round(two, 3),
                flag='empty' if ml < 0.2 else 'fragmented' if two < 0.7 else '')


sq = coll('SegQueue')
seeds = subfolder(sq['_id'], 'collection', 'seeds-totalseg',
                  'TotalSegmentator 2.18.0 coronary_arteries (binary) seed masks for the volumes in cases/, one per '
                  'CT, same grid, named <CT name>__totalseg-coronary.nii.gz. Automatic, uncorrected: a starting point '
                  'for annotation, not a label. Licence: TotalSegmentator academic (non-commercial) licence.')

# ---- 1. check on ImageCAS-X test cases ------------------------------------------------------------------------
check_f = os.path.join(WORK, 'check.json')
check = json.load(open(check_f)) if os.path.exists(check_f) else {}
if N_CHECK and len(check) < N_CHECK:
    icx = coll('ImageCAS-X')
    cases = {it['name']: it for it in items(subfolder(icx['_id'], 'collection', 'cases')['_id'])}
    lab_items = {}
    for sub in p.req('GET', 'folder', {'parentType': 'folder', 'parentId': subfolder(icx['_id'], 'collection', 'labels')['_id']}):
        for it in items(sub['_id']):
            if it['name'].endswith('__labels14.nii.gz'):
                lab_items[it['name']] = it
    test = sorted(n for n, it in cases.items() if (it.get('meta') or {}).get('icx_split') == 'test'
                  and not n.endswith('__mask.nii.gz'))
    for name in test[:N_CHECK]:
        if name in check:
            continue
        lab = lab_items.get(name.replace('ImageCAS__', 'ImageCAS-X__').replace('.nii.gz', '__labels14.nii.gz'))
        if not lab:
            continue
        tmp = tempfile.mkdtemp(dir=WORK)
        try:
            out, m, vox, secs = segment(cases[name]['_id'], tmp)
            lp = os.path.join(tmp, 'lab.nii.gz')
            open(lp, 'wb').write(p.req('GET', f"item/{lab['_id']}/download", raw=True))
            ref = np.asarray(nib.load(lp).dataobj) > 0
            pr = m > 0
            tp = float((pr & ref).sum())
            check[name] = dict(dice=round(2 * tp / max(pr.sum() + ref.sum(), 1), 4),
                               precision=round(tp / max(pr.sum(), 1), 4), recall=round(tp / max(ref.sum(), 1), 4),
                               seconds=round(secs))
            log('check', name, check[name])
            json.dump(check, open(check_f, 'w'), indent=1)
        except Exception as e:  # noqa: BLE001
            log('check FAILED', name, repr(e)[:300])
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    if check:
        log('check mean', {k: round(float(np.mean([v[k] for v in check.values()])), 4)
                           for k in ('dice', 'precision', 'recall')})

# ---- 2. the batch -------------------------------------------------------------------------------------------
todo = json.load(open(INPUTS))
have = {it['name'] for it in items(seeds['_id'])}
log(f'batch: {len(todo)} volumes, {sum(1 for i in todo if i["name"][:-7] + "__totalseg-coronary.nii.gz" in have)} already done')
logf = open(os.path.join(WORK, 'log.jsonl'), 'a')
for k, it in enumerate(todo, 1):
    name = it['name'][:-7] + '__totalseg-coronary.nii.gz'
    if name in have:
        continue
    tmp = tempfile.mkdtemp(dir=WORK)
    rec = dict(name=it['name'], priority=it['priority'], dataset=it['dataset'])
    try:
        out, m, vox, secs = segment(it['item_id'], tmp)
        st = stats(m, vox)
        meta = dict(st, role='seed mask (automatic, uncorrected)', ct_item=it['item_id'], ct_name=it['name'],
                    method='TotalSegmentator 2.18.0 coronary_arteries, CPU, binarised', source=it['dataset'],
                    qc_annotatable=it['annotatable'], spacing_suspect=it['spacing_suspect'],
                    created=time.strftime('%Y-%m-%d'))
        p.upload(seeds['_id'], out, name, meta)
        have.add(name)
        rec.update(st, seconds=round(secs))
        log(f'{k}/{len(todo)} {it["name"]}: {st["volume_ml"]} ml, {st["components"]} parts {st["flag"]} ({secs:.0f} s)')
    except Exception as e:  # noqa: BLE001 - one bad volume must not stop the batch
        rec['error'] = repr(e)[-400:]
        log(f'{k}/{len(todo)} {it["name"]}: FAILED {rec["error"][:200]}')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    logf.write(json.dumps(rec) + '\n'); logf.flush()
log('batch finished')
