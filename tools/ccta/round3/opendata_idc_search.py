"""OpenData round 3: re-search IDC (idc-index v25) for cardiac contrast CT missed in round 1, using
ScanOptions / pitch / kernel / ImageType / descriptions. Writes a candidate CSV."""
import sys, re
from idc_index import IDCClient
c = IDCClient()
for k in ('ct_index', 'contrast_index', 'collections_index'):
    c.fetch_index(k)
q = """
SELECT i.collection_id, i.PatientID, i.StudyInstanceUID, i.SeriesInstanceUID, i.StudyDescription, i.SeriesDescription,
 i.BodyPartExamined, i.Manufacturer, i.ManufacturerModelName, i.instanceCount, i.series_size_MB, i.license_short_name,
 i.series_init_idc_version, i.series_aws_url, i.PatientAge, i.PatientSex,
 ct.ScanOptions, ct.SliceThickness, ct.ConvolutionKernel, ct.SpiralPitchFactor, ct.ImageType, ct.ReconstructionDiameter,
 ct.ExposureTime_min, ct.KVP, cb.ContrastBolusAgent
FROM index i LEFT JOIN ct_index ct USING (SeriesInstanceUID) LEFT JOIN contrast_index cb USING (SeriesInstanceUID)
WHERE i.Modality='CT'
"""
df = c.sql_query(q)
df.to_parquet(sys.argv[1])
print(len(df))
