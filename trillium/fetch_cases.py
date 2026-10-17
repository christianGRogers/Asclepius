#!/usr/bin/env python3
"""Download the 1000 SegQueue cases from Girder into the layout the experiments expect.

    python3 fetch_cases.py <dest>/cases

Writes <dest>/cases/c0000/ct.nii.gz + coronary_arteries.nii.gz ... c0999/, the Girder export
layout of trillium/README.md. Case ids follow the tournament's numbering: the cases are paired
and ordered by upload time, which makes cNNNN = ImageCAS case NNNN+1 (vault note "Crucible -
ImageCAS-X is real and its 800 cases are our cases c(id-1)").

Read-only on Girder. Authenticates with GIRDER_TOKEN, or GIRDER_USER + GIRDER_PASSWORD, or
prompts once. Resumable: a file already present at the right size is skipped, and downloads go
to a .part file renamed when complete, so an interrupted run can simply be started again.
Standard library only.
"""
import base64
import bisect
import concurrent.futures as cf
import getpass
import json
import os
import sys
import time
import urllib.parse
import urllib.request

API = os.environ.get('GIRDER_API', 'https://janus.bradensbay.com/api/v1')
COLLECTION = 'SegQueue'
FOLDER = 'cases'
THREADS = int(os.environ.get('FETCH_THREADS', 8))


def call(path, token=None, auth=None, params=None):
    url = f'{API}/{path}' + ('?' + urllib.parse.urlencode(params) if params else '')
    req = urllib.request.Request(url)
    if token:
        req.add_header('Girder-Token', token)
    if auth:
        req.add_header('Authorization', 'Basic ' + base64.b64encode(auth.encode()).decode())
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.load(r)


def login():
    if os.environ.get('GIRDER_TOKEN'):
        return os.environ['GIRDER_TOKEN']
    user = os.environ.get('GIRDER_USER') or input('Girder username: ')
    pw = os.environ.get('GIRDER_PASSWORD') or getpass.getpass(f'Girder password for {user}: ')
    return call('user/authentication', auth=f'{user}:{pw}')['authToken']['token']


def list_cases(token):
    folder = call('resource/lookup', token, params={'path': f'/collection/{COLLECTION}/{FOLDER}'})
    items = call('item', token, params={'folderId': folder['_id'], 'limit': 0})
    items.sort(key=lambda i: i['created'])
    cts = [i for i in items if i['name'].startswith('ct')]
    masks = [i for i in items if i['name'].startswith('coronary')]
    times = [m['created'] for m in masks]
    pairs, used = [], set()
    for ct in cts:  # each CT is uploaded just before its own mask
        j = bisect.bisect_left(times, ct['created'])
        if j >= len(masks) or j in used:
            sys.exit(f'cannot pair {ct["name"]} ({ct["_id"]}) with a mask; refusing to guess')
        used.add(j)
        pairs.append((ct, masks[j]))
    if len(pairs) != 1000:
        print(f'warning: expected 1000 cases, found {len(pairs)}', file=sys.stderr)
    return pairs


def fetch(token, item, dest):
    if os.path.exists(dest) and os.path.getsize(dest) == item['size']:
        return 0
    tmp = dest + '.part'
    for attempt in range(5):
        try:
            req = urllib.request.Request(f'{API}/item/{item["_id"]}/download')
            req.add_header('Girder-Token', token)
            with urllib.request.urlopen(req, timeout=600) as r, open(tmp, 'wb') as f:
                while True:
                    b = r.read(1 << 22)
                    if not b:
                        break
                    f.write(b)
            if os.path.getsize(tmp) != item['size']:
                raise IOError(f'size {os.path.getsize(tmp)} != {item["size"]}')
            os.replace(tmp, dest)
            return item['size']
        except Exception as e:  # noqa: BLE001 - retry any transfer failure
            print(f'retry {attempt + 1}/5 {dest}: {e}', file=sys.stderr)
            time.sleep(2 ** attempt)
    raise SystemExit(f'failed to download {dest}')


def main():
    out = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else 'cases')
    token = login()
    pairs = list_cases(token)
    jobs = []
    for n, (ct, mask) in enumerate(pairs):
        d = os.path.join(out, f'c{n:04d}')
        os.makedirs(d, exist_ok=True)
        jobs += [(ct, os.path.join(d, 'ct.nii.gz')), (mask, os.path.join(d, 'coronary_arteries.nii.gz'))]
    json.dump([{'case': f'c{n:04d}', 'ct_id': c['_id'], 'mask_id': m['_id']} for n, (c, m) in enumerate(pairs)],
              open(os.path.join(out, 'cases.json'), 'w'), indent=0)
    total = sum(i['size'] for i, _ in jobs)
    print(f'{len(pairs)} cases, {total / 1e9:.1f} GB -> {out}', flush=True)
    done, t0 = 0, time.time()
    with cf.ThreadPoolExecutor(THREADS) as ex:
        futs = [ex.submit(fetch, token, i, d) for i, d in jobs]
        for k, f in enumerate(cf.as_completed(futs), 1):
            done += f.result()
            if k % 50 == 0 or k == len(futs):
                rate = done / max(time.time() - t0, 1) / 1e6
                print(f'  {k}/{len(futs)} files, {done / 1e9:.1f} GB new, {rate:.0f} MB/s', flush=True)
    print('cases complete', flush=True)


if __name__ == '__main__':
    main()
