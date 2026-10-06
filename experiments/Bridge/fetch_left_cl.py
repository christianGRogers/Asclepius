"""Fetch ImageCAS-X LEFT centreline files only (start_points truth), range reads with retries."""
import os, sys, time, remotezip
OUT = sys.argv[1]
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
for attempt in range(40):
    try:
        z = remotezip.RemoteZip(URL)
        todo = [n for n in z.namelist() if n.endswith('_left_centerline.vtk')
                and not os.path.exists(os.path.join(OUT, os.path.basename(n)))]
        print('todo', len(todo), flush=True)
        if not todo:
            break
        for n in todo:
            dest = os.path.join(OUT, os.path.basename(n))
            open(dest + '.part', 'wb').write(z.read(n)); os.replace(dest + '.part', dest)
    except Exception as e:
        print('retry', attempt, type(e).__name__, flush=True); time.sleep(10)
