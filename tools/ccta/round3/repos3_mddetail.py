"""Repos3: Mendeley Data public-api details for ids on stdin -> JSONL (files, sizes, licence, description)."""
import json, sys, time, urllib.request, os
out = sys.argv[1]; seen = set()
if os.path.exists(out):
    seen = {json.loads(l)['id'] for l in open(out)}
f = open(out, 'a')
for line in sys.stdin:
    i = line.strip()
    if not i or i in seen: continue
    seen.add(i); d = None
    for a in range(4):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://data.mendeley.com/public-api/datasets/{i}', headers={'User-Agent': 'curl/8.5.0'}), timeout=60) as r:
                d = json.load(r); break
        except urllib.error.HTTPError as e:
            d = {'error': e.code}; break
        except Exception:
            time.sleep(5 * (a + 1))
    if d is None: continue
    files = [(x.get('filename'), (x.get('content_details') or {}).get('size'), (x.get('content_details') or {}).get('download_url')) for x in d.get('files', [])] if 'files' in d else []
    f.write(json.dumps({'id': i, 'title': d.get('name'), 'license': (d.get('data_licence') or {}).get('short_name') if isinstance(d.get('data_licence'), dict) else d.get('data_licence'),
                        'desc': (d.get('description') or '')[:3000], 'files': files[:400], 'nfiles': len(files),
                        'size': sum((s or 0) for _, s, _ in files), 'error': d.get('error'),
                        'owner_id': d.get('owner_id'), 'contributors': [c.get('first_name', '') + ' ' + c.get('last_name', '') for c in d.get('contributors', [])][:8],
                        'related': [x.get('href') for x in d.get('related_links', [])][:20] if isinstance(d.get('related_links'), list) else None}) + '\n'); f.flush()
    time.sleep(0.7)
