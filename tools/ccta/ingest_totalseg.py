"""Ingest the 130 contrast cardiac / thoracic-aorta CTs of TotalSegmentator v2.0.1 (Wasserthal et al., Zenodo
10047292, CC BY 4.0, University Hospital Basel) into CCTA-Pool/TotalSegmentator-cardiac.
Case ids and metadata: totalseg_cardiac_ids.json (from the dataset's meta.csv; contrast checked per case by
measuring the median HU in its own aorta / left-atrium masks). Volumes are fetched from a Hugging Face mirror
of the Zenodo release (values checked identical on one case); every image is 1.5 mm isotropic, as released.
Usage: GIRDER_TOKEN_FILE=... ingest_totalseg.py <workdir>"""
import json, os, shutil, sys, time, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccta_ingest import Pool

MIRROR = 'https://huggingface.co/datasets/MedOtter/totalsegmentator-cardiac/resolve/main/{id}/ct.nii.gz'
work = sys.argv[1]
ids = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'totalseg_cardiac_ids.json')))
pool = Pool()
pool.dataset('TotalSegmentator-cardiac', 'CC BY 4.0', 'T2 (1.5 mm)', 'https://zenodo.org/records/10047292',
             'Contrast cardiac, TAVI, left-atrium and thoracic-aorta CTs from TotalSegmentator v2.0.1 (University '
             'Hospital Basel), 130 of the 144 cardiac-labelled cases (the other 14 are non-contrast). Resampled to '
             '1.5 mm isotropic by the authors, so only proximal/mid coronaries are resolved.',
             citation='Wasserthal J et al., TotalSegmentator: robust segmentation of 104 anatomic structures in CT '
                      'images, Radiology: AI 2023; data Zenodo 10.5281/zenodo.10047292 (CC BY 4.0).')
os.makedirs(work, exist_ok=True)
for cid in ids['gated_like'] + ids['contrast_other']:
    if pool.case_done('TotalSegmentator-cardiac', cid):
        print('exists', cid, flush=True); continue
    p = os.path.join(work, f'{cid}.nii.gz')
    for attempt in range(5):
        try:
            with urllib.request.urlopen(MIRROR.format(id=cid), timeout=300) as r, open(p, 'wb') as f:
                shutil.copyfileobj(r, f)
            break
        except Exception as e:
            print('retry', cid, repr(e)[:100], flush=True); time.sleep(10 * (attempt + 1))
    else:
        print('FAILED', cid, flush=True); continue
    extra = dict(source_ids={'totalsegmentator_id': cid, 'zenodo': 10047292}, hu_calibrated=True,
                 subset='gated_like' if cid in ids['gated_like'] else 'contrast_other', **ids['meta'][cid])
    print(pool.ingest('TotalSegmentator-cardiac', cid, p, extra), cid, flush=True)
    os.remove(p)
