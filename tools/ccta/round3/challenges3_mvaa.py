"""Round 3 (agent Challenges3): MVAA 2026 (MICCAI 2026 MWM workshop challenge, Codabench 15662), Task 1 cardiac CT.

Training + validation data are a public Google Drive zip (MVAA_Data.zip, 6.9 GB; no account needed), licence
CC BY-NC stated on the challenge page. Members are read one at a time by HTTP range requests (only t1_ct).
Volumes are mitral-valve-centred crops (typically ~5 cm cubes, 0.36 mm in-plane) of contrast cardiac CT, in HU,
from Guangdong Provincial People's Hospital and two other Guangdong centres (overlap with ImageCAS possible).

    challenges3_mvaa.py --dry-run [--case ID]     # stage one case (no Girder)
    challenges3_mvaa.py [--limit N]               # upload (needs GIRDER_TOKEN_FILE)
"""
import argparse, http.client, os, shutil, sys, tempfile, time, zipfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
from ingest_open import HTTPFile, Sink, anatomy_check, blood_pool_hu, copy_member, log  # noqa: E402

ZIP = 'https://drive.usercontent.google.com/download?id=14WneBUBZ1X4p69tRdRzximNb0IsWuh2B&export=download&confirm=t'
PAGE = 'https://www.codabench.org/competitions/15662/'
DESC = ('MVAA 2026 challenge (Mitral Valve Anatomy Analysis Using Multimodal Imaging Data; MICCAI 2026 Workshop on '
        'Medical World Models), Task 1 cardiac CT: 1,040 unlabeled + 27 labeled training volumes + 30 validation '
        'volumes (no labels). Multi-vendor contrast cardiac CT from Guangdong Provincial People\'s Hospital, First '
        'Affiliated Hospital of Jinan University and Dongguan Eastern Central Hospital (Guangdong: overlap with '
        'ImageCAS patients cannot be ruled out). CROPPED: each volume is a mitral-valve-centred ROI (most ~5 cm, '
        '~0.36x0.36x0.5 mm; a few larger 1 mm crops); coronaries are mostly outside the ROI (LCx at the edge at '
        'best). HU as released. label.nii.gz (27 labeled cases) = released mitral valve mask (annulus/leaflets; '
        'challenge evaluates label 1). Licence CC BY-NC (non-commercial). Downloaded from the public Google Drive '
        'link on the challenge page.')
class RobustHTTPFile(HTTPFile):
    """HTTPFile whose block reads also retry truncated responses (http.client.IncompleteRead is not an OSError)."""

    def _fetch(self, k):
        for attempt in range(8):
            try:
                return super()._fetch(k)
            except (http.client.HTTPException, IOError) as e:
                if attempt == 7:
                    raise
                log('retry block', k, repr(e)[:120])
                time.sleep(min(60, 5 * 2 ** attempt))


CITE = ('MVAA 2026: Mitral Valve Anatomy Analysis Using Multimodal Imaging Data (organisers: J. Bai et al.; Jinan '
        'University / University of Auckland), MICCAI 2026 Workshop on Medical World Models, '
        'https://www.codabench.org/competitions/15662/ ; data licence CC BY-NC.')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--stage', default='ccta-stage')
    ap.add_argument('--work', default=None)
    ap.add_argument('--case', action='append')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    sink = Sink(args, 'MVAA2026-MitralCT', 'CC BY-NC', 'T2', PAGE, DESC, CITE)
    z = zipfile.ZipFile(RobustHTTPFile(ZIP, block=8 << 20))
    names = {i.filename: i for i in z.infolist()}
    todo = []
    for n in sorted(names):
        if not n.endswith('.nii.gz') or '/t1_ct/' not in n or '/labels/' in n:
            continue
        sid = os.path.basename(n)[:-7]
        split = 'val' if '/val/' in n else 'train-labeled' if '/labeled/' in n else 'train-unlabeled'
        todo.append((f'{split}_{sid}', split, sid, n))
    log(len(todo), 'CT volumes')
    for case, split, sid, m in todo:
        if args.case and case not in args.case:
            continue
        if sink.done(case):
            continue
        work = tempfile.mkdtemp(prefix='mvaa-', dir=args.work)
        try:
            ct = copy_member(z.open(names[m]), os.path.join(work, 'ct.nii.gz'))
            files = {}
            lm = f'reference_data/t1_ct/train/labeled/labels/{sid}-seg.nii.gz'
            if split == 'train-labeled' and lm in names:
                files['label.nii.gz'] = copy_member(z.open(names[lm]), os.path.join(work, 'label.nii.gz'))
            extra = dict(source_ids={'challenge': 'MVAA 2026', 'archive': 'MVAA_Data.zip', 'member': m,
                                     **({'label_member': lm} if files else {})},
                         split=split, hu_calibrated=True, cropped_roi='mitral valve',
                         coronaries_visible='mostly outside ROI',
                         blood_pool_median_hu=blood_pool_hu(ct), orientation_check=anatomy_check(ct),
                         labels={'label.nii.gz': 'released mitral valve segmentation (label 1 evaluated)'}
                         if files else {})
            sink.put(case, ct, extra, files)
        except Exception as e:   # one bad member must not stop the run
            log('ERROR', case, repr(e)[:300])
        finally:
            shutil.rmtree(work, ignore_errors=True)
        if sink.full():
            break


if __name__ == '__main__':
    main()
