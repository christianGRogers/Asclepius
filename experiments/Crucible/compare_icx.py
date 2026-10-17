# For every ImageCAS-X case: verify the header match to our case c{id-1} (tolerant), then compare
# ICX merged lumen vs our binary mask (Dice, coverage), and per-ICX-class coverage by our mask.
import json, glob, os, re, sys, numpy as np, nibabel as nib
from scipy import ndimage as ndi
SCR='/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
sys.path.insert(0, SCR+'/tools'); from girder import mask_path
W=SCR+'/work/Crucible'
ours=json.load(open(W+'/our_headers.json'))
rows=[]
files=sorted(glob.glob(W+'/icx/ImageCAS-X_dataset/segmentations/*.nii.gz'))
files=sorted(files,key=lambda f:int(os.path.basename(f).split('.')[0]))[::4]  # 200-case subset
SH,NS=int(sys.argv[1]),int(sys.argv[2]); files=files[SH::NS]
for f in files:
    i=int(re.match(r'(\d+)\.',os.path.basename(f)).group(1)); c='c%04d'%(i-1)
    try: im=nib.load(f); L=np.asarray(im.dataobj).astype(np.uint8)
    except Exception as e: print('bad',f,e); continue
    o=ours[c]
    hdr_ok = list(im.shape)==o['shape'] and np.allclose(im.affine, np.array(o['affine']), atol=0.01)
    m=np.asarray(nib.load(mask_path(c)).dataobj)>0.5
    u=np.argwhere((L>0)|m); lo=np.maximum(u.min(0)-8,0); hi=u.max(0)+9
    sl=tuple(slice(a,b) for a,b in zip(lo,hi)); L=L[sl]; m=m[sl]
    x=L>0; inter=(x&m).sum()
    r={'id':i,'case':c,'hdr_ok':bool(hdr_ok),'dice':float(2*inter/(x.sum()+m.sum())),
       'icx_vox':int(x.sum()),'our_vox':int(m.sum()),
       'icx_cov_by_ours':float(inter/x.sum()),'ours_cov_by_icx':float(inter/m.sum())}
    # tolerant Dice: ICX dilated by 1 voxel vs ours, and vice versa (boundary-convention check)
    xd=ndi.binary_dilation(x); md=ndi.binary_dilation(m)
    r['ours_within1_icx']=float((m&xd).sum()/m.sum()); r['icx_within1_ours']=float((x&md).sum()/x.sum())
    # component count of our mask outside ICX dilated by 2 mm-ish (5 vox): spurious structures
    far=m & ~ndi.binary_dilation(x,iterations=5)
    r['ours_far_frac']=float(far.sum()/m.sum())
    lab,n=ndi.label(m); r['our_ncomp']=int(n)
    lab2,n2=ndi.label(x); r['icx_ncomp']=int(n2)
    for k in range(1,15):
        v=(L==k); s=int(v.sum()); r[f'n{k}']=s
        r[f'cov{k}']=float((v&m).sum()/s) if s else None
    rows.append(r); print(i,c,hdr_ok,round(r['dice'],3),round(r['icx_cov_by_ours'],3),round(r['ours_cov_by_icx'],3),flush=True)
json.dump(rows,open(W+f'/compare_icx_{SH}.json','w'))
