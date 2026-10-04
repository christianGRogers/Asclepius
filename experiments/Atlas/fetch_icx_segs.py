"""Fetch only the ImageCAS-X segmentation files + filelists + descriptors (~14 MB) from the
Zenodo zip via HTTP range requests (remotezip), with retries. Output dir: argv[1]"""
import os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
OUT = sys.argv[1]
for attempt in range(50):
    try:
        with RemoteZip(URL) as z:
            names = [n for n in z.namelist() if ('/segmentations/' in n and n.endswith('.nii.gz'))
                     or '/filelist/' in n or n.endswith('.xlsx')]
            todo = [n for n in names if not os.path.exists(os.path.join(OUT, os.path.basename(n)))]
            print('attempt', attempt, 'todo', len(todo), flush=True)
            for n in todo:
                dest = os.path.join(OUT, os.path.basename(n))
                data = z.read(n)
                with open(dest + '.part', 'wb') as f: f.write(data)
                os.replace(dest + '.part', dest)
        print('done', len(names)); break
    except Exception as e:
        print('error', repr(e)[:200], flush=True); time.sleep(10)
