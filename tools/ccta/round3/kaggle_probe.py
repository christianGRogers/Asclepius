"""Summarise Kaggle dataset file lists (extension counts + sample names) for a list of refs. Appends to jsonl."""
import json, sys, time, urllib.request, urllib.parse, collections, os, re
OUT = sys.argv[1]; refs = [l.split()[0] for l in open(sys.argv[2]) if l.strip() and not l.startswith('#')]
done = set()
if os.path.exists(OUT):
    for l in open(OUT): done.add(json.loads(l)['ref'])
def get(url):
    for a in range(3):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'curl/8.5.0'}), timeout=20) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code == 429: time.sleep(30); continue
            if e.code >= 500: time.sleep(5); continue
            return {'error': e.code}
        except Exception: time.sleep(5)
    return {'error': 'fail'}
with open(OUT, 'a') as o:
    for ref in refs:
        if ref in done: continue
        files, tok, pages = [], '', 0
        while pages < int(os.environ.get("PROBE_PAGES", "2")):
            d = get(f'https://www.kaggle.com/api/v1/datasets/list/{ref}?pageSize=200' + (f'&pageToken={tok}' if tok else ''))
            if 'error' in d: break
            files += d.get('datasetFiles') or []; pages += 1
            tok = d.get('nextPageToken')
            if not tok: break
        ext = collections.Counter()
        for f in files:
            n = f['name'].lower()
            m = re.search(r'(\.nii\.gz|\.seg\.nrrd|\.[a-z0-9]{1,10})$', n)
            ext[m.group(1) if m else '(none)'] += 1
        rec = dict(ref=ref, n=len(files), more=bool(tok), ext=dict(ext.most_common(8)),
                   sample=[f['name'] for f in files[:6]] + ([f['name'] for f in files[-3:]] if len(files) > 6 else []),
                   err=d.get('error') if isinstance(d, dict) else None)
        o.write(json.dumps(rec) + '\n'); o.flush()
        print(ref, rec['n'], rec['ext'], rec['sample'][:4], flush=True)
        time.sleep(0.1)
