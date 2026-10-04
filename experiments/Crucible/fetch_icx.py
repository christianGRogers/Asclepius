# Pull ImageCAS-X segmentations + filelists + Descriptors.xlsx from the 1.44 GB Zenodo zip
# (record 21887809, CC BY 4.0) WITHOUT downloading the zip: these entries are contiguous in the
# last ~13.5 MB, so one HTTP range request + manual parsing of ZIP local headers suffices.
import os, struct, zlib, subprocess
W = '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/work/Crucible/icx'
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
START = 1429694744  # offset of the filelist/ entry (found with remotezip infolist)
blob = W + '/tail.bin'
os.makedirs(W, exist_ok=True)
if not os.path.exists(blob): subprocess.run(['curl', '-sS', '-L', '--retry', '10', '-r', f'{START}-', '-o', blob, URL], check=True)
from remotezip import RemoteZip
infos = [i for i in RemoteZip(URL).infolist() if i.header_offset >= START and not i.filename.endswith('/')]
b = open(blob, 'rb').read(); n = 0
for i in infos:  # sizes/crc come from the central directory (local headers use data descriptors)
    p = i.header_offset - START; assert b[p:p + 4] == b'PK\x03\x04'
    nl, el = struct.unpack('<HH', b[p + 26:p + 30]); q = p + 30 + nl + el
    data = b[q:q + i.compress_size]; meth = i.compress_type; crc = i.CRC; name = i.filename
    out = zlib.decompress(data, -15) if meth == 8 else data
    assert zlib.crc32(out) & 0xffffffff == crc, name
    fn = os.path.join(W, name); os.makedirs(os.path.dirname(fn), exist_ok=True)
    open(fn, 'wb').write(out); n += 1
print('extracted', n)
os.remove(blob)
