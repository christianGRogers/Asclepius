"""Ingest the IDC cardiac CT series (sourcing/IDC_T1T2_series.csv, found by the IDC sourcing agent) into
CCTA-Pool/IDC-<collection>/. One series at a time: s5cmd download (no login) -> dcm2niix -> every 3D volume
with >= 40 slices becomes a case (multi-phase series give one case per phase, suffix _pNN) -> upload -> delete.
Usage: GIRDER_TOKEN_FILE=... ingest_idc.py <series.csv> <tmpdir>"""
import csv, glob, os, re, shutil, subprocess, sys
import nibabel as nib, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from ccta_ingest import Pool

S5 = os.path.join(os.path.dirname(__import__('s5cmd').__file__), 'bin', 's5cmd')
CITE = {'rider_lung_pet_ct': 'https://doi.org/10.7937/k9/tcia.2015.ofip7tvm',
        'nsclc_radiogenomics': 'https://doi.org/10.7937/K9/TCIA.2017.7hs46erv',
        'varepop_apollo': 'https://www.cancerimagingarchive.net/collection/varepop-apollo/',
        'tcga_ov': 'https://doi.org/10.7937/K9/TCIA.2016.NDO1MDFQ'}
TIER = {'rider_lung_pet_ct': 'T1/T2', 'nsclc_radiogenomics': 'T2', 'varepop_apollo': 'T2', 'tcga_ov': 'T2'}


def slug(s):
    return re.sub(r'[^A-Za-z0-9]+', '-', s).strip('-')[:40]


def volumes(nii_dir, out_dir):
    """Every 3D volume (4D files split along the last axis) with >= 40 slices, largest first."""
    vols = []
    for f in sorted(glob.glob(os.path.join(nii_dir, '*.nii.gz'))):
        im = nib.load(f)
        if im.ndim == 3 and im.shape[2] >= 40:
            vols.append(f)
        elif im.ndim == 4:
            a = np.asarray(im.dataobj)
            for t in range(a.shape[3]):
                if a.shape[2] >= 40:
                    p = os.path.join(out_dir, f'{os.path.basename(f)[:-7]}_t{t:02d}.nii.gz')
                    nib.save(nib.Nifti1Image(a[..., t], im.affine, im.header), p)
                    vols.append(p)
    return vols


def main(csv_path, tmp):
    rows = list(csv.DictReader(open(csv_path)))
    pool = Pool()
    for coll in sorted({r['collection_id'] for r in rows}):
        pool.dataset(f'IDC-{coll}', licence=rows[[r['collection_id'] for r in rows].index(coll)]['license_short_name'],
                     tier=TIER.get(coll, 'T2'), source_url=CITE.get(coll, 'https://portal.imaging.datacommons.cancer.gov'),
                     description=f'Incidental cardiac CT from TCIA/IDC collection {coll} (found by idc-index search; '
                                 f'cite the collection DOI and IDC). Not designed as a cardiac dataset.')
    for r in rows:
        ds, base = f'IDC-{r["collection_id"]}', f'{r["PatientID"]}__{slug(r["SeriesDescription"])}_{r["SeriesInstanceUID"][-6:]}'
        if pool.case_done(ds, base) or pool.case_done(ds, base + '_p00'):
            print('exists', base, flush=True); continue
        dcm, nii = os.path.join(tmp, 'dcm'), os.path.join(tmp, 'nii')
        shutil.rmtree(tmp, ignore_errors=True); os.makedirs(dcm); os.makedirs(nii)
        try:
            subprocess.run([S5, '--no-sign-request', '--endpoint-url', 'https://s3.amazonaws.com', 'cp',
                            r['series_aws_url'], dcm + '/'], check=True, stdout=subprocess.DEVNULL)
            subprocess.run(['dcm2niix', '-z', 'y', '-b', 'n', '-o', nii, '-f', 'v_%s_%t', dcm], check=False,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            shutil.rmtree(dcm)
            vols = volumes(nii, nii)
            extra = {'patient_id': r['PatientID'], 'study_uid': r['StudyInstanceUID'], 'series_uid': r['SeriesInstanceUID'],
                     'series_description': r['SeriesDescription'], 'study_description': r['StudyDescription'],
                     'patient_age': r['PatientAge'], 'patient_sex': r['PatientSex'], 'idc_collection': r['collection_id']}
            for k, v in enumerate(vols):
                case = base if len(vols) == 1 else f'{base}_p{k:02d}'
                print(pool.ingest(ds, case, v, dict(extra, phase_index=k, n_phases=len(vols))), case, flush=True)
            if not vols:
                print('no 3D volume >= 40 slices in', base, flush=True)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
