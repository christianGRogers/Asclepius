"""Round 3 (agent Modelling): SLAWT 2016 CT set -> CCTA-Pool.

STACOM 2016 Left Atrial Wall Thickness challenge (Karim et al., Med Image Anal 50:36-53, 2018). 10 ECG-gated
coronary CTAs (Philips 256 iCT, IV contrast, single breath hold, 0.8-1 mm slices, 0.4 mm increment, 250 mm FOV),
released as NIfTI on figshare *private links* (CC BY 4.0 shown on the item pages) linked from
https://www.doc.ic.ac.uk/~rkarim/la_lv_framework/wall/datasets.html . The figshare pages sit behind an AWS WAF
JavaScript challenge, but ndownloader.figshare.com serves the files with ?private_link= directly; the S3
redirect is signed for only 10 s, so every range request goes through ndownloader again.
The supplement zip (SLAWT_CT_la_chamber, 1.8 MB) holds LA chamber approximations CT_N_la.nii: attached as
label.nii.gz when it shares the image grid.

    python3 -I modelling_slawt.py --dry-run [--case CT_1]      # stage one case in --stage
    python3 -I modelling_slawt.py [--case ...] [--limit N]      # upload (needs GIRDER_TOKEN_FILE)
"""
import argparse, os, shutil, subprocess, sys, zipfile
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ingest_open as io_  # noqa: E402

CT = 'https://ndownloader.figshare.com/files/5011837?private_link=2a5de3a2b89a3fb87932'
LA = 'https://ndownloader.figshare.com/files/5028424?private_link=0ffc9facc15436a41ff9'
DATASET = 'SLAWT2016-CT'


class F(io_.HTTPFile):
    def _resolve(self):
        super()._resolve()
        self.url = self.src


def to_gz(src, dst, dtype=None):
    im = nib.load(src)
    a = np.asanyarray(im.dataobj)
    if a.ndim == 4 and a.shape[3] == 1:
        a = a[..., 0]
    if dtype is not None:
        a = a.astype(dtype)
    out = nib.Nifti1Image(a, im.affine)
    out.header.set_qform(im.affine, 1)
    out.header.set_sform(im.affine, 1)
    out.header.set_xyzt_units('mm')
    if dtype is not None:
        out.set_data_dtype(dtype)
    nib.save(out, dst)
    return dst


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--case', nargs='*')
    ap.add_argument('--limit', type=int, default=0)
    here = os.path.dirname(os.path.abspath(__file__))
    ap.add_argument('--stage', default='/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/sourcing/round3/work_Modelling/stage')
    ap.add_argument('--work', default='/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/sourcing/round3/work_Modelling')
    args = ap.parse_args()
    os.makedirs(args.work, exist_ok=True)
    sink = io_.Sink(
        args, DATASET, 'CC BY 4.0', 'T1',
        'https://www.doc.ic.ac.uk/~rkarim/la_lv_framework/wall/datasets.html',
        'STACOM 2016 SLAWT (Left Atrial Wall Thickness) challenge CT set, King\'s College London / Guy\'s and '
        'St Thomas\' (NIHR BRC). 10 ECG-gated contrast coronary CTAs, Philips 256 iCT, 0.8-1 mm slices '
        '(0.4 mm increment), 512x512, 250 mm FOV; released as NIfTI on figshare private links '
        '(SLAWT_CT_set.zip, file 5011837, CC BY 4.0). label.nii.gz = the released LA chamber approximation '
        '(SLAWT_CT_la_chamber supplement, file 5028424): 1 = left atrium blood pool (approximate).',
        'Karim R. et al. (2018). Algorithms for left atrial wall segmentation and thickness - Evaluation on an '
        'open-source CT and MRI image database. Medical Image Analysis 50:36-53. doi:10.1016/j.media.2018.08.004. '
        'Data: SLAWT_CT_set, figshare (CC BY 4.0), https://www.doc.ic.ac.uk/~rkarim/la_lv_framework/wall/')
    z = zipfile.ZipFile(F(CT, block=8 << 20))
    lzip = io_.download(LA, os.path.join(args.work, 'SLAWT_CT_supplement.zip'))   # 1.8 MB, Deflate64
    lnames = set(subprocess.run(['unzip', '-Z1', lzip], check=True, capture_output=True, text=True).stdout.split())
    for info in sorted(z.infolist(), key=lambda i: int(''.join(c for c in i.filename if c.isdigit()) or 0)):
        case = os.path.basename(info.filename)[:-4]
        if not info.filename.endswith('.nii') or not io_.selected(args, case) or sink.done(case):
            continue
        work = io_.tmpdir(args)
        try:
            raw = io_.copy_member(z.open(info), os.path.join(work, 'ct.nii'))
            ct = to_gz(raw, os.path.join(work, 'ct.nii.gz'))
            os.remove(raw)
            files, lm = {}, f'{case}_la.nii'
            if lm in lnames:
                lraw = os.path.join(work, 'la.nii')
                with open(lraw, 'wb') as fh:   # Python's zipfile cannot inflate Deflate64; unzip can
                    subprocess.run(['unzip', '-p', lzip, lm], check=True, stdout=fh)
                li, ci = nib.load(lraw), nib.load(ct)
                if li.shape[:3] == ci.shape[:3] and np.allclose(li.affine, ci.affine, atol=1e-3):
                    files['label.nii.gz'] = to_gz(lraw, os.path.join(work, 'label.nii.gz'), np.uint8)
                else:
                    io_.log(f'{case}: LA label grid differs ({li.shape} vs {ci.shape}); not attached')
            extra = dict(source_ids={'figshare_file_id': 5011837, 'archive': 'SLAWT_CT_set.zip',
                                     'member': info.filename, **({'label_file_id': 5028424, 'label_member': lm}
                                                                 if files else {})},
                         scanner='Philips Brilliance iCT 256', ecg_gated=True, hu_calibrated=True,
                         blood_pool_median_hu=io_.blood_pool_hu(ct), orientation_check=io_.anatomy_check(ct),
                         labels={'label.nii.gz': {'1': 'left atrium chamber (approximation)'}} if files else {})
            sink.put(case, ct, extra, files)
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


if __name__ == '__main__':
    main()
