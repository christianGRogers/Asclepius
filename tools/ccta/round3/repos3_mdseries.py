"""Repos3: sample DICOM headers of a Mendeley record's files (range read 64 KB) and summarise series."""
import json, sys, io, os, collections, urllib.request, time
import pydicom
did = sys.argv[1]; n = int(sys.argv[2]) if len(sys.argv) > 2 else 40
with urllib.request.urlopen(urllib.request.Request(f'https://data.mendeley.com/public-api/datasets/{did}', headers={'User-Agent': 'curl/8.5.0'})) as r:
    d = json.load(r)
fs = d['files']; print('files', len(fs), 'folders?', len({f.get('folder_id') for f in fs}))
step = max(1, len(fs) // n)
ser = collections.Counter(); ex = {}
for f in fs[::step]:
    u = f['content_details']['download_url']
    try:
        with urllib.request.urlopen(urllib.request.Request(u, headers={'User-Agent': 'curl/8.5.0', 'Range': 'bytes=0-65535'}), timeout=60) as r:
            b = r.read()
        ds = pydicom.dcmread(io.BytesIO(b), stop_before_pixels=True, force=True)
        k = (str(getattr(ds, 'Modality', '')), str(getattr(ds, 'StudyDescription', '')), str(getattr(ds, 'ProtocolName', '')), str(getattr(ds, 'BodyPartExamined', '')), str(getattr(ds, 'ImageComments', ''))[:40], str(getattr(ds, 'SeriesDescription', '')), str(getattr(ds, 'SeriesNumber', '')), str(getattr(ds, 'ContrastBolusAgent', '')), str(getattr(ds, 'SliceThickness', '')), str(getattr(ds, 'ManufacturerModelName', '')))
        ser[k] += 1
    except Exception as e:
        ser[('ERR', type(e).__name__, f['filename'][:20])] += 1
    time.sleep(0.2)
for k, v in ser.most_common(): print(v, k)
