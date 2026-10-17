"""Peek at one Kaggle dataset member: download it (into a fresh work dir), print DICOM tags or a volume
report (+ preview PNG). Usage: kaggle_peek.py <workdir> <ref> <member> [--nohu]"""
import os, sys, json, shutil
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import ingest_open as io_
import kaggle_common as kc
work, ref, member = sys.argv[1:4]
hu = '--nohu' not in sys.argv
os.makedirs(work, exist_ok=True)
dst = os.path.join(work, os.path.basename(member) or 'file')
kc.fetch(ref, member, dst)
print('size', os.path.getsize(dst))
low = dst.lower()
if low.endswith('.dcm') or '.' not in os.path.basename(low):
    import pydicom
    d = pydicom.dcmread(dst, force=True, stop_before_pixels=True)
    for k in ('Modality', 'Manufacturer', 'ManufacturerModelName', 'StudyDescription', 'SeriesDescription', 'BodyPartExamined',
              'ProtocolName', 'ContrastBolusAgent', 'SliceThickness', 'PixelSpacing', 'Rows', 'Columns', 'KVP',
              'ConvolutionKernel', 'ImageType', 'CardiacNumberOfImages', 'NominalPercentageOfCardiacPhase',
              'PatientIdentityRemoved', 'DeidentificationMethod', 'InstitutionName', 'ImageComments', 'StudyDate'):
        v = d.get(k)
        if v is not None:
            print(f'{k}: {str(v)[:120]}' if k not in ('StudyDate', 'InstitutionName') else f'{k}: <present>')
else:
    if low.endswith('.nii'):
        shutil.move(dst, dst + '.gz') if False else None
    import nibabel as nib, SimpleITK as sitk
    path = dst
    if not (low.endswith('.nii') or low.endswith('.nii.gz')):
        path = dst + '.nii.gz'; sitk.WriteImage(sitk.ReadImage(dst), path)
    print(json.dumps(io_.report(path, hu, os.path.join(work, 'peek.png')), indent=0))
