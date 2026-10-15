#!/usr/bin/env python3
"""Download the TotalSegmentator inputs (inputs.json: SegQueue/cases item ids) from Girder into <dest>/.

    python3 fetch.py <inputs.json> <dest>

Read-only on Girder. Authenticates with GIRDER_TOKEN, or GIRDER_USER + GIRDER_PASSWORD, or prompts once.
Resumable: a file already present at the right size is skipped; downloads go to a .part file renamed when
complete. Standard library only (runs with the login node's python before any venv exists).
"""
import base64, concurrent.futures as cf, getpass, json, os, sys, time, urllib.parse, urllib.request

API = os.environ.get('GIRDER_API', 'https://janus.bradensbay.com/api/v1')
THREADS = int(os.environ.get('FETCH_THREADS', 8))


def call(path, token=None, auth=None):
    req = urllib.request.Request(f'{API}/{path}')
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


def fetch(token, item, dest):
    if os.path.exists(dest) and os.path.getsize(dest) == item['size']:
        return 0
    tmp = dest + '.part'
    for attempt in range(6):
        try:
            req = urllib.request.Request(f'{API}/item/{item["item_id"]}/download')
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
            print(f'retry {attempt + 1}/6 {item["name"]}: {e}', file=sys.stderr, flush=True)
            time.sleep(2 ** attempt)
    raise SystemExit(f'failed to download {item["name"]}')


def main():
    items = json.load(open(sys.argv[1]))
    out = os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    todo = [i for i in items if not (os.path.exists(os.path.join(out, i['name']))
                                     and os.path.getsize(os.path.join(out, i['name'])) == i['size'])]
    print(f'[fetch] {len(items)} volumes, {len(todo)} to download '
          f'({sum(i["size"] for i in todo) / 1e9:.1f} GB) -> {out}', flush=True)
    if not todo:
        return
    token = login()
    done, t0 = 0, time.time()
    with cf.ThreadPoolExecutor(THREADS) as ex:
        futs = [ex.submit(fetch, token, i, os.path.join(out, i['name'])) for i in todo]
        for k, f in enumerate(cf.as_completed(futs), 1):
            done += f.result()
            if k % 25 == 0 or k == len(futs):
                rate = done / max(time.time() - t0, 1) / 1e6
                print(f'[fetch]   {k}/{len(futs)} files, {done / 1e9:.1f} GB, {rate:.0f} MB/s', flush=True)
    print('[fetch] complete', flush=True)


if __name__ == '__main__':
    main()
