"""Score one arm's 80 val predictions with score.py (A1 tF1, flags, FP census, threshold sweep), in parallel.
Idempotent per case (a per-case JSON cache in <out>.d/). Refuses sealed cases.
Usage: score_run.py <arm> <pred_dir> <ref_dir> <layout.json> <aorta_dir> <icx_dir> <cl_dir> <cases.json> <sealed.json>
                    <out.json> <n_proc>"""
import json
import os
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score  # noqa: E402
import vtkcl  # noqa: E402

arm, pred_dir, ref_dir, layout_json, aorta_dir, icx_dir, cl_dir, cases_json, sealed_json, out, NP = sys.argv[1:12]
NP = int(NP)
L = json.load(open(layout_json))['cases']
cases = json.load(open(cases_json))
S = json.load(open(sealed_json))
if set(cases) & (set(S['sealed_icx_test']) | set(S['sealed_quality0'])):
    sys.exit('[score] REFUSING: sealed case in the case list')
cache = out + '.d'
os.makedirs(cache, exist_ok=True)


def starts(c):
    n = int(c[1:]) + 1; d = {}
    for side in ('left', 'right'):
        f = f'{cl_dir}/{n}.coronary_{side}_centerline.vtk'
        if os.path.exists(f):
            try:
                s = vtkcl.start_points(f)
                if s is not None and len(s):
                    d[side] = s
            except Exception as e:
                print(f'[score] {c} {side} centreline unreadable: {e!r}', flush=True)
    return d


def one(c):
    f = f'{cache}/{c}.json'
    if os.path.exists(f):
        return json.load(open(f))
    t = time.time()
    try:
        r = score.score_case(c, f'{pred_dir}/{c}.nii.gz', f'{ref_dir}/{c}.nii.gz',
                             ct_path=L.get(c, {}).get('ct'), aorta_path=f'{aorta_dir}/{c}_aorta.nii.gz',
                             icx_path=f'{icx_dir}/{int(c[1:]) + 1}.coronary.nii.gz',
                             npz_path=f'{pred_dir}/{c}.npz', starts_world=starts(c),
                             sweep=os.environ.get('SCORE_SWEEP', '1') != '0')
        r['sec'] = time.time() - t
    except Exception as e:
        r = dict(case=c, error=repr(e)[:500])
    json.dump(r, open(f + '.part', 'w')); os.replace(f + '.part', f)
    print(f"[score {arm}] {c} {time.time() - t:.0f}s {'ERROR ' + r['error'] if 'error' in r else ''}", flush=True)
    return r


todo = [c for c in cases if os.path.exists(f'{pred_dir}/{c}.nii.gz')]
print(f'[score {arm}] {len(todo)}/{len(cases)} predictions present; {NP} workers', flush=True)
with Pool(NP, maxtasksperchild=4) as p:
    per = p.map(one, todo, chunksize=1)
ok = [r for r in per if 'error' not in r]
json.dump(dict(arm=arm, per_case=ok, errors=[r for r in per if 'error' in r],
               summary=score.aggregate(ok) if ok else None), open(out, 'w'), indent=1)
print(f'[score {arm}] {len(ok)} scored, {len(per) - len(ok)} errors -> {out}', flush=True)
