"""Round 3 (agent Kaggle): Kaggle mrdurch/weakly-supervised-3d-cardiac-image-segmentation -> CCTA-Pool.
5 test CCTA volumes (NIfTI, HU, 0.43 x 0.43 x 0.5 mm) + ground-truth LV myo / LV blood / RV labels.
The release names files after patients; those names are NEVER stored: cases are numbered 1-5 in the order
of the file list, and only a truncated sha256 of the file name is kept for re-identification of the source file.
    kaggle_mrdurch.py [--dry-run] [--stage DIR] [--limit N]"""
import argparse, hashlib, os, shutil, sys, tempfile
import numpy as np, nibabel as nib
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kaggle_common as kc
from ingest_open import Sink

REF = 'mrdurch/weakly-supervised-3d-cardiac-image-segmentation'


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true'); ap.add_argument('--stage', default='stage')
    ap.add_argument('--limit', type=int, default=0); ap.add_argument('--work', default=None)
    ap.add_argument('--case', nargs='*')
    a = ap.parse_args()
    sink = Sink(a, 'Kaggle-mrdurch-WS3D-Cardiac', 'CC0 1.0 (as stated by the uploader; provenance unverified)', 'T1',
                f'https://www.kaggle.com/datasets/{REF}',
                'Kaggle "weakly-supervised-3D-cardiac-image-segmentation" (uploader mrdurch, 2025/26): the 5 test '
                'volumes of a SAM-Med3D-based weakly supervised LV/RV segmentation project trained on 430 of 570 '
                'Chinese hospital cardiac CT cases (institution not documented). Gated-looking CCTA, 512x512, '
                '0.43 mm in-plane, 0.5 mm slices, HU. Source file names are patient names and are NOT stored. '
                'label.nii.gz = the release label_GT: 1 LV myocardium, 2 LV blood pool, 3 RV, 255 ignore '
                '(GT region SAM-Med3D missed). provenance_verified=false: check before sharing labels.',
                'mrdurch, "weakly-supervised-3D-cardiac-image-segmentation", Kaggle, '
                f'https://www.kaggle.com/datasets/{REF} (CC0 as stated).')
    files = kc.kaggle_files(REF)
    imgs = sorted(n for n in files if n.startswith('result/test/images/'))
    for k, img in enumerate(imgs, 1):
        case = f'case{k}'
        if a.case and case not in a.case or sink.done(case):
            continue
        base = os.path.basename(img)[:-4]
        work = tempfile.mkdtemp(prefix='kg-mrdurch-', dir=a.work)
        try:
            ip = kc.fetch(REF, img, os.path.join(work, 'img.nii'))
            lp = kc.fetch(REF, f'result/test/label_GT/{base}.nii', os.path.join(work, 'lab.nii'))
            im = nib.load(ip)
            ct = os.path.join(work, 'ct.nii.gz')
            nib.save(nib.Nifti1Image(np.asarray(im.dataobj).astype(np.int16), im.affine, im.header), ct)
            os.remove(ip)
            lb = nib.load(lp)
            l = np.asarray(lb.dataobj).astype(np.uint8)
            assert l.shape == im.shape[:3], (l.shape, im.shape)
            lab = os.path.join(work, 'label.nii.gz')
            h = lb.header.copy(); h.set_data_dtype(np.uint8)
            nib.save(nib.Nifti1Image(l, lb.affine, h), lab)
            os.remove(lp)
            chk = kc.anatomy_check(ct, lab, 2)
            extra = dict(source_ids={'kaggle': REF, 'file_index': k,
                                     'file_name_sha256_16': hashlib.sha256(base.encode()).hexdigest()[:16]},
                         provenance_verified=False, hu_calibrated=True, orientation_check=chk,
                         label_file='label.nii.gz', label_classes='1 LV myo,2 LV blood,3 RV (per README; on case1 class 3 lies where the LA is: verify),255 ignore',
                         label_values=sorted(int(v) for v in np.unique(l)))
            sink.put(case, ct, extra, files={'label.nii.gz': lab})
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


if __name__ == '__main__':
    main()
