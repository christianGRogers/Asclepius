"""Repos3: screen zenodo.jsonl harvest -> candidates (cardiac + CT words, not known)."""
import json, re, sys
known = open(sys.argv[2]).read()
seen_out = set(open(sys.argv[3]).read().split()) if len(sys.argv) > 3 else set()
card = re.compile(r'coronar|cardi|heart|aort|atri(al|um)|ventric|valv|TAVI|TAVR|LAA|appendage|myocard|pericard|epicard|CCTA|FFR|congenital|mitral|tricusp|pulmonary vein|fistula', re.I)
ct = re.compile(r'\bCT\b|CTA|CCTA|computed tomograph|DICOM|\.nii|nrrd|tomograf', re.I)
img = re.compile(r'\.(dcm|nii|nii\.gz|nrrd|mha|mhd|zip|tar|gz|rar|7z|vti|npy|npz|h5|hdf5|raw|img)$', re.I)
for l in open(sys.argv[1]):
    r = json.loads(l)
    t = (r['title'] or '') + ' ' + re.sub('<[^>]+>', ' ', r.get('desc') or '')
    if not (card.search(t) and ct.search(t)): continue
    if r['id'] in seen_out: continue
    fs = r.get('files') or []
    big = sum((s or 0) for _, s in fs)
    imgf = [n for n, s in fs if img.search(n or '')]
    print(('KNOWN ' if r['id'] in known else '') + r['id'], '|', r.get('rtype'), r.get('access'), r.get('license'), '|', round(big / 1e9, 2), 'GB', len(fs), 'f |', (r['title'] or '')[:110], '|', ', '.join(imgf[:3])[:80])
