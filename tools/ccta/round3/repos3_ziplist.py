"""Repos3: list a remote zip by HTTP range reads (name, size). Usage: repos3_ziplist.py URL [grep-regex]"""
import sys, os, zipfile, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from ingest_open import HTTPFile
hf = HTTPFile(sys.argv[1], block=1 << 20)
z = zipfile.ZipFile(hf)
pat = re.compile(sys.argv[2], re.I) if len(sys.argv) > 2 else None
print('# entries', len(z.infolist()), 'size', hf.size)
for i in z.infolist():
    if pat is None or pat.search(i.filename):
        print(i.file_size, i.filename)
