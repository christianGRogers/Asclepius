"""Janus 1-F round 2 (Foxtrot): stage 2's background band, measured on D45's 620 training labels (CPU, labels only).

Stage 2 (F-A11) turns ImageCAS-X background near the traced tree into the set {bg, S1-S3, SN, Conus, RMA}, because
ImageCAS-X never traced those classes. Per case, for band half-widths w in {4, 8, 15, 25} mm and per parent region:
  S   -- the LAD trunk (1-F label 2): where septals leave;
  N   -- the RCA's first 30 mm and the LCx's first 20 mm by geodesic arc from the ostium end: SN and conus;
  R   -- the RCA from 20 mm to 80 % of its arc length: right marginals;
it reports the released background (mm^3), its share of a 256^3 patch at 0.5 mm (2.10e6 mm^3) and of all background
within 25 mm of the tree, where along the LAD the S band lies (proximal / mid / distal thirds of arc), and how much
traced branch volume (D1-D3, OM1-2, Ramus, PDA, PLB) lies within w of the LAD (where an S head borders a traced one).
Synthetic septals: straight 1 mm tubes leaving the LAD trunk at 15 %, 30 % and 45 % of its arc, aimed at the nearest
PDA voxel (the septum spans the two interventricular grooves; tree centroid if no PDA); for lengths 10-60 mm, the
share of each tube's centreline that lies within w of the LAD label (inside the band, so unpenalised by the CE term).
The septal lengths are a sweep, not a measurement: no CT and no traced septal exists in ImageCAS-X.
Usage: python3 band.py <label_dir> <out.jsonl> <every_k> [nproc]
"""
import json, os, sys
from multiprocessing import Pool
import numpy as np, nibabel as nb
from scipy import ndimage as ndi
from skimage.graph import MCP_Geometric

HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import labels_r2 as L  # noqa
from pass1 import TRAIN  # noqa  (pin-checked 620)

WS = (4, 8, 15, 25); LENS = (10, 20, 30, 40, 60); FRACS = (.15, .30, .45)
PATCH_MM3 = (256 * .5) ** 3


def arc_from(mask, z, src):
    d, _ = MCP_Geometric(np.where(mask, 1.0, np.inf), sampling=tuple(z)).find_costs([tuple(s) for s in src])
    d[~mask] = np.inf
    return d


def ostium_end(mask, z):
    pts = np.argwhere(mask)
    d1 = arc_from(mask, z, pts[:1]); a = np.unravel_index(np.argmin(np.where(np.isfinite(d1), -d1, np.inf)), mask.shape)
    d2 = arc_from(mask, z, [a]); b = np.unravel_index(np.argmin(np.where(np.isfinite(d2), -d2, np.inf)), mask.shape)
    e = ndi.distance_transform_edt(mask, sampling=z)
    return a if e[a] >= e[b] else b


def one(path):
    cid = 'c%04d' % (int(os.path.basename(path).split('.')[0]) - 1)
    assert cid in TRAIN
    im = nb.load(path); z = np.array(im.header.get_zooms()[:3], float)
    raw = np.asarray(im.dataobj).astype(np.uint8)
    mg = np.ceil(27 / z).astype(int)
    sl0 = ndi.find_objects((raw > 0).astype(np.uint8))[0]
    sl = tuple(slice(max(s.start - m, 0), min(s.stop + m, n)) for s, m, n in zip(sl0, mg, raw.shape))
    raw = raw[sl]
    lab, _ = L.map13(raw, z)
    vv = float(np.prod(z)); bg = lab == 0
    lad, lcx, rca = lab == 2, lab == 3, lab == 4
    row = {'case': cid}
    # arcs
    lm = lab == 1
    src_left = np.argwhere(lm) if lm.any() else None
    arc_lad = arc_from(lad, z, np.argwhere(lad & ndi.binary_dilation(lm, iterations=2)) if (src_left is not None and (lad & ndi.binary_dilation(lm, iterations=2)).any()) else [ostium_end(lad, z)])
    arc_lcx = arc_from(lcx, z, np.argwhere(lcx & ndi.binary_dilation(lm, iterations=2)) if (src_left is not None and (lcx & ndi.binary_dilation(lm, iterations=2)).any()) else [ostium_end(lcx, z)])
    arc_rca = arc_from(rca, z, [ostium_end(rca, z)])
    Lr = float(np.max(arc_rca[np.isfinite(arc_rca)])); La = float(np.max(arc_lad[np.isfinite(arc_lad)]))
    row['arc_mm'] = {'LAD': round(La, 1), 'RCA': round(Lr, 1), 'LCx': round(float(np.max(arc_lcx[np.isfinite(arc_lcx)])), 1)}
    regN = (rca & (arc_rca <= 30)) | (lcx & (arc_lcx <= 20))
    regR = rca & (arc_rca > 20) & (arc_rca <= .8 * Lr)
    dS, iS = ndi.distance_transform_edt(~lad, sampling=z, return_indices=True)
    dN = ndi.distance_transform_edt(~regN, sampling=z) if regN.any() else np.full(lab.shape, np.inf)
    dR = ndi.distance_transform_edt(~regR, sampling=z) if regR.any() else np.full(lab.shape, np.inf)
    dT = ndi.distance_transform_edt(lab == 0, sampling=z)
    near25 = bg & (dT <= 25)
    arc_at = arc_lad[iS[0], iS[1], iS[2]] / La
    traced_br = np.isin(lab, [5, 6, 7, 8, 9, 10, 11, 12])
    row['bg_within25_mm3'] = round(near25.sum() * vv)
    row['traced_mm3'] = round(float((lab > 0).sum() * vv), 1)
    row['bands'] = {}
    for w in WS:
        bS, bN, bR = bg & (dS <= w), bg & (dN <= w), bg & (dR <= w)
        U = bS | bN | bR
        a = arc_at[bS]
        row['bands'][w] = {'S': round(bS.sum() * vv), 'N': round(bN.sum() * vv), 'R': round(bR.sum() * vv),
                           'union': round(U.sum() * vv), 'union_patch_share': round(U.sum() * vv / PATCH_MM3, 4),
                           'union_share_bg25': round(U.sum() / max(near25.sum(), 1), 4),
                           'S_prox_mid_dist': [round(float(np.mean(a < 1 / 3)), 3), round(float(np.mean((a >= 1 / 3) & (a < 2 / 3))), 3), round(float(np.mean(a >= 2 / 3)), 3)] if a.size else None,
                           'SN_overlap': round((bS & (bN | bR)).sum() * vv),
                           'traced_branch_within_w_of_LAD_share': round(float((traced_br & (dS <= w)).sum() / max(traced_br.sum(), 1)), 4)}
    # synthetic septals
    pda = np.argwhere(lab == 11)
    tgt_all = pda * z if len(pda) else np.argwhere(lab > 0).mean(0, keepdims=True) * z
    syn = []
    for f in FRACS:
        cand = np.argwhere(lad & (np.abs(arc_lad - f * La) < 1.0))
        if not len(cand):
            continue
        p0 = cand[0] * z
        tgt = tgt_all[np.argmin(np.linalg.norm(tgt_all - p0, axis=1))]
        u = tgt - p0; nu = np.linalg.norm(u)
        if nu < 1:
            continue
        u /= nu
        t = np.arange(0, max(LENS) + .25, .25)
        P = p0[None] + t[:, None] * u[None]
        idx = np.round(P / z).astype(int)
        ok = np.all((idx >= 0) & (idx < np.array(lab.shape)), 1)
        d = np.full(len(t), np.inf); d[ok] = dS[tuple(idx[ok].T)]
        hit = np.zeros(len(t), bool); hit[ok] = lab[tuple(idx[ok].T)] > 0
        rec = {'frac': f, 'dist_to_pda_mm': round(float(nu), 1)}
        for Ln in LENS:
            k = t <= Ln
            rec[Ln] = {w: round(float(np.mean(d[k] <= w)), 3) for w in WS}
            rec[Ln]['hits_traced'] = round(float(np.mean(hit[k & (t > 2)])), 3)
        syn.append(rec)
    row['synthetic_septals'] = syn
    return row


if __name__ == '__main__':
    d, out, k = sys.argv[1], sys.argv[2], int(sys.argv[3])
    npr = int(sys.argv[4]) if len(sys.argv) > 4 else 1
    files = sorted(os.path.join(d, f) for f in os.listdir(d) if f.endswith('.coronary.nii.gz'))
    files = [f for f in files if (int(os.path.basename(f).split('.')[0]) - 1) % k == 0]
    done = {json.loads(l)['case'] for l in open(out)} if os.path.exists(out) else set()
    todo = [f for f in files if 'c%04d' % (int(os.path.basename(f).split('.')[0]) - 1) not in done]
    with Pool(npr, maxtasksperchild=10) as p, open(out, 'a') as fo:
        for i, r in enumerate(p.imap_unordered(one, todo)):
            fo.write(json.dumps(r) + '\n'); fo.flush()
            print(i, r['case'], flush=True)
