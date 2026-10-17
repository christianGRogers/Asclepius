"""Select Kaggle search hits worth a file-list probe (cardiac/vascular/CT-volume words, >30 MB)."""
import json, re, sys, glob
probed = set()
for f in glob.glob('probe*.jsonl'):
    for l in open(f): probed.add(json.loads(l)['ref'])
CARD = r'heart|cardi|coronar|aort|ccta|\bcta\b|angio|vessel|vascul|whs|asoca|valve|ventric|atrium|atrial|calcium|plaque|\bchd\b|tavi\b|tavr|epicard|pericard|myocard|herz|coeur|coraz|kalp|jantung|心|冠|thora|chest|mediastin'
VOL = r'\bct\b|\bcts\b|computed tomograph|dicom|\bdcm\b|nifti|\bnii\b|nrrd|\bmhd\b|3d|volum|segment|totalseg|whole.?body|multi.?organ|organ'
seen = set()
for f in sys.argv[1:]:
    for l in open(f):
        x = json.loads(l)
        if x['ref'] in seen or x['ref'] in probed: continue
        seen.add(x['ref'])
        t = (x['title'] or '') + ' ' + (x['subtitle'] or '') + ' ' + x['ref']
        if (x['totalBytes'] or 0) < 30e6: continue
        if re.search(r'\bmri\b|\bmr\b|echo|ecg|ekg|x-?ray|cxr|retina|fundus|sound|pcg|murmur|stroke pred|tabular|csv|hearthstone|heartbeat|cardiomegaly|vinbig', t, re.I): continue
        if re.search(CARD, t, re.I) or (re.search(VOL, t, re.I) and (x['totalBytes'] or 0) > 300e6):
            print(x['ref'])
