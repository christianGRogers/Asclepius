import json, re, sys
seen = set(open(sys.argv[2]).read().split()) if len(sys.argv) > 2 else set()
for l in open(sys.argv[1]):
    x = json.loads(l); t = (x['title'] or '') + ' | ' + (x['subtitle'] or '')
    if x['ref'] in seen: continue
    if re.search(r'heart|cardi|coronar|aort|ccta|cta\b|angio|vessel|whs|asoca|imagecas|\bcas\b|valve|ventric|atri[au]|calcium|plaque|chd|tavi|tavr|epicard|pericard|myocard|herz|coeur|corazon|kalp|jantung|心|冠', t, re.I) \
       and (x['totalBytes'] or 0) > 20e6 and not re.search(r'\bmri\b|echo|ecg|ekg|x-ray|xray|retina|fundus|sound|pcg|phonocard|disease prediction|failure prediction|tabular|csv', t, re.I):
        print(f"{x['ref']:70s} {x['totalBytes']/1e9:6.2f}GB {(x['licenseName'] or '')[:18]:18s} {t[:120]}")
