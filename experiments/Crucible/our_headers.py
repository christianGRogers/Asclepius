# Header + cheap stats for all 1000 binary masks -> work/Crucible/our_headers.json
import sys, json, numpy as np, nibabel as nib
SCR='/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR+'/tools'); from girder import case_ids, mask_path
out={}
full = '--full' in sys.argv
for c in case_ids():
    im=nib.load(mask_path(c)); h=im.header
    r={'shape':list(im.shape),'zooms':[float(x) for x in h.get_zooms()],'affine':np.round(im.affine,4).tolist()}
    if full:
        a=np.asarray(im.dataobj)>0.5
        idx=np.argwhere(a); r['nvox']=int(a.sum()); r['centroid']=idx.mean(0).round(2).tolist()
    out[c]=r
json.dump(out,open(SCR+'/work/Crucible/our_headers.json','w'))
