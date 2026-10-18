"""Round 9: fetch ImageCAS-X labels and expert centrelines by HTTP range requests from the Zenodo zip
(10.5281/zenodo.21887809, CC BY 4.0), in priority order: ImageCAS-X val (80), then the non-sealed test cases (80),
then train. The 80 sealed test cases (vault/Plans/Sealed test.md, trillium/sealed_test.json) are never fetched.
Case c<k> is ImageCAS-X id k+1. Usage: r9_fetch.py <dest_dir> <repo_root>"""
import json, os, sys, time
from remotezip import RemoteZip
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'
dest, root = sys.argv[1], sys.argv[2]
os.makedirs(dest, exist_ok=True)
sealed = {int(c[1:]) + 1 for c in json.load(open(f'{root}/trillium/sealed_test.json'))['sealed_icx_test']}
for attempt in range(200):
    try:
        with RemoteZip(URL) as z:
            names = set(z.namelist())
            split = {s: [int(x) for x in z.read(f'ImageCAS-X_dataset/filelist/{s}.txt').decode().split()]
                     for s in ('val', 'test', 'train')}
            for s, ids in split.items():
                open(f'{dest}/{s}.txt', 'w').write('\n'.join(map(str, ids)) + '\n')
            order = [i for s in ('val', 'test', 'train') for i in split[s] if i not in sealed]
            files = []
            for i in order:
                files += [f'ImageCAS-X_dataset/segmentations/{i}.coronary.nii.gz',
                          f'ImageCAS-X_dataset/centerlines/{i}.coronary_left_centerline.vtk',
                          f'ImageCAS-X_dataset/centerlines/{i}.coronary_right_centerline.vtk']
            todo = [n for n in files if n in names and not os.path.exists(f'{dest}/{os.path.basename(n)}')]
            print(f'{len(order)} cases ({len(sealed)} sealed skipped); {len(todo)} files to fetch (attempt {attempt})',
                  flush=True)
            for n in todo:
                p = f'{dest}/{os.path.basename(n)}'
                open(p + '.part', 'wb').write(z.read(n)); os.replace(p + '.part', p)
        print('complete'); sys.exit(0)
    except Exception as e:
        print('retry:', repr(e)[:100], flush=True); time.sleep(20)
