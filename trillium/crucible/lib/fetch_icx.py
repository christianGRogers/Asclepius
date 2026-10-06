"""Login node: fetch ImageCAS-X segmentations + split files (Zenodo 10.5281/zenodo.21887809, CC BY 4.0) with one HTTP
range request (~13.5 MB of the 1.44 GB zip), CRC-checked. Idempotent. Usage: python fetch_icx.py <out_dir>"""
import os, struct, sys, zlib, urllib.request, zipfile, io

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def rng_get(start, end=None):
    req = urllib.request.Request(URL, headers={'Range': f'bytes={start}-' + ('' if end is None else str(end))})
    with urllib.request.urlopen(req, timeout=600) as r:
        return r.read()


def main(out):
    done = os.path.join(out, '.complete')
    if os.path.exists(done):
        print('ImageCAS-X labels already fetched:', out); return
    os.makedirs(out, exist_ok=True)
    # central directory: read the end of the file, locate EOCD (zip64-aware via zipfile on a tail buffer)
    head = urllib.request.urlopen(urllib.request.Request(URL, method='HEAD'), timeout=120)
    size = int(head.headers['Content-Length'])
    tail = rng_get(max(0, size - 1_000_000))
    off0 = size - len(tail)

    class Tail(io.RawIOBase):  # file-like over (sparse) remote zip: tail buffer + lazily fetched ranges
        def __init__(s): s.pos = 0; s.cache = {off0: tail}
        def seekable(s): return True
        def readable(s): return True
        def seek(s, p, wh=0):
            s.pos = p if wh == 0 else (s.pos + p if wh == 1 else size + p); return s.pos
        def tell(s): return s.pos
        def readinto(s, b):
            n = min(len(b), size - s.pos)
            if n <= 0: return 0
            for o, buf in s.cache.items():
                if o <= s.pos and s.pos + n <= o + len(buf):
                    b[:n] = buf[s.pos - o:s.pos - o + n]; s.pos += n; return n
            data = rng_get(s.pos, min(size - 1, s.pos + max(n, 1 << 20) - 1)); s.cache[s.pos] = data
            b[:n] = data[:n]; s.pos += n; return n

    z = zipfile.ZipFile(io.BufferedReader(Tail(), buffer_size=1 << 20))
    want = [i for i in z.infolist() if ('segmentations/' in i.filename or 'filelist/' in i.filename) and not i.filename.endswith('/')]
    start = min(i.header_offset for i in want)
    blob = rng_get(start)  # one request for the contiguous tail holding all wanted entries
    n = 0
    for i in want:
        p = i.header_offset - start
        assert blob[p:p + 4] == b'PK\x03\x04', i.filename
        nl, el = struct.unpack('<HH', blob[p + 26:p + 30]); q = p + 30 + nl + el
        data = blob[q:q + i.compress_size]
        raw = zlib.decompress(data, -15) if i.compress_type == 8 else data
        assert zlib.crc32(raw) & 0xffffffff == i.CRC, i.filename
        fn = os.path.join(out, os.path.basename(i.filename)); open(fn, 'wb').write(raw); n += 1
    open(done, 'w').write(str(n))
    print(f'fetched {n} ImageCAS-X files into {out}')


if __name__ == '__main__':
    main(sys.argv[1])
