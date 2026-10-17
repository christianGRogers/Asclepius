"""Round 3 (agent Journals): journal-supplement DICOM archives -> CCTA-Pool, one case per contrast series/phase.

Each SOURCE entry is a paper whose supplementary files (often split RAR/ZIP archives on the publisher's figshare)
hold whole DICOM studies. All volumes of a source are fetched, extracted (split RAR via unrar, path in $UNRAR or
the Journals tools dir), grouped by SeriesInstanceUID, and only ORIGINAL axial reconstructions with >= MIN_SLICES
slices and contrast (blood pool) are stored: one case per series (= per cardiac phase), patient id in extra.
Derived MPRs, calcium-score tables, scouts and non-contrast series are skipped. File and folder names inside the
archives can encode patient names and exam dates: they are never stored; only non-identifying tags are kept
(ingest_open.dicom_extra).

    python3 journals_suppdicom.py <source> --dry-run [--stage DIR]
    python3 journals_suppdicom.py <source> [--limit N]          # upload (needs GIRDER_TOKEN_FILE)
"""
import argparse, collections, glob, os, re, shutil, subprocess, sys
import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ingest_open as io_  # noqa: E402

UNRAR = os.environ.get('UNRAR', '/tmp/claude-0/-home-user-Asclepius/1b43aea1-ed14-5dd0-84ee-25f776047e09/scratchpad/'
                       'journals_tools/root/usr/bin/unrar-nonfree')
MIN_SLICES = 40

SOURCES = {
    'bmc-zhang2017': dict(
        dataset='BMC-BEO2017-SerialStenosis-CCTA',
        parts=['https://ndownloader.figshare.com/files/9720220', 'https://ndownloader.figshare.com/files/9720244'],
        kind='rar', patient='P1', licence='CC BY 4.0 (+ CC0 for data, BioMed Central)', tier='T1',
        source_url='https://doi.org/10.1186/s12938-017-0413-0',
        description=('Additional files 1-2 ("CTA image data", split RAR, springernature figshare 5589196 / 5589220) of '
                     '"Hemodynamics analysis of the serial stenotic coronary arteries", Biomed Eng Online 2017. One '
                     'patient, Siemens SOMATOM Definition Flash prospectively gated sequential CCTA (Shenzhen Sun '
                     'Yat-Sen Cardiovascular Hospital, 2015): BestDiast 70 % and BestSyst 40 % reconstructions, '
                     '0.75 mm, HU. The deposit covers only part of the heart (about 55 / 37 mm). Same hospital and '
                     'group as PLOS-Peng2016-CCTA-JPEG (different exam date; overlap not excluded).'),
        citation=('Hemodynamics analysis of the serial stenotic coronary arteries. Biomed Eng Online 16:127 (2017). '
                  'https://doi.org/10.1186/s12938-017-0413-0 ; Additional files 1-2 '
                  'https://doi.org/10.6084/m9.figshare.5589196 , https://doi.org/10.6084/m9.figshare.5589220')),
}


def extract(src, work):
    x = os.path.join(work, 'x')
    os.makedirs(x)
    paths = []
    for k, u in enumerate(src['parts']):
        ext = 'rar' if src['kind'] == 'rar' else 'zip'
        p = os.path.join(work, f'a.part{k + 1}.{ext}')
        io_.download(u, p)
        paths.append(p)
    if src['kind'] == 'rar':
        r = subprocess.run([UNRAR, 'x', '-inul', '-o+', paths[0], x + '/'])
        if r.returncode:   # e.g. a member continued from a volume missing from the deposit: keep what is complete
            io_.log(f'unrar exit {r.returncode}: some members could not be extracted')
    else:
        for p in paths:
            subprocess.run(['bsdtar', '-xf', p, '-C', x], check=True)
    for p in paths:
        os.remove(p)
    return x


def series(x):
    import pydicom
    g = collections.defaultdict(list)
    for f in glob.glob(os.path.join(x, '**', '*'), recursive=True):
        if not os.path.isfile(f):
            continue
        try:
            d = pydicom.dcmread(f, stop_before_pixels=True)
        except Exception:
            continue
        if getattr(d, 'Modality', '') != 'CT' or 'ImagePositionPatient' not in d:
            continue
        it = [str(v).upper() for v in (getattr(d, 'ImageType', []) or [])]
        if it[:1] != ['ORIGINAL'] or (len(it) > 2 and it[2] not in ('AXIAL', '')):
            continue
        g[d.SeriesInstanceUID].append((f, d))
    return g


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('source', choices=sorted(SOURCES))
    ap.add_argument('--dry-run', action='store_true')
    ap.add_argument('--stage', default='ccta-stage')
    ap.add_argument('--work', default=None)
    ap.add_argument('--case', action='append')
    ap.add_argument('--limit', type=int, default=0)
    args = ap.parse_args()
    src = SOURCES[args.source]
    sink = io_.Sink(args, src['dataset'], src['licence'], src['tier'], src['source_url'], src['description'],
                    src['citation'])
    work = io_.tmpdir(args)
    try:
        x = extract(src, work)
        g = series(x)
        for uid, lst in sorted(g.items(), key=lambda kv: int(getattr(kv[1][0][1], 'SeriesNumber', 0) or 0)):
            d = lst[0][1]
            if len(lst) < MIN_SLICES or re.search(r'casc|calcium|ca[ _]?score', str(getattr(d, 'SeriesDescription', '')), re.I):
                continue
            desc = str(getattr(d, 'SeriesDescription', ''))
            ph = str(getattr(d, 'ImageComments', '') or '')
            case = f"{src['patient']}_s{int(getattr(d, 'SeriesNumber', 0) or 0)}"
            if not io_.selected(args, case) or sink.done(case):
                continue
            sd = os.path.join(work, 'series')
            shutil.rmtree(sd, ignore_errors=True)
            os.makedirs(sd)
            for k, (f, _) in enumerate(lst):
                os.link(f, os.path.join(sd, f'{k:05d}.dcm'))
            tmp = os.path.join(work, 'nii')
            shutil.rmtree(tmp, ignore_errors=True)
            os.makedirs(tmp)
            nii = io_.ccta_ingest.to_nifti(sd, tmp)
            bp = io_.blood_pool_hu(nii)
            if bp is None:
                io_.log('skip (no contrast)', case, desc)
                continue
            inst = sorted(int(getattr(dd, 'InstanceNumber', 0) or 0) for _, dd in lst)
            complete = inst == list(range(1, len(inst) + 1))
            extra = dict(source_ids={'source': args.source, 'series_number': int(getattr(d, 'SeriesNumber', 0) or 0),
                                     'n_slices': len(lst), 'instance_range': [inst[0], inst[-1]]},
                         series_complete=complete,
                         patient_id=src['patient'], phase=ph.split(',')[1].strip() if ',' in ph else ph,
                         series_description=desc, hu_calibrated=True, blood_pool_median_hu=bp,
                         orientation_check=io_.anatomy_check(nii), **{'dicom': io_.dicom_extra(sd)})
            sink.put(case, nii, extra)
            if sink.full():
                break
    finally:
        shutil.rmtree(work, ignore_errors=True)


if __name__ == '__main__':
    main()
