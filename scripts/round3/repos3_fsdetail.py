"""Repos3: fetch figshare article details (files, licence, description, authors) for ids on stdin -> JSONL."""
import json, sys, time, urllib.request, os
out = sys.argv[1]; seen = set()
if os.path.exists(out):
    seen = {json.loads(l)['id'] for l in open(out)}
f = open(out, 'a')
import threading, queue
Q = queue.Queue(); L = threading.Lock()
for line in sys.stdin:
    i = line.strip()
    if i and int(i) not in seen: Q.put(i)
def work():
  while True:
    try: i = Q.get_nowait()
    except queue.Empty: return
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(f'https://api.figshare.com/v2/articles/{i}', headers={'User-Agent': 'curl/8.5.0'}), timeout=60) as r:
                d = json.load(r); break
        except Exception as e:
            d = None; time.sleep(5 * (a + 1))
    if d:
      with L:
        f.write(json.dumps({'id': d['id'], 'title': d.get('title'), 'type': d.get('defined_type_name'), 'url': d.get('url_public_html'),
            'license': (d.get('license') or {}).get('name'), 'desc': (d.get('description') or '')[:3000],
            'authors': [(a.get('full_name'), a.get('id')) for a in d.get('authors', [])][:10], 'group': d.get('group_id'),
            'files': [(x.get('name'), x.get('size'), x.get('id')) for x in d.get('files', [])][:300],
            'tags': d.get('tags'), 'related': [r.get('link') for r in d.get('related_materials', [])][:30],
            'restricted': d.get('is_embargoed') or bool(d.get('embargo_type')), 'resource_doi': d.get('resource_doi')}) + '\n'); f.flush()
    time.sleep(0.3)
T = [threading.Thread(target=work) for _ in range(4)]
[t.start() for t in T]; [t.join() for t in T]
