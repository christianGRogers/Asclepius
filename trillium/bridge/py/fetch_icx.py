"""Login node only (compute nodes have no internet): fetch ImageCAS-X per-segment label maps and file
lists (CC BY 4.0, Zenodo 10.5281/zenodo.21887809) by HTTP range reads of the release zip (~14 MB, not 1.4 GB).
usage: python fetch_icx.py OUTDIR      (idempotent; retries)
"""
import os
import sys
import time

URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def main(out):
    import remotezip
    os.makedirs(out, exist_ok=True)
    for attempt in range(30):
        try:
            z = remotezip.RemoteZip(URL)
            want = [n for n in z.namelist() if ('/segmentations/' in n and n.endswith('.coronary.nii.gz'))
                    or ('/filelist/' in n and n.endswith('.txt'))]
            todo = [n for n in want if not os.path.exists(os.path.join(out, os.path.basename(n)))]
            print(f'ImageCAS-X: {len(want)} files in release, {len(todo)} to fetch', flush=True)
            for n in todo:
                dest = os.path.join(out, os.path.basename(n))
                with open(dest + '.part', 'wb') as f:
                    f.write(z.read(n))
                os.replace(dest + '.part', dest)
            have = len([f for f in os.listdir(out) if f.endswith('.coronary.nii.gz')])
            if have < 800:
                raise RuntimeError(f'only {have}/800 label maps present')
            return
        except Exception as e:  # network hiccups on shared login nodes
            print(f'fetch attempt {attempt}: {type(e).__name__}: {e}', flush=True)
            time.sleep(min(60, 5 * (attempt + 1)))
    raise SystemExit('ERROR: could not fetch ImageCAS-X labels from Zenodo')


if __name__ == '__main__':
    main(sys.argv[1])
