"""Ingest the Taiwan AI CUP cardiac CT cohort (100 patients, contrast cardiac CTA, HU NIfTI ~0.42 x 0.5 mm) from its
Hugging Face re-host benchang1110/cardiac_segmentation into CCTA-Pool/Taiwan-AICUP-CardiacCT.
Licence unclear (Taiwan Ministry of Education AI CUP competition data, re-hosted without a licence; a PNG copy on
Kaggle claims Apache 2.0). Included with the project lead's approval (2026-10-13), flagged licence_stated=false;
do not redistribute until clarified. train_image/ has 50 images with *_gt.nii.gz label maps (classes undocumented),
test_image/ has 50 images without labels.
Usage: GIRDER_TOKEN_FILE=... ingest_aicup.py <workdir>"""
import json, os, shutil, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccta_ingest import Pool

REPO = 'benchang1110/cardiac_segmentation'
BASE = f'https://huggingface.co/datasets/{REPO}/resolve/main/'
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


with urllib.request.urlopen(f'https://huggingface.co/api/datasets/{REPO}?full=true', timeout=120) as r:
    files = [s['rfilename'] for s in json.load(r)['siblings']]
images = sorted(f for f in files if f.endswith('.nii.gz') and not f.endswith('_gt.nii.gz'))
pool = Pool()
DS = 'Taiwan-AICUP-CardiacCT'
pool.dataset(DS, 'unclear (competition data re-hosted without a licence; included with the project lead\'s approval)',
             'T2', f'https://huggingface.co/datasets/{REPO}',
             'Taiwan AI CUP (Ministry of Education) cardiac CT competition cohort, re-hosted on Hugging Face as HU '
             'NIfTI: 100 contrast cardiac CTA patients, ~0.42 mm in-plane, 0.5 mm slices, coronaries visible. '
             '50 have competition label maps (label.nii.gz, classes undocumented). Licence not stated: do not '
             'redistribute until clarified.',
             citation=f'Taiwan AI CUP cardiac CT competition data, via Hugging Face {REPO}.')
for img in images:
    case = os.path.basename(img)[:-7]
    if pool.case_done(DS, case):
        print('exists', case, flush=True); continue
    ip = fetch(img, os.path.join(work, 'ct.nii.gz'))
    files_extra = {}
    gt = img[:-7] + '_gt.nii.gz'
    if gt in files:
        files_extra['label.nii.gz'] = fetch(gt, os.path.join(work, 'label.nii.gz'))
    extra = dict(source_ids={'hf_repo': REPO, 'file': img}, licence_stated=False, hu_calibrated=True,
                 split=img.split('/')[0], label_classes='competition labels, classes undocumented' if files_extra else None)
    print(pool.ingest(DS, case, ip, extra, files=files_extra or None), case, flush=True)
    for p in [ip] + list(files_extra.values()):
        if os.path.exists(p): os.remove(p)
