"""Kaggle anonymous dataset search harvester (round 3, agent Kaggle). Appends unique datasets to a jsonl."""
import json, sys, time, urllib.parse, urllib.request, os
OUT = sys.argv[1]
queries = [l.strip() for l in open(sys.argv[2]) if l.strip()] or [""]
extra = sys.argv[3] if len(sys.argv) > 3 else ''
seen = set()
if os.path.exists(OUT):
    for l in open(OUT):
        seen.add(json.loads(l)['ref'])
done_q = OUT + '.queries'
dq = set(open(done_q).read().split('\n')) if os.path.exists(done_q) else set()
def get(url):
    for a in range(5):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'curl/8.5.0'}), timeout=60) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(30); continue
            if e.code >= 500: time.sleep(5); continue
            print('ERR', e.code, url, file=sys.stderr); return []
        except Exception as e:
            time.sleep(5)
    return []
with open(OUT, 'a') as o, open(done_q, 'a') as dqf:
    for q in queries:
        key = q + '|' + extra
        if key in dq: continue
        new = 0
        for page in range(1, 500):
            d = get(f'https://www.kaggle.com/api/v1/datasets/list?search={urllib.parse.quote(q)}&page={page}{extra}')
            if not d: break
            for x in d:
                if x['ref'] in seen: continue
                seen.add(x['ref']); new += 1
                o.write(json.dumps({k: x.get(k) for k in ('ref', 'title', 'subtitle', 'totalBytes', 'licenseName', 'lastUpdated', 'downloadCount', 'ownerRef')} | {'q': q}) + '\n')
            o.flush()
            if len(d) < 20: break
            time.sleep(0.3)
        print(f'{q!r}: +{new}', flush=True)
        dqf.write(key + '\n'); dqf.flush()
