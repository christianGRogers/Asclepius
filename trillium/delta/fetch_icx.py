"""Login-node step: fetch the ImageCAS-X 14-class segmentations and file lists (~18 MB) from Zenodo
by HTTP range reads of the dataset zip (no 1.4 GB download). Idempotent; retries.

Usage: python fetch_icx.py <dest_dir>
ImageCAS-X: Bransby et al., arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809 (CC BY 4.0).
"""
import os
import sys
import time

from remotezip import RemoteZip

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def main(dest):
    os.makedirs(dest, exist_ok=True)
    for attempt in range(20):
        try:
            z = RemoteZip(URL)
            todo = [i for i in z.infolist()
                    if ('segmentations/' in i.filename or 'filelist/' in i.filename)
                    and not i.filename.endswith('/') and not os.path.exists(os.path.join(dest, i.filename))]
            print(f'ImageCAS-X: {len(todo)} files to fetch', flush=True)
            for i in todo:
                z.extract(i.filename, dest)
            break
        except Exception as e:  # noqa
            print('retry', attempt, type(e).__name__, e, flush=True)
            time.sleep(10)
    segs = os.listdir(os.path.join(dest, 'ImageCAS-X_dataset', 'segmentations'))
    lists = os.listdir(os.path.join(dest, 'ImageCAS-X_dataset', 'filelist'))
    print(f'ImageCAS-X ready: {len(segs)} segmentations, file lists {sorted(lists)}')
    if len(segs) < 800 or not {'train.txt', 'val.txt', 'test.txt'} <= set(lists):
        sys.exit('ImageCAS-X fetch incomplete')


if __name__ == '__main__':
    main(sys.argv[1])
