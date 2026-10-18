#!/usr/bin/env python3
"""Download the 1000 ImageCAS CTs from Girder (D22 layout) into the layout the experiments expect.

    python3 fetch_cases.py <dest>/cases            # CTs only (~91 GB): what icx4 needs
    python3 fetch_cases.py --masks <dest>/cases    # also the original ImageCAS binary masks

Writes <dest>/cases/c0000/ct.nii.gz ... c0999/ct.nii.gz (with --masks also coronary_arteries.nii.gz
beside each), plus <dest>/cases/cases.json (case -> ImageCAS id, Girder folder and item ids).
ImageCAS id n is case c{n-1:04d}. Since D22 the ImageCAS volumes sit in two folders (see GIRDER LAYOUT
below): the 800 ImageCAS-X cases in ImageCAS-X/cases and the 200 unlabelled ones in SegQueue/cases,
beside the CCTA-Pool volumes, which are skipped. The run refuses unless the two folders give exactly
ImageCAS ids 1-1000, each once.

Read-only on Girder. Authenticates with GIRDER_TOKEN, or GIRDER_USER + GIRDER_PASSWORD, or prompts
once. Resumable: a file already present at the right size is skipped, and downloads go to a .part
file (<file>.part.<pid>) renamed when complete, so an interrupted run can simply be started again. One
fetch at a time per cases/: an exclusive lock on cases/.fetch.lock refuses a second run (#82). Ends with a verdict
("1000 of 1000 CTs complete", or what is missing or partial and how to resume) and exits non-zero
unless every file is complete (#82). Standard library only.
"""
import argparse
import base64
import concurrent.futures as cf
import errno
import fcntl
import getpass
import glob
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request

API = os.environ.get('GIRDER_API', 'https://janus.bradensbay.com/api/v1')
THREADS = int(os.environ.get('FETCH_THREADS', 8))

# ---- GIRDER LAYOUT (D22; folder and item names verified on janus by the PM, 2026-10-18, issue #79) ----
# (Girder path, number of ImageCAS ids it must hold). Each item holds one file with the item's name.
FOLDERS = (
    ('/collection/ImageCAS-X/cases', 800),   # ImageCAS-X's 800 cases (CT + original mask)
    ('/collection/SegQueue/cases', 200),     # the 200 unlabelled ImageCAS cases; every other item is skipped
)
CT_NAME = re.compile(r'ImageCAS__(\d{4})\.nii\.gz')            # the CT, 4-digit 1-based ImageCAS id
MASK_NAME = re.compile(r'ImageCAS__(\d{4})__mask\.nii\.gz')    # the original ImageCAS binary mask
N_CASES = 1000
# ------------------------------------------------------------------------------------------------------


class LayoutError(SystemExit):
    """Girder does not hold exactly what GIRDER LAYOUT describes; nothing is downloaded."""


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


def scan_folder(items, where):
    """{ImageCAS id: {'ct': item, 'mask': item or None}} from one folder's items, and the skip count."""
    found, skipped = {}, 0
    for it in items:
        for kind, rx in (('ct', CT_NAME), ('mask', MASK_NAME)):
            m = rx.fullmatch(it['name'])
            if m:
                break
        else:
            skipped += 1   # a pool volume (ImageCHD__..., CCA200-HF__...) or anything else
            continue
        n = int(m.group(1))
        entry = found.setdefault(n, {'ct': None, 'mask': None, 'folder': where})
        if entry[kind] is not None:
            raise LayoutError(f'{where}: two items named {it["name"]} ({entry[kind]["_id"]}, {it["_id"]}); '
                              'refusing to guess')
        entry[kind] = it
    no_ct = sorted(n for n, e in found.items() if e['ct'] is None)
    if no_ct:
        raise LayoutError(f'{where}: {len(no_ct)} ImageCAS mask(s) without a CT, e.g. ids {no_ct[:5]}')
    return found, skipped


def list_cases(token, masks=False):
    """{ImageCAS id: {'ct', 'mask', 'folder'}} for exactly ids 1..1000, or LayoutError."""
    cases = {}
    for path, expect in FOLDERS:
        folder = call('resource/lookup', token, params={'path': path})
        items = call('item', token, params={'folderId': folder['_id'], 'limit': 0})
        found, skipped = scan_folder(items, path)
        print(f'{path}: {len(found)} ImageCAS ids ({len(items)} items, {skipped} other volumes skipped)',
              flush=True)
        if len(found) != expect:
            raise LayoutError(f'{path}: expected {expect} ImageCAS ids, found {len(found)}; refusing')
        both = sorted(set(found) & set(cases))
        if both:
            raise LayoutError(f'ImageCAS ids in more than one folder, e.g. {both[:5]}; refusing to guess')
        cases.update(found)
    if set(cases) != set(range(1, N_CASES + 1)):
        bad = sorted(set(cases) ^ set(range(1, N_CASES + 1)))
        raise LayoutError(f'the ImageCAS ids are not exactly 1-{N_CASES} ({len(cases)} found; '
                          f'off by e.g. {bad[:5]}); refusing')
    if masks:
        no_mask = sorted(n for n, e in cases.items() if e['mask'] is None)
        if no_mask:
            raise LayoutError(f'--masks: {len(no_mask)} case(s) have no __mask item, e.g. ids {no_mask[:5]}')
    return cases


LOCK_NAME = '.fetch.lock'


def lock(out):
    """Hold an exclusive lock on out/.fetch.lock for the life of the process, or refuse (#82)."""
    path = os.path.join(out, LOCK_NAME)
    f = open(path, 'a+')
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        f.seek(0)
        holder = f.read().strip() or '?'
        f.close()
        raise SystemExit(f'another fetch_cases.py (pid {holder}) is already filling {out} (it holds {path}); '
                         'refusing to race it. Wait for it, or stop it, then re-run to resume.') from None
    except OSError as e:
        if e.errno not in (errno.ENOSYS, errno.EOPNOTSUPP, errno.ENOLCK):
            raise
        print(f'WARNING: this file system does not support locks ({path}: {e}); '
              'make sure no other fetch_cases.py is filling this cases/', file=sys.stderr, flush=True)
    f.seek(0)
    f.truncate()
    f.write(f'{os.getpid()}\n')
    f.flush()
    return f   # the caller keeps it open: closing it (or exiting) releases the lock


def fetch(token, item, dest):
    if os.path.exists(dest) and os.path.getsize(dest) == item['size']:
        return 0
    tmp = f'{dest}.part.{os.getpid()}'   # per process, so no other writer can rename or delete ours (#82)
    for stale in glob.glob(glob.escape(dest) + '.part*'):
        if stale != tmp:   # left by an interrupted run; we hold the lock, so nobody else is writing it
            os.remove(stale)
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


def plan(cases, out, masks=False):
    """[(item, dest path)] and the cases.json rows."""
    jobs, rows = [], []
    for n in sorted(cases):
        e, c = cases[n], f'c{n - 1:04d}'
        d = os.path.join(out, c)
        jobs.append((e['ct'], os.path.join(d, 'ct.nii.gz')))
        if masks:
            jobs.append((e['mask'], os.path.join(d, 'coronary_arteries.nii.gz')))
        rows.append({'case': c, 'imagecas_id': n, 'folder': e['folder'], 'ct_id': e['ct']['_id'],
                     'mask_id': e['mask']['_id'] if e['mask'] else None})
    return jobs, rows


def verdict(jobs, out, n_cases):
    """Print the completeness verdict from what is on disk; True only if every file is complete (#82)."""
    bad = [d for i, d in jobs if not (os.path.exists(d) and os.path.getsize(d) == i['size'])]
    partial = [d for d in bad if glob.glob(glob.escape(d) + '.part*')]
    cts = [d for i, d in jobs if d.endswith('ct.nii.gz')]
    ok_cts = len(cts) - sum(d.endswith('ct.nii.gz') for d in bad)
    if not bad:
        print(f'{ok_cts} of {n_cases} CTs complete', flush=True)
        return True
    eg = sorted(os.path.relpath(d, out) for d in bad)[:5]
    print(f'INCOMPLETE: {ok_cts} of {n_cases} CTs complete; {len(bad) - len(partial)} missing / '
          f'{len(partial)} partial (.part), e.g. {eg}', flush=True)
    print(f're-run to resume: python3 {os.path.abspath(__file__)} {"--masks " if len(jobs) > len(cts) else ""}'
          f'{out}', flush=True)
    return False


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('dest', nargs='?', default='cases', help='the cases/ directory to fill')
    ap.add_argument('--masks', action='store_true',
                    help='also fetch the original ImageCAS masks (icx4 does not read them)')
    a = ap.parse_args(argv)
    out = os.path.abspath(a.dest)
    token = login()
    cases = list_cases(token, a.masks)
    jobs, rows = plan(cases, out, a.masks)
    os.makedirs(out, exist_ok=True)
    with lock(out):   # released when the run ends, however it ends
        for _, d in jobs:
            os.makedirs(os.path.dirname(d), exist_ok=True)
        with open(os.path.join(out, 'cases.json'), 'w') as f:
            json.dump(rows, f, indent=0)
        total = sum(i['size'] for i, _ in jobs)
        print(f'{len(cases)} ImageCAS cases ({"CT + mask" if a.masks else "CT only"}), {total / 1e9:.1f} GB -> {out}',
              flush=True)
        done, t0 = 0, time.time()
        ex = cf.ThreadPoolExecutor(THREADS)
        futs = [ex.submit(fetch, token, i, d) for i, d in jobs]
        try:
            for k, f in enumerate(cf.as_completed(futs), 1):
                try:
                    done += f.result()
                except (Exception, SystemExit) as e:  # noqa: BLE001 - one file failing must not hide the rest
                    print(e, file=sys.stderr, flush=True)
                if k % 50 == 0 or k == len(futs):
                    rate = done / max(time.time() - t0, 1) / 1e6
                    print(f'  {k}/{len(futs)} files, {done / 1e9:.1f} GB new, {rate:.0f} MB/s', flush=True)
        except KeyboardInterrupt:
            ex.shutdown(wait=False, cancel_futures=True)
            print('interrupted', flush=True)
            verdict(jobs, out, len(cases))
            sys.stderr.flush()
            os._exit(130)  # do not wait for the downloads still running; their .part files are resumed next time
        ex.shutdown()
        if not verdict(jobs, out, len(cases)):
            raise SystemExit(1)


if __name__ == '__main__':
    main()
