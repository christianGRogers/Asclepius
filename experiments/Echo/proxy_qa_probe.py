"""Echo audit probe: run segtrain.proxy.make_case (projection + A4 namer QA) on real cached cases and
measure where the A4 `ignore` voxels lie relative to the namer's LM end (carina).
Usage: proxy_qa_probe.py <out_dir> <icx_seg_dir> case [case ...]"""
import json, sys, time
from pathlib import Path
import numpy as np, nibabel as nib
SCR = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR + '/tools')
from girder import mask_path, ct_path  # noqa: E402
from segtrain import proxy, namer  # noqa: E402

out, icx_dir, cases = Path(sys.argv[1]), Path(sys.argv[2]), sys.argv[3:]
rows = []
for c in cases:
    t = time.time()
    mi = nib.load(mask_path(c)); m = np.asarray(mi.dataobj) > 0.5
    li = nib.load(str(icx_dir / f"{proxy.case_to_imagecas_id(c)}.coronary.nii.gz"))
    lab, st = proxy.project_names(m, np.asarray(li.dataobj), mi.header.get_zooms()[:3])
    d = namer.disagreement(lab, m, mi.affine)
    ign = d["ignore"] & (lab > 0)
    lm_end = d["report"] and namer.extract_decisions(lab, mi.affine).lm_end_vox
    sp = np.sqrt((mi.affine[:3, :3] ** 2).sum(0))
    far = None
    if ign.any() and lm_end is not None:
        dist = np.linalg.norm((np.argwhere(ign) - np.array(lm_end)) * sp, axis=1)
        far = float((dist > 10).mean())
    # world-x of the RCA-named voxels vs left-named voxels (orientation sanity)
    w = lambda sel: float((np.c_[np.argwhere(sel), np.ones(sel.sum())] @ mi.affine.T)[:, 0].mean()) if sel.any() else None
    rows.append(dict(case=c, flags=d["flags"], exclude=bool(d["exclude"]), ramus_only=bool(d["ramus_only"]),
                     ignore_vox=int(ign.sum()), ignore_frac=float(ign.sum() / max(1, (lab > 0).sum())),
                     ignore_share_beyond_10mm_of_carina=far, unreached=st.unreached_frac,
                     world_x_left=w(np.isin(lab, (1, 2, 3))), world_x_rca=w(lab == 4),
                     seconds=round(time.time() - t, 1)))
    print(json.dumps(rows[-1]), flush=True)
out.mkdir(parents=True, exist_ok=True)
(out / "proxy_qa_probe.json").write_text(json.dumps(rows, indent=1))
