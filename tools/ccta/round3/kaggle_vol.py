"""From probe jsonl files, print datasets containing 3D-volume-like files (nii/dcm/nrrd/mhd/mha/vti/npz/h5/zip/no-ext)."""
import json, sys, glob
VOLX = {'.nii', '.nii.gz', '.dcm', '.nrrd', '.seg.nrrd', '.mhd', '.mha', '.raw', '.vti', '.ima', '.img', '.hdr', '(none)', '.zip', '.7z', '.rar', '.gz', '.tar', '.npz', '.npy', '.h5', '.hdf5', '.zarr', '.dicom'}
skip = set(open(sys.argv[1]).read().split()) if len(sys.argv) > 1 else set()
for f in sorted(glob.glob('probe*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if r['ref'] in skip: continue
        v = {k: n for k, n in r['ext'].items() if k in VOLX}
        if v and sum(v.values()) >= 1:
            print(f"{r['ref']:65s} n={r['n']}{'+' if r['more'] else ''} {v} {r['sample'][:3]}"[:300])
