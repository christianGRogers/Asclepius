"""Repos3: one Zenodo query (all types), all pages; prints id | type | access | licence | title | n files | total size."""
import json, sys, time, urllib.parse, urllib.request
q = sys.argv[1]; extra = dict(a.split('=', 1) for a in sys.argv[2:])
page = 1
while True:
    for a in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request('https://zenodo.org/api/records?' + urllib.parse.urlencode(dict({'q': q, 'size': 25, 'page': page}, **extra)), headers={'User-Agent': 'curl/8.5.0'}), timeout=120) as r:
                d = json.load(r); break
        except Exception as e:
            time.sleep(5 * (a + 1)); d = None
    if not d: break
    hh = d['hits']['hits']
    for h in hh:
        m = h['metadata']; fs = h.get('files', [])
        print(h['id'], '|', m.get('resource_type', {}).get('type'), '|', m.get('access_right'), '|', (m.get('license') or {}).get('id'), '|', m.get('title', '')[:110], '|', len(fs), '|', round(sum(f.get('size', 0) for f in fs) / 1e9, 2), 'GB |', ', '.join(f['key'] for f in fs[:4])[:120])
    if page * 25 >= min(d['hits']['total'], 10000) or not hh: break
    page += 1; time.sleep(0.8)
print('# total', d and d['hits']['total'], file=sys.stderr)
