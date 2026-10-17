"""Round 3 (HuggingFace agent): ingest CCA-200 public training split (20 CCTA, coronary lumen labels) from Hugging Face
MedHK23/CCA into CCTA-Pool/CCA200-HF.
Yang et al., "Segmentation and Vascular Vectorization for Coronary Artery by Geometry-based Cascaded Neural Network",
arXiv:2305.04208. Licence on the HF repo: GPL-3.0. Volumes are HU int16 NIfTI, 0.5 mm isotropic (resampled), LPS affine.
Labels: binary coronary artery (radiologist internal-diameter annotations).
Usage: GIRDER_TOKEN_FILE=... huggingface_cca.py <workdir>"""
import json, os, shutil, sys, time, urllib.request
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from ccta_ingest import Pool

REPO = 'MedHK23/CCA'
BASE = f'https://huggingface.co/datasets/{REPO}/resolve/main/'
DS = 'CCA200-HF'
work = sys.argv[1]; os.makedirs(work, exist_ok=True)


def fetch(path, dst):
    for attempt in range(5):
        try:
            with urllib.request.urlopen(BASE + path, timeout=600) as r, open(dst, 'wb') as f:
                shutil.copyfileobj(r, f)
            return dst
        except Exception as e:
            print('retry', path, repr(e)[:100], flush=True); time.sleep(10 * (attempt + 1))
    raise RuntimeError(f'could not fetch {path}')


with urllib.request.urlopen(f'https://huggingface.co/api/datasets/{REPO}', timeout=120) as r:
    files = [s['rfilename'] for s in json.load(r)['siblings']]
images = sorted((f for f in files if f.startswith('train/images/') and f.endswith('.nii.gz')),
                key=lambda f: int(os.path.basename(f)[:-7]))
pool = Pool()
pool.dataset(DS, 'GPL-3.0 (as stated on the Hugging Face dataset card)', 'T1', f'https://huggingface.co/datasets/{REPO}',
             'CCA-200 coronary CTA dataset (Shanghai AI Lab / CUHK; arXiv:2305.04208): public training split, 20 CCTA '
             'with coronary artery disease, HU NIfTI resampled to 0.5 mm isotropic, heart-centred FOV. label.nii.gz = '
             'binary coronary artery lumen (internal diameter annotated by radiologists). Independent collection '
             '(not ImageCAS).',
             citation='Yang X, Xu L, Yu S, Xia Q, Li H, Zhang S. Segmentation and Vascular Vectorization for Coronary '
                      'Artery by Geometry-based Cascaded Neural Network. arXiv:2305.04208 (2023).')
for img in images:
    case = 'CCA_' + os.path.basename(img)[:-7].zfill(2)
    if pool.case_done(DS, case):
        print('exists', case, flush=True); continue
    ip = fetch(img, os.path.join(work, 'ct.nii.gz'))
    lab = 'train/labels/' + os.path.basename(img)
    fx = {}
    if lab in files:
        fx['label.nii.gz'] = fetch(lab, os.path.join(work, 'label.nii.gz'))
    extra = dict(source_ids={'hf_repo': REPO, 'file': img}, licence_stated=True, hu_calibrated=True, split='train',
                 resampled_isotropic_mm=0.5, label_classes={'1': 'coronary artery'} if fx else None)
    print(pool.ingest(DS, case, ip, extra, files=fx or None), case, flush=True)
    for p in [ip] + list(fx.values()):
        if os.path.exists(p): os.remove(p)
