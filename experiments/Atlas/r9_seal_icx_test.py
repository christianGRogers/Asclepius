"""Round 9 (Atlas v11 §6.1 step 3b): keep the A14 sealed test sealed when icx4 runs, without changing icx4.
FALLBACK ONLY: use it only if PR #66 (icx4's own sealed filter) is not merged; #66's launcher refuses a trimmed list.

icx4's prepare.py builds splits.json "test" from ImageCAS-X's filelist test.txt, and score.py scores every case in it,
including the 80 sealed ImageCAS-X test cases (Echo, #49). This rewrites <icx_dir>/test.txt without the sealed cases
(backup: test.full.txt), so icx4 scores only the 80 open test cases. Training (train.txt, val.txt) is untouched;
icx4 still predicts all 1000 cases, but never scores a sealed one. fetch_icx.py skips files that already exist, so the
edited test.txt survives `./icx4`.

  python r9_seal_icx_test.py <icx_dir> <sealed_test.json> [--fetch]

--fetch: if the filelists are missing, download only them (a few kB, HTTP range requests on the Zenodo zip; Python
standard library only, so it runs on a bare login node). Idempotent. Refuses (exit 2) if a sealed case is in
train/val, if the sealed list does not match, or if the result is not 80 open test cases.
Self-test: python r9_seal_icx_test.py --selftest
"""
import io
import json
import os
import shutil
import sys
import tempfile
import urllib.request
import zipfile

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


class HTTPRange(io.RawIOBase):
    """A read-only, seekable file over HTTP range requests (enough for zipfile)."""

    def __init__(self, url):
        self.url, self.pos = url, 0
        req = urllib.request.Request(url, method='HEAD')
        with urllib.request.urlopen(req, timeout=60) as r:
            self.size = int(r.headers['Content-Length'])

    def seekable(self):
        return True

    def readable(self):
        return True

    def tell(self):
        return self.pos

    def seek(self, off, whence=0):
        self.pos = {0: off, 1: self.pos + off, 2: self.size + off}[whence]
        return self.pos

    def read(self, n=-1):
        if n is None or n < 0:
            n = self.size - self.pos
        if n == 0 or self.pos >= self.size:
            return b''
        end = min(self.pos + n, self.size) - 1
        req = urllib.request.Request(self.url, headers={'Range': f'bytes={self.pos}-{end}'})
        with urllib.request.urlopen(req, timeout=120) as r:
            data = r.read()
        self.pos += len(data)
        return data

    def readinto(self, b):
        data = self.read(len(b))
        b[:len(data)] = data
        return len(data)


def fetch_filelists(dest):
    os.makedirs(dest, exist_ok=True)
    with zipfile.ZipFile(io.BufferedReader(HTTPRange(URL), buffer_size=1 << 16)) as z:
        for n in z.namelist():
            if '/filelist/' in n and n.endswith('.txt'):
                p = os.path.join(dest, os.path.basename(n))
                if not os.path.exists(p):
                    open(p + '.part', 'wb').write(z.read(n))
                    os.replace(p + '.part', p)
                    print(f'[seal] fetched {os.path.basename(n)}')


def ids(path):
    return ['c%04d' % (int(x) - 1) for x in open(path).read().split()]


def seal(icx, sealed_json):
    S = json.load(open(sealed_json))
    sealed = set(S['sealed_icx_test'])
    if len(sealed) != 80:
        sys.exit(f'[seal] REFUSING: {len(sealed)} sealed ImageCAS-X cases in {sealed_json}, expected 80')
    full = os.path.join(icx, 'test.full.txt')
    test = os.path.join(icx, 'test.txt')
    if not os.path.exists(full):
        shutil.copy2(test, full)
    raw = open(full).read().split()
    tr, va = ids(os.path.join(icx, 'train.txt')), ids(os.path.join(icx, 'val.txt'))
    leak = sorted(sealed & set(tr + va))
    if leak:
        print(f'[seal] REFUSING: sealed cases in ImageCAS-X train/val: {leak[:5]}'); sys.exit(2)
    full_ids = ['c%04d' % (int(x) - 1) for x in raw]
    missing = sorted(sealed - set(full_ids))
    if missing:
        print(f'[seal] REFUSING: sealed cases not in ImageCAS-X test: {missing[:5]}'); sys.exit(2)
    keep = [x for x in raw if 'c%04d' % (int(x) - 1) not in sealed]
    if len(keep) != 80:
        print(f'[seal] REFUSING: {len(keep)} open test cases, expected 80'); sys.exit(2)
    open(test + '.part', 'w').write('\n'.join(keep) + '\n')
    os.replace(test + '.part', test)
    open_ = set(S['open_icx_test']) | set(S['excluded_dev_cases_in_test'])
    if {'c%04d' % (int(x) - 1) for x in keep} != open_:
        print('[seal] REFUSING: the open test cases do not match sealed_test.json'); sys.exit(2)
    print(f'[seal] test.txt: {len(raw)} -> {len(keep)} cases ({len(raw) - len(keep)} sealed removed); '
          f'backup {full}. train {len(tr)}, val {len(va)} unchanged.')


def selftest():
    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    sj = os.path.join(root, 'trillium', 'sealed_test.json')
    S = json.load(open(sj))
    test_cases = S['sealed_icx_test'] + S['open_icx_test'] + S['excluded_dev_cases_in_test']
    num = lambda c: str(int(c[1:]) + 1)  # noqa: E731
    other = [f'c{i:04d}' for i in range(1000) if f'c{i:04d}' not in set(test_cases)]
    with tempfile.TemporaryDirectory() as td:
        open(os.path.join(td, 'test.txt'), 'w').write('\n'.join(num(c) for c in test_cases))
        open(os.path.join(td, 'train.txt'), 'w').write('\n'.join(num(c) for c in other[:560]))
        open(os.path.join(td, 'val.txt'), 'w').write('\n'.join(num(c) for c in other[560:640]))
        seal(td, sj)
        seal(td, sj)  # idempotent
        assert len(open(os.path.join(td, 'test.txt')).read().split()) == 80
        assert len(open(os.path.join(td, 'test.full.txt')).read().split()) == 160
        open(os.path.join(td, 'val.txt'), 'a').write('\n' + num(S['sealed_icx_test'][0]))
        try:
            seal(td, sj)
            raise AssertionError('leak not refused')
        except SystemExit as e:
            assert e.code == 2
    print('[seal] self-test passed')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--selftest']:
        selftest(); sys.exit(0)
    icx_dir, sealed_json = sys.argv[1], sys.argv[2]
    if '--fetch' in sys.argv and not all(os.path.exists(os.path.join(icx_dir, f)) for f in ('train.txt', 'val.txt', 'test.txt')):
        fetch_filelists(icx_dir)
    seal(icx_dir, sealed_json)
