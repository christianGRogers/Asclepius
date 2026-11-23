"""Bridge, Janus 1-L round 3: fetch the ImageCAS-X labels of the D45 train 620 only (remotezip range reads).

Refuses any id in the locked 100, in trillium/sealed_test.json (sealed ImageCAS-X test 80 and quality-0 20).
Case id cNNNN is file (NNNN + 1).coronary.nii.gz (as in Step T). Labels only; no CT, no surfaces, no centrelines.
Usage: python3 fetch620.py <out dir>
"""
import json, os, sys
import remotezip

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
URL = 'https://zenodo.org/api/records/21887809/files/ImageCAS-X_dataset.zip/content'


def lists():
    sp = json.load(open(os.path.join(REPO, 'experiments/Delta/j1l_r1/janus1_split_proposal.json')))
    se = json.load(open(os.path.join(REPO, 'trillium/sealed_test.json')))
    sealed = set(se['sealed_icx_test']) | set(se['sealed_quality0'])
    train, locked = list(sp['train620']), set(sp['locked100'])
    assert len(train) == 620 and not (set(train) & (locked | sealed)), 'train 620 overlaps locked/sealed'
    return train, locked | sealed


def main(out):
    train, banned = lists()
    os.makedirs(out, exist_ok=True)
    with remotezip.RemoteZip(URL) as z:
        names = set(z.namelist())
        for c in train:
            assert c not in banned
            n = int(c[1:]) + 1
            src = f'ImageCAS-X_dataset/segmentations/{n}.coronary.nii.gz'
            dest = os.path.join(out, f'{c}.nii.gz')
            if os.path.exists(dest):
                continue
            assert src in names, src
            with open(dest + '.part', 'wb') as f:
                f.write(z.read(src))
            os.replace(dest + '.part', dest)
    print('fetched', len(os.listdir(out)))


if __name__ == '__main__':
    main(sys.argv[1])
