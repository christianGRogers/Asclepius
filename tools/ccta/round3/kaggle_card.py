import json, re, glob, sys
T = {}
for f in glob.glob('hits*.jsonl'):
    for l in open(f):
        x = json.loads(l); T[x['ref']] = x
CARD = re.compile(r'heart|cardi|coronar|aort|ccta|\bcta\b|angio|vessel|vascul|whs|asoca|valve|ventric|atri(um|al)|calcium|plaque|\bchd\b|tavi\b|tavr|epicard|pericard|myocard|\blv\b|\brv\b|\bla\b|\bra\b|lad|rca|lcx|herz|coeur|coraz|kalp|jantung|心|冠|gated|ecg|cine|phase', re.I)
VOLX = {'.nii', '.nii.gz', '.dcm', '.nrrd', '.seg.nrrd', '.mhd', '.mha', '.raw', '.vti', '.ima', '.img', '.hdr', '(none)', '.zip', '.7z', '.rar', '.gz', '.tar', '.npz', '.npy', '.h5', '.hdf5', '.dicom', '.mrb'}
skip = set(open(sys.argv[1]).read().split()) if len(sys.argv) > 1 else set()
for f in sorted(glob.glob('probe*.jsonl')):
    for l in open(f):
        r = json.loads(l)
        if r['ref'] in skip or not any(k in VOLX for k in r['ext']): continue
        x = T.get(r['ref'], {})
        t = (x.get('title') or '') + ' ' + (x.get('subtitle') or '') + ' ' + r['ref'] + ' ' + ' '.join(r['sample'])
        if CARD.search(t):
            print(f"{r['ref']:60s} {(x.get('totalBytes') or 0)/1e9:6.2f}GB {(x.get('licenseName') or '')[:12]:12s} {r['ext']} | {x.get('title')} | {r['sample'][:2]}"[:260])
