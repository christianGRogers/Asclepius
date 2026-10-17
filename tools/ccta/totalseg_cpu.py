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
import json, os, shutil, signal, subprocess, sys, tempfile, time
import numpy as np, nibabel as nib
from scipy import ndimage
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ccta_ingest

INPUTS, WORK = sys.argv[1], sys.argv[2]
N_CHECK = int(sys.argv[sys.argv.index('--check') + 1]) if '--check' in sys.argv else 5
TS = ['TotalSegmentator', '-ta', 'coronary_arteries', '--ml', '-d', 'cpu', '-nr', '4', '-ns', '4', '-q']
# Retry after a failure (in practice an out-of-memory kill on the 0.5 mm, 832x832x576 CCA200-HF volumes):
# one worker each and TotalSegmentator's three-chunk split, slower but within the container's 16 GB.
TS_LOWMEM = ['TotalSegmentator', '-ta', 'coronary_arteries', '--ml', '-d', 'cpu', '-nr', '1', '-ns', '1',
             '--force_split', '-q']
# Volumes larger than this (the 832x832x576, 0.5 mm CCA200-HF scans: ~13 GB even with --force_split, over the
# container's 16 GB with the batch itself) are segmented on a LOWRES_MM copy and the mask mapped back.
LARGE_VOXELS = 200e6
LOWRES_MM = 0.8
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
    for attempt in range(4):              # Girder sometimes cuts a large download short (IncompleteRead)
        try:
            open(src, 'wb').write(p.req('GET', f'item/{item_id}/download', raw=True))
            break
        except Exception:  # noqa: BLE001
            if attempt == 3:
                raise
            time.sleep(10 * (attempt + 1))
    t0 = time.time()
    orig = nib.load(src)
    run_src = src
    if np.prod(orig.shape[:3]) > LARGE_VOXELS:
        run_src = downsample(orig, os.path.join(tmp, 'ct_lo.nii.gz'))
    err = ''
    for cmd in (TS, TS_LOWMEM):
        code, err = run_ts(cmd + ['-i', run_src, '-o', out], tmp)
        if code == 0 and os.path.exists(out):
            break
        log(f'  TotalSegmentator exit {code}; ' + ('retrying with one worker and --force_split' if cmd is TS else 'giving up'))
    else:
        raise RuntimeError(err)
    im = nib.load(out)
    m = (np.asarray(im.dataobj) > 0).astype(np.uint8)
    if run_src != src:                    # back onto the CT's own grid, nearest neighbour
        m = upsample_mask(m, orig.shape[:3])
        im = orig
    hdr = im.header.copy(); hdr.set_data_dtype(np.uint8)
    hdr.set_slope_inter(1, 0)
    nib.save(nib.Nifti1Image(m, im.affine, hdr), out)
    return out, m, float(np.prod(im.header.get_zooms()[:3])), time.time() - t0


def downsample(img, path):
    """A copy at LOWRES_MM (never finer than the original), affine adjusted so the copy covers the same space."""
    zooms = np.array(img.header.get_zooms()[:3], float)
    factor = np.minimum(zooms / LOWRES_MM, 1.0)
    data = ndimage.zoom(np.asarray(img.dataobj, dtype=np.float32), factor, order=1)
    scale = np.array(img.shape[:3], float) / np.array(data.shape, float)    # original voxels per new voxel
    aff = img.affine.copy()
    aff[:3, :3] = img.affine[:3, :3] * scale
    aff[:3, 3] = img.affine[:3, :3] @ (0.5 * scale - 0.5) + img.affine[:3, 3]
    nib.save(nib.Nifti1Image(np.round(data).astype(np.int16), aff), path)
    return path


def upsample_mask(m, shape):
    up = ndimage.zoom(m, np.array(shape, float) / np.array(m.shape, float), order=0)
    out = np.zeros(shape, np.uint8)
    sl = tuple(slice(0, min(a, b)) for a, b in zip(shape, up.shape))
    out[sl] = up[sl]
    return out


def run_ts(cmd, tmp):
    """Run TotalSegmentator in its own process group, output to a file (not a pipe), and kill the whole group
    afterwards. An OOM-killed TotalSegmentator leaves joblib/loky workers behind; with pipes they held the
    output open and the batch waited forever (2026-10-17)."""
    logpath = os.path.join(tmp, 'ts.log')
    with open(logpath, 'w') as fh:
        proc = subprocess.Popen(cmd, stdout=fh, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
        try:
            code = proc.wait(timeout=3 * 3600)
        except subprocess.TimeoutExpired:
            code = 'timeout'
        finally:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except OSError:
                pass
            proc.wait()
    return code, open(logpath, errors='replace').read().strip()[-400:]


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
big = {i['name'] for i in todo if i['dataset'] == 'CCA200-HF'}   # 832x832x576 at 0.5 mm: last, so they cannot hold up the rest
todo = [i for i in todo if i['name'] not in big] + [i for i in todo if i['name'] in big]
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
