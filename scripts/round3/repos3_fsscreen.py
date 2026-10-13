"""Repos3: screen figshare/mendeley detail JSONL: imaging-like files or >30 MB, print summary lines."""
import json, re, sys
known = open(sys.argv[2]).read()
img = re.compile(r'\.(dcm|dicom|nii|gz|nrrd|mha|mhd|zip|tar|rar|7z|vti|vtk|npy|npz|h5|hdf5|raw|img|ima|mat)$', re.I)
skip = set(open(sys.argv[3]).read().split()) if len(sys.argv) > 3 else set()
for l in open(sys.argv[1]):
    r = json.loads(l)
    if str(r['id']) in skip: continue
    fs = r.get('files') or []
    tot = sum((x[1] or 0) for x in fs)
    imgf = [x[0] for x in fs if img.search(x[0] or '')]
    if not imgf and tot < 30e6: continue
    k = 'KNOWN ' if str(r['id']) in known else ''
    print(k + str(r['id']), '|', r.get('type', ''), '|', r.get('license'), '|', round(tot / 1e9, 2), 'GB', len(fs), 'f |', (r.get('title') or '')[:100], '|', ', '.join(imgf[:3])[:90])
