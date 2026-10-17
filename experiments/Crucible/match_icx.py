# Match ImageCAS-X segmentations (ImageCAS ids) to our c#### cases by header (shape + affine).
import json, glob, os, re, collections, numpy as np, nibabel as nib
SCR='/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad'
W=SCR+'/work/Crucible'
ours=json.load(open(W+'/our_headers.json'))
def key(shape,aff): return (tuple(shape), tuple(np.round(np.array(aff)[:3],2).ravel()))
idx=collections.defaultdict(list)
for c,v in ours.items(): idx[key(v['shape'],v['affine'])].append(c)
print('our unique keys',len(idx),'of',len(ours))
res={}
for f in sorted(glob.glob(W+'/icx/ImageCAS-X_dataset/segmentations/*.nii.gz')):
    i=int(re.match(r'(\d+)\.',os.path.basename(f)).group(1))
    im=nib.load(f); res[i]=idx.get(key(im.shape,im.affine),[])
n=collections.Counter(len(v) for v in res.values()); print('icx cases',len(res),'matches per case',n)
json.dump({str(k):v for k,v in res.items()},open(W+'/icx_to_ours.json','w'))
# Is the upload order = ImageCAS id order? check monotonic
pairs=sorted((k,v[0]) for k,v in res.items() if len(v)==1)
print(pairs[:10], pairs[-5:])
print('c==id-1 for', sum(int(v[1:])==k-1 for k,v in pairs),'of',len(pairs))
