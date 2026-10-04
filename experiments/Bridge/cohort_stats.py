"""Pass A over all binary masks: geometry header + 26-connected components.
usage: cohort_stats.py OUT.jsonl SHARD NSHARDS"""
import sys, json, os, numpy as np, nibabel as nib, cc3d
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools'); from girder import case_ids, mask_path
out, shard, ns = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
done = set()
if os.path.exists(out):
    done = {json.loads(l)['case'] for l in open(out)}
f = open(out, 'a')
for c in case_ids()[shard::ns]:
    if c in done: continue
    im = nib.load(mask_path(c)); A = im.affine
    m = (np.asarray(im.dataobj) > 0.5).astype(np.uint8)
    z = [float(v) for v in im.header.get_zooms()]
    lab, n = cc3d.connected_components(m, connectivity=26, return_N=True)
    st = cc3d.statistics(lab)
    sizes = st['voxel_counts'][1:]; cents = st['centroids'][1:]
    order = np.argsort(-sizes)
    comps = []
    for k in order:
        w = A[:3, :3] @ cents[k] + A[:3, 3]
        bb = st['bounding_boxes'][k + 1]
        comps.append(dict(n=int(sizes[k]), ras=[round(float(x), 1) for x in w],
                          zlo=int(bb[2].start), zhi=int(bb[2].stop)))
    # 6-connectivity too (stricter: is the tree connected face-wise?)
    n6 = cc3d.connected_components(m, connectivity=6, return_N=True)[1]
    rec = dict(case=c, shape=list(m.shape), zooms=z, affine=np.round(A, 4).tolist(),
               axcodes=''.join(nib.aff2axcodes(A)), nvox=int(m.sum()),
               vol_mm3=float(m.sum() * np.prod(z)), ncomp26=int(n), ncomp6=int(n6),
               comps=comps[:12], uniq=sorted(set(np.unique(np.asarray(im.dataobj)[::4, ::4, ::4]).round(3).tolist()))[:5])
    f.write(json.dumps(rec) + '\n'); f.flush()
