"""Round 3 (agent Modelling): figshare private item "DCM3_Pulmonary_35" -> CCTA-Pool.

https://figshare.com/s/caa70792c43ac01d8175 (CC BY 4.0 on the item page; behind an AWS WAF JS challenge, but
ndownloader serves the files with ?private_link=). One de-identified cardiac CTA (study "CTA CARDIAC
MORPHOLOGY", series "PULMONARY VEIN, 35%, iDose (3)": a 35 % R-R phase reconstruction, i.e. ECG-gated), Philips
iCT 256, 512x512x354, 0.38x0.38 mm, 0.8 mm slices at 0.4 mm. NOTE the file names on figshare are swapped:
"dcm3_annotations.zip" (file 45936537) holds the DICOM study, "dcm3_pulmonary_35.zip" (file 45936534) the
CVAT-style per-slice colour PNG annotations (SegmentationClass/<SOPInstanceUID>.png + labelmap.txt), which are
converted to an integer label volume on the CT grid (label ids = labelmap order).

    python3 modelling_dcm3.py --dry-run | upload (needs GIRDER_TOKEN_FILE)
"""
import argparse, glob, json, os, shutil, subprocess, sys, tempfile
import numpy as np, nibabel as nib

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ingest_open as io_  # noqa: E402

PL = 'caa70792c43ac01d8175'
DCM_FILE, ANN_FILE = 45936537, 45936534
URL = 'https://ndownloader.figshare.com/files/{}?private_link=' + PL
DATASET = 'Figshare-DCM3-Pulmonary35'
WORK = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/sourcing/round3/work_Modelling'


def load_series(dcm_dir):
    import pydicom
    sl = []
    for f in glob.glob(os.path.join(dcm_dir, '**', '*.dcm'), recursive=True):
        d = pydicom.dcmread(f, stop_before_pixels=True)
        if 'PULMONARY VEIN' in str(d.get('SeriesDescription', '')) and d.get('Rows') == 512:
            sl.append((float(d.ImagePositionPatient[2]), f, d))
    sl.sort(key=lambda t: t[0])
    d0 = sl[0][2]
    rows = [np.asarray(pydicom.dcmread(f).pixel_array, np.float32) * float(d.RescaleSlope) + float(d.RescaleIntercept)
            for _, f, d in sl]
    a = np.stack(rows, -1).transpose(1, 0, 2)          # (col=x, row=y, z)
    ps = [float(v) for v in d0.PixelSpacing]           # row spacing, col spacing
    o = np.array([float(v) for v in d0.ImagePositionPatient])
    dz = (sl[-1][0] - sl[0][0]) / (len(sl) - 1)
    rc = np.array([float(v) for v in d0.ImageOrientationPatient])
    # LPS world = o + i*ps[1]*row_dir + j*ps[0]*col_dir + k*dz*z ; convert to RAS
    aff = np.eye(4)
    aff[:3, 0], aff[:3, 1], aff[:3, 2], aff[:3, 3] = rc[:3] * ps[1], rc[3:] * ps[0], [0, 0, dz], o
    aff = np.diag([-1, -1, 1, 1]) @ aff
    uids = [os.path.basename(f)[:-4] for _, f, _ in sl]   # PNGs are named after the DICOM file names (not the SOP UID tag)
    meta = dict(manufacturer=str(d0.get('Manufacturer', '')), scanner=str(d0.get('ManufacturerModelName', '')),
                series_description=str(d0.get('SeriesDescription', '')),
                study_description=str(d0.get('StudyDescription', '')), kvp=str(d0.get('KVP', '')),
                kernel=str(d0.get('ConvolutionKernel', '')), slice_thickness_mm=float(d0.SliceThickness),
                slice_increment_mm=round(abs(dz), 4), recon_diameter_mm=str(d0.get('ReconstructionDiameter', '')))
    return a.astype(np.int16), aff, uids, meta


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--stage', default=os.path.join(WORK, 'stage'))
    ap.add_argument('--work', default=WORK)
    ap.add_argument('--case', nargs='*')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    sink = io_.Sink(
        args, DATASET, 'CC BY 4.0', 'T1', 'https://figshare.com/s/' + PL,
        'figshare private item "DCM3_Pulmonary_35" (modified 2024-04-27; depositor not named on the page): one '
        'de-identified ECG-gated cardiac CTA ("CTA CARDIAC MORPHOLOGY", 35 % phase pulmonary-vein reconstruction, '
        'iDose 3), Philips iCT 256, 120 kV, kernel CA, 512x512x354, 0.383x0.383 mm, 0.8 mm slices every 0.4 mm. '
        'label.nii.gz = the released per-slice annotations (CVAT colour PNGs) converted to integer labels: '
        'see the labels field. Only the main series is stored (scouts, locators, bolus tracker skipped). '
        'The figshare file names are swapped (the "annotations" zip holds the DICOM).',
        'DCM3_Pulmonary_35. figshare dataset, private link https://figshare.com/s/caa70792c43ac01d8175 '
        '(CC BY 4.0).')
    case = 'DCM3_Pulmonary_35'
    if sink.done(case):
        return
    work = tempfile.mkdtemp(prefix='dcm3-', dir=args.work)
    try:
        dz, az = (io_.download(URL.format(f), os.path.join(work, n)) for f, n in ((DCM_FILE, 'd.zip'), (ANN_FILE, 'a.zip')))
        for z, d in ((dz, 'dcm'), (az, 'ann')):
            subprocess.run(['unzip', '-q', '-o', z, '-d', os.path.join(work, d)], check=True)
            os.remove(z)
        a, aff, uids, meta = load_series(os.path.join(work, 'dcm'))
        ct = io_.save_nifti(a, aff, os.path.join(work, 'ct.nii.gz'))
        names, cols = [], []
        for ln in open(os.path.join(work, 'ann', 'labelmap.txt')):
            if ln.startswith('#') or ':' not in ln:
                continue
            n, c = ln.split(':')[:2]
            names.append(n)
            cols.append(tuple(int(x) for x in c.split(',')))
        from PIL import Image
        lab = np.zeros(a.shape, np.uint8)
        found = 0
        for k, u in enumerate(uids):
            p = os.path.join(work, 'ann', 'SegmentationClass', u + '.png')
            if not os.path.exists(p):
                continue
            im = np.asarray(Image.open(p).convert('RGB'))
            s = np.zeros(im.shape[:2], np.uint8)
            for i, c in enumerate(cols):
                if i:
                    s[np.all(im == c, -1)] = i
            lab[:, :, k] = s.T                         # PNG (row, col) -> array (x=col, y=row)
            found += 1
        files = {'label.nii.gz': io_.save_nifti(lab, aff, os.path.join(work, 'label.nii.gz'))}
        labels = {str(i): n for i, n in enumerate(names) if i}
        extra = dict(source_ids={'figshare_private_link': PL, 'dicom_file_id': DCM_FILE, 'annotation_file_id': ANN_FILE},
                     ecg_gated=True, cardiac_phase='35 %', hu_calibrated=True, annotated_slices=found,
                     blood_pool_median_hu=io_.blood_pool_hu(ct), orientation_check=io_.anatomy_check(ct),
                     labels={'label.nii.gz': labels}, **meta)
        sink.put(case, ct, extra, files)
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
