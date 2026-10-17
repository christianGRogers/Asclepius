#!/usr/bin/env python3
"""GPU job body: TotalSegmentator `coronary_arteries` (binary) on the inputs, after a 20-case check against
ImageCAS-X. Usage: run.py <W> <inputs.json>   (W = $SCRATCH/totalseg)

  1. check: 20 ImageCAS-X test cases already on $SCRATCH from icx14 (CT = $SCRATCH/icx14/predict_in,
     reference = ImageCAS-X 14-class labels > 0). Dice / precision / recall of the binary masks.
  2. batch: every volume in inputs.json in priority order (1 = QC annotatable, 2 = limited, 3 = header spacing
     suspect). Output <W>/out/<name>__totalseg-coronary.nii.gz (uint8, 0/1, in the input's own grid).
Resumable (finished outputs are skipped), several cases at once on the one GPU, stops before $TS_DEADLINE.
Each worker gets its own TOTALSEG_HOME_DIR (TotalSegmentator rewrites config.json on every run; the copies
have usage statistics off because compute nodes have no internet)."""
import concurrent.futures as cf, json, os, shutil, subprocess, sys, tempfile, threading, time
import numpy as np, nibabel as nib
from scipy import ndimage

W, INPUTS = sys.argv[1], sys.argv[2]
WORKERS = int(os.environ.get('TS_WORKERS', 3))
DEADLINE = float(os.environ.get('TS_DEADLINE', 0)) or None
ICX_W = os.path.join(os.path.dirname(W.rstrip('/')), 'icx14')
N_CHECK = 20
os.makedirs(f'{W}/out', exist_ok=True); os.makedirs(f'{W}/check', exist_ok=True); os.makedirs(f'{W}/results', exist_ok=True)

homes = []
cfg = json.load(open(os.path.expanduser('~/.totalsegmentator/config.json')))
cfg['send_usage_stats'] = False
for k in range(WORKERS):
    h = f'{W}/home/w{k}'; os.makedirs(h, exist_ok=True)
    json.dump(cfg, open(f'{h}/config.json', 'w'))
    homes.append(h)
free = list(range(WORKERS)); lock = threading.Lock()


def segment(src, dst):
    """Run TotalSegmentator on one volume; returns (seconds, error or None)."""
    with lock:
        k = free.pop()
    t0 = time.time()
    tmp = tempfile.mkdtemp(dir=f'{W}/home')
    try:
        env = dict(os.environ, TOTALSEG_HOME_DIR=homes[k],
                   TOTALSEG_WEIGHTS_PATH=os.path.expanduser('~/.totalsegmentator/nnunet/results'))
        out = os.path.join(tmp, 'seg.nii.gz')
        r = subprocess.run(['TotalSegmentator', '-i', src, '-o', out, '-ta', 'coronary_arteries', '--ml',
                            '-nr', '4', '-ns', '2', '-d', 'gpu', '-q'], env=env, capture_output=True, text=True,
                           timeout=1800)
        if r.returncode != 0 or not os.path.exists(out):
            return time.time() - t0, (r.stderr or r.stdout)[-600:]
        im = nib.load(out)
        m = (np.asarray(im.dataobj) > 0).astype(np.uint8)
        nib.save(nib.Nifti1Image(m, im.affine), dst + '.part.nii.gz')
        os.replace(dst + '.part.nii.gz', dst)
        return time.time() - t0, None
    except Exception as e:  # noqa: BLE001 - one bad volume must not stop the batch
        return time.time() - t0, repr(e)[-600:]
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
        with lock:
            free.append(k)


def stats(path):
    im = nib.load(path)
    m = np.asarray(im.dataobj) > 0
    vox = float(np.prod(im.header.get_zooms()[:3]))
    lab, n = ndimage.label(m, structure=np.ones((3, 3, 3)))
    sizes = np.bincount(lab.ravel())[1:] if n else np.zeros(0)
    ml = m.sum() * vox / 1000
    return dict(volume_ml=round(float(ml), 3), components=int(n),
                largest_two_fraction=round(float(np.sort(sizes)[-2:].sum() / max(m.sum(), 1)), 3),
                flag=('empty' if ml < 0.2 else 'fragmented' if n and np.sort(sizes)[-2:].sum() < 0.7 * m.sum() else ''))


def time_left(median_s):
    # a case started now needs about one median case time on its own worker
    return DEADLINE is None or time.time() + 1.5 * median_s + 300 < DEADLINE


def run_all(jobs, label):
    """jobs: list of (key, src, dst). Returns {key: record}."""
    rec, times = {}, [120.0]
    todo = [j for j in jobs if not os.path.exists(j[2])]
    print(f'[{label}] {len(jobs)} volumes, {len(todo)} to segment, {WORKERS} at a time', flush=True)
    with cf.ThreadPoolExecutor(WORKERS) as ex:
        pending = {}
        it = iter(todo)
        stop = False
        def submit():
            nonlocal stop
            if stop or not time_left(float(np.median(times[-20:]))):
                stop = True; return False
            j = next(it, None)
            if j is None:
                return False
            pending[ex.submit(segment, j[1], j[2])] = j
            return True
        for _ in range(WORKERS * 2):
            submit()
        done = 0
        while pending:
            f = next(cf.as_completed(list(pending)))
            j = pending.pop(f)
            s, err = f.result()
            times.append(s); done += 1
            rec[j[0]] = dict(seconds=round(s, 1), error=err)
            if err:
                print(f'[{label}] FAILED {j[0]}: {err.strip().splitlines()[-1] if err.strip() else err}', flush=True)
            if done % 25 == 0:
                print(f'[{label}]   {done}/{len(todo)}  median {np.median(times[-50:]):.0f} s/case', flush=True)
            submit()
    if stop:
        print(f'[{label}] stopped before the deadline; the next job continues', flush=True)
    return rec


# ---- 1. 20-case check against ImageCAS-X ------------------------------------------------------------
check = {}
sp = f'{ICX_W}/splits.json'
if os.path.exists(sp) and os.path.isdir(f'{ICX_W}/icx'):
    test = sorted(json.load(open(sp))['test'])[:N_CHECK]
    jobs = [(c, os.path.realpath(f'{ICX_W}/predict_in/{c}_0000.nii.gz'), f'{W}/check/{c}__totalseg-coronary.nii.gz')
            for c in test if os.path.exists(f'{ICX_W}/predict_in/{c}_0000.nii.gz')]
    run_all(jobs, 'check')
    for c, _, dst in jobs:
        if not os.path.exists(dst):
            continue
        p = np.asarray(nib.load(dst).dataobj) > 0
        r = np.asarray(nib.load(f'{ICX_W}/icx/{int(c[1:]) + 1}.coronary.nii.gz').dataobj) > 0
        tp = float((p & r).sum())
        check[c] = dict(dice=round(2 * tp / max(p.sum() + r.sum(), 1), 4), precision=round(tp / max(p.sum(), 1), 4),
                        recall=round(tp / max(r.sum(), 1), 4))
else:
    print(f'[check] skipped: no icx14 splits/labels under {ICX_W}', flush=True)

# ---- 2. the batch -----------------------------------------------------------------------------------
items = json.load(open(INPUTS))
jobs = [(i['name'], f'{W}/in/{i["name"]}', f'{W}/out/{i["name"][:-7]}__totalseg-coronary.nii.gz')
        for i in items if os.path.exists(f'{W}/in/{i["name"]}')]
new = run_all(jobs, 'batch')
per_case_f = f'{W}/results/per_case.json'
per_case = json.load(open(per_case_f)) if os.path.exists(per_case_f) else {}
for i in items:
    dst = f'{W}/out/{i["name"][:-7]}__totalseg-coronary.nii.gz'
    r = dict(per_case.get(i['name'], {}), **new.get(i['name'], {}))
    r.update(dataset=i['dataset'], priority=i['priority'], annotatable=i['annotatable'],
             spacing_suspect=i['spacing_suspect'])
    if os.path.exists(dst):
        r.pop('error', None)
        if 'volume_ml' not in r:
            r.update(stats(dst))
    per_case[i['name']] = r
json.dump(per_case, open(per_case_f, 'w'), indent=0)

# ---- 3. summary -------------------------------------------------------------------------------------
segd = [r for r in per_case.values() if 'volume_ml' in r]
failed = {k: r['error'] for k, r in per_case.items() if r.get('error')}
flags = {}
for r in segd:
    if r['flag']:
        flags[r['flag']] = flags.get(r['flag'], 0) + 1
res = dict(check=check, check_mean={k: round(float(np.mean([v[k] for v in check.values()])), 4)
                                    for k in ('dice', 'precision', 'recall')} if check else {},
           segmented=len(segd), total=len(items), failed=len(failed), flags=flags,
           median_volume_ml=round(float(np.median([r['volume_ml'] for r in segd])), 2) if segd else None,
           not_downloaded=sum(1 for i in items if not os.path.exists(f'{W}/in/{i["name"]}')),
           complete=all('volume_ml' in r or r.get('error') for r in per_case.values()))   # failures count as done
json.dump(res, open(f'{W}/results/results.json', 'w'), indent=1)
by_ds = {}
for r in segd:
    d = by_ds.setdefault(r['dataset'], [0, 0, 0]); d[0] += 1; d[1] += r['flag'] == 'empty'; d[2] += r['flag'] == 'fragmented'
lines = ['# TotalSegmentator coronary_arteries on the SegQueue volumes', '',
         f'Segmented {len(segd)} of {len(items)} volumes; {len(failed)} failed; {res["not_downloaded"]} not downloaded. '
         'Masks: `$SCRATCH/totalseg/out/`.', '']
if check:
    m = res['check_mean']
    lines += [f'**Check on {len(check)} ImageCAS-X test cases** (binary, vs ImageCAS-X labels > 0): '
              f'Dice {m["dice"]}, precision {m["precision"]}, recall {m["recall"]}.', '']
lines += ['| dataset | segmented | empty (< 0.2 ml) | fragmented |', '|---|---|---|---|']
lines += [f'| {d} | {v[0]} | {v[1]} | {v[2]} |' for d, v in sorted(by_ds.items())]
if failed:
    lines += ['', '## Failed', ''] + [f'- `{k}`: {(e or "").strip().splitlines()[-1][:200] if (e or "").strip() else "?"}'
                                       for k, e in sorted(failed.items())]
open(f'{W}/results/SUMMARY.md', 'w').write('\n'.join(lines) + '\n')
if res['complete']:
    open(f'{W}/DONE', 'w').write('ok')
print(f'[totalseg] {len(segd)}/{len(items)} segmented, {len(failed)} failed; complete={res["complete"]}', flush=True)
