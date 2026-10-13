"""Repos3: screen detail JSONL (figshare or mendeley) by cardiac+CT words in title/description and imaging files."""
import json, re, sys
known = open(sys.argv[2]).read()
skip = set(open(sys.argv[3]).read().split()) if len(sys.argv) > 3 else set()
card = re.compile(r'coronar|cardi|heart|aort|atri(al|um)|ventric|valv|TAVI|TAVR|appendage|myocard|pericard|epicard|CCTA|congenital|mitral|fistula', re.I)
ct = re.compile(r'\bCT\b|CTA|computed tomograph|DICOM|tomograf|\bnii\b|nrrd', re.I)
img = re.compile(r'\.(dcm|ima|nii|gz|nrrd|mha|mhd|zip|rar|7z|tar|raw)$|^\d{6,}$|^[0-9A-F]{8}$|^IM', re.I)
bad = re.compile(r'mouse|mice|\brat\b|zebrafish|porcine|swine|rabbit|murine|canine|X-ray angiograph|ECG|echocardiograph|MRI\b|magnetic resonance', re.I)
seen = set()
for l in open(sys.argv[1]):
    r = json.loads(l); i = str(r['id'])
    if i in seen or i in skip: continue
    seen.add(i)
    t = (r.get('title') or '') + ' ' + re.sub('<[^>]+>', ' ', r.get('desc') or '')
    if not (card.search(t) and ct.search(t)) or bad.search(r.get('title') or ''): continue
    if r.get('type') == 'media': continue
    fs = r.get('files') or []; tot = sum((x[1] or 0) for x in fs)
    imgf = [x[0] for x in fs if img.search(x[0] or '')]
    if tot < 20e6 and not imgf: continue
    print(('KNOWN ' if i in known else '') + i, '|', r.get('license'), '|', round(tot / 1e6), 'MB', len(fs), '|', (r.get('title') or '')[:100], '|', ', '.join(imgf[:3])[:60])
