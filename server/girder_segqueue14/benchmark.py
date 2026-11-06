"""``segqueue14-benchmark`` -- the annotator benchmark (D43, #286).

One ImageCAS-X case, drawn once and then fixed, served to every annotator (but the
logins named at run time) as their next case, seeded like a pool case and scored on
its own against ImageCAS-X. Runs on the server against the database, like
``segqueue14-populate``. Every step is idempotent, and every step that writes is a
dry run without ``--apply``::

    segqueue14-benchmark pick                     # the draw from the repository alone
    segqueue14-benchmark create [--apply]         # make the case (or show the one there is)
    segqueue14-benchmark seed --totalseg BIN [--apply]    # its TotalSegmentator seed, on CPU
    segqueue14-benchmark seed --seed-file PATH [--apply]  # ... or one made elsewhere
    segqueue14-benchmark seed --from-girder user/x/Public [--from-girder-file NAME] [--apply]
    segqueue14-benchmark assign --exclude a,b [--login x,y] [--retest] [--apply]
    segqueue14-benchmark status [--json]

**pick / create.** Which ImageCAS-X cases may be drawn, and the draw, are
``segqueue14.benchmark``'s: train/val cases that are not test, on no
``trillium/sealed_test.json`` list, and not refused by the JA12 guard
(``janusm.guard``: the A14 sealed 100, test, val 80, the Janus-M seal and decision
cases); a salted sha256 ranks the rest. The guard checks every input against its
sha256 pin, and a missing or changed file stops the run. ``create`` takes the first
case in draw order whose CT (``ImageCAS-X/cases/ImageCAS__NNNN.nii.gz``) and
ImageCAS-X reference (``ImageCAS-X/labels/**/ImageCAS-X__NNNN__labels14.nii.gz``)
are in Girder, references both in place (nothing is copied) and records the pick
on the case. Once the case exists, nothing is drawn again: later runs show it.

**seed.** As the pool seeds were made (``tools/ccta/totalseg_cpu.py``):
TotalSegmentator 2.18.0 ``coronary_arteries``, on CPU, the same command, the mask
made binary (uint8 0/1) on the CT's own grid, uploaded to
``SegQueue/seeds-totalseg/ImageCAS__NNNN__totalseg-coronary.nii.gz``. The
TotalSegmentator install is separate from Girder's (``--totalseg`` names its
executable); the deploy step builds one. A seed made elsewhere the same way can be
given with ``--seed-file``; it must be on the CT's grid. ``--from-girder`` takes it
from a Girder folder instead (#293): the volume there whose name holds the case's
ImageCAS id (``0855``), else the only volume there, else ``--from-girder-file``
names it. The file is downloaded and copied into the seeds folder; the original is
never changed, moved or deleted. The case is served only once it has a seed.

**assign.** Invites every member of ``segqueue14-annotators`` except the
``--exclude`` logins (required, may be empty: say who is left out), or only the
``--login`` ones. An annotator who has submitted it already is skipped unless
``--retest``, which gives a fresh attempt; each attempt keeps its own score. An
invited annotator gets it from ``/next`` before any pool case (after the case they
hold, if any). Excluded logins with an invitation have it withdrawn.

**status.** Who has it, in what state, and each attempt's Dice against ImageCAS-X
(collapsed to the four classes, D25), per class and mean.
"""

import argparse
import datetime
import json
import os
import shutil
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

from segqueue import states as st
from segqueue14 import benchmark as sqbench
from segqueue14 import labels as sqlabels
from segqueue14 import plan as sqplan

from .constants import ANNOTATOR_GROUP, LIVE_COLLECTION_NAME, SEEDS_FOLDER

#: Where ImageCAS-X lives in Girder (D22). Read only.
ICX_COLLECTION = 'ImageCAS-X'
ICX_CASES_FOLDER = 'cases'
ICX_LABELS_FOLDER = 'labels'

#: The repository files the draw reads, both sha256-pinned by ``janusm.guard``.
SPLITS_RELPATH = 'trillium-results/icx14/results/splits.json'
SEALED_TEST_RELPATH = 'trillium/sealed_test.json'
#: Environment variable naming the repository checkout (default: the guard's).
REPO_ENV = 'SEGQUEUE14_REPO'

#: The pool seeds' model (``plan.SEED_SOURCE_TOTALSEG``, ``tools/ccta/totalseg_cpu.py``).
TOTALSEG_VERSION = '2.18.0'
#: ``tools/ccta/totalseg_cpu.py``'s two commands, unchanged: the normal one, then the
#: low-memory retry (one worker, three-chunk split).
TS_ARGS = ['-ta', 'coronary_arteries', '--ml', '-d', 'cpu', '-nr', '4', '-ns', '4', '-q']
TS_LOWMEM_ARGS = ['-ta', 'coronary_arteries', '--ml', '-d', 'cpu', '-nr', '1', '-ns', '1',
                  '--force_split', '-q']
#: The batch segmented larger volumes on a 0.8 mm copy. ImageCAS volumes are far
#: below this; a bigger one is refused rather than made differently.
LARGE_VOXELS = 200e6
TS_TIMEOUT = 3 * 3600


def _now():
    return datetime.datetime.now(datetime.timezone.utc)


def ctName(n):
    return f'ImageCAS__{int(n):04d}.nii.gz'


def referenceName(n):
    return f'ImageCAS-X__{int(n):04d}__labels14.nii.gz'


def seedName(n):
    """``ImageCAS__0123__totalseg-coronary.nii.gz``, the pool seeds' naming (D23)."""
    return sqplan.seed_name_for(ctName(n))


# --------------------------------------------------------------- the draw


def repoRoot(path=None):
    """The checkout whose pinned lists the draw reads."""
    for candidate in (path, os.environ.get(REPO_ENV), os.environ.get('JANUSM_REPO')):
        if candidate:
            return Path(candidate)
    if (Path.cwd() / SPLITS_RELPATH).is_file():
        return Path.cwd()
    return Path(sqbench.__file__).resolve().parents[2]


def loadInputs(root):
    """``(guard, splits, sealed_test)``, every file checked against its pin.

    Fails closed: no guard, an unpinned or changed list, or a missing file stops
    the run before anything is drawn.
    """
    import hashlib

    try:
        from janusm import guard as jguard
    except Exception as exc:  # noqa: BLE001 - fail closed on any import problem
        raise SystemExit(
            f'REFUSED: the JA12 guard (janusm.guard) cannot be imported ({exc})') from exc
    try:
        guard = jguard.load_guard(root)
    except Exception as exc:  # noqa: BLE001
        raise SystemExit(
            f'REFUSED: the JA12 guard could not load from {root} ({exc})') from exc
    pins = {SPLITS_RELPATH: jguard.PINNED[jguard.SPLITS_RELPATH],
            # trillium/sealed_test.json is the same file as the guard's A14 list.
            SEALED_TEST_RELPATH: jguard.PINNED[jguard.A14_RELPATH]}
    loaded = {}
    for rel, sha in pins.items():
        path = Path(root) / rel
        if not path.is_file():
            raise SystemExit(f'REFUSED: {rel} not found under {root}')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != sha:
            raise SystemExit(f'REFUSED: {rel} is not the pinned file (sha256 {sha[:12]}...)')
        loaded[rel] = json.loads(raw.decode('utf-8'))
    return guard, loaded[SPLITS_RELPATH], loaded[SEALED_TEST_RELPATH]


def loadTwins(path):
    """ImageCAS-X c-ids from a twin list (a JSON list, or ``{"twins": [...]}``), or None.

    The project has none for ImageCAS (``segqueue14.benchmark.NO_TWIN_LIST``);
    this is for when one exists. Entries may be c-ids or ImageCAS ids.
    """
    if not path:
        return None
    data = json.loads(Path(path).read_text())
    if isinstance(data, dict):
        data = data.get('twins', [])
    out = set()
    for entry in data:
        text = str(entry).strip()
        out.add(text if text.startswith('c') else sqbench.icx_case(int(text)))
    return out


def computeEligibility(root, twinsFile=None):
    guard, splits, sealedTest = loadInputs(root)
    elig = sqbench.eligibility(
        splits, sealedTest, lambda c: guard.reason(c, source='ImageCAS-X'),
        twins=loadTwins(twinsFile))
    return elig, splits, guard


def _printEligibility(elig, out):
    out(f'eligible: {len(elig.eligible)} ImageCAS-X train/val case(s); excluded: '
        + (', '.join(f'{k} {v}' for k, v in elig.counts().items()) or 'none'))
    out(f'twins: {elig.twins}')


def runPick(root=None, twinsFile=None, out=print):
    """The draw from the repository alone (no database)."""
    elig, splits, _ = computeEligibility(repoRoot(root), twinsFile)
    _printEligibility(elig, out)
    pick = sqbench.draw(elig, splits)
    out(f'pick: {pick.name}  ({pick.why})')
    return pick


# ---------------------------------------------------------- Girder lookups


def _icxIndex():
    """``({CT item name: item}, {reference item name: item})`` in ImageCAS-X."""
    from .populate import _namedFolder, _walkItems

    cases = _namedFolder(ICX_COLLECTION, ICX_CASES_FOLDER)
    labels = _namedFolder(ICX_COLLECTION, ICX_LABELS_FOLDER)
    if cases is None or labels is None:
        raise SystemExit(f'REFUSED: no {ICX_COLLECTION}/{ICX_CASES_FOLDER} or '
                         f'{ICX_COLLECTION}/{ICX_LABELS_FOLDER} folder')
    cts = {item['name']: item for _, item in _walkItems(cases)}
    refs = {}
    for _, item in _walkItems(labels):
        refs.setdefault(item['name'], []).append(item)
    return cts, refs


def _seedsFolder():
    from .populate import _namedFolder

    return _namedFolder(LIVE_COLLECTION_NAME, SEEDS_FOLDER)


def _seedItem(n):
    from girder.models.item import Item

    folder = _seedsFolder()
    if folder is None:
        return None
    return Item().findOne({'folderId': folder['_id'], 'name': seedName(n)})


def _sources(n, cts, refs):
    """``(ct file, reference file, problem)`` for ImageCAS id ``n``."""
    from .populate import _firstFile

    item = cts.get(ctName(n))
    if item is None:
        return None, None, f'no {ctName(n)} in {ICX_COLLECTION}/{ICX_CASES_FOLDER}'
    split = (item.get('meta') or {}).get('icx_split')
    if split is not None and split not in sqbench.ELIGIBLE_SPLITS:
        return None, None, f'{ctName(n)} is marked icx_split={split!r}'
    ct = _firstFile(item)
    if ct is None:
        return None, None, f'{ctName(n)} has no file'
    found = refs.get(referenceName(n), [])
    if len(found) != 1:
        return None, None, f'{len(found)} {referenceName(n)} items under {ICX_COLLECTION}/labels'
    ref = _firstFile(found[0])
    if ref is None:
        return None, None, f'{referenceName(n)} has no file'
    return ct, ref, None


def _admin():
    from girder.models.user import User

    admin = User().findOne({'admin': True})
    if admin is None:
        raise SystemExit('REFUSED: no Girder admin account')
    return admin


def _case(required=True):
    from girder.exceptions import ValidationException

    from .models import Case14

    try:
        case = Case14().benchmarkCase()
    except ValidationException as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
    if case is None and required:
        raise SystemExit('No annotator benchmark case yet: run `segqueue14-benchmark create`.')
    return case


# ------------------------------------------------------------------ create


def runCreate(apply=False, root=None, twinsFile=None, out=print):
    """Make the benchmark case, or show the one there is. Returns a summary dict."""
    from girder.models.file import File

    from .models import Case14
    from .utils import hashStoredFile

    existing = _case(required=False)
    if existing is not None:
        pick = existing.get('benchmarkPick') or {}
        out(f"benchmark case: {existing['name']} (exists; never redrawn)")
        out(f"  pick: {pick.get('why', '?')}")
        n = sqbench.imagecas_id_of(existing['name'])
        seed = None
        if not existing.get('seedFileId') and n is not None:
            seed = _seedItem(n)
            if seed is not None:
                from .populate import _firstFile

                seedFile = _firstFile(seed)
                if seedFile is not None and apply:
                    _attachSeed(existing, seedFile['_id'])
                state = 'attached' if apply else 'found; --apply attaches it'
                out(f'  seed: {seedName(n)} {state}')
        out(f"  seed: {'yes' if existing.get('seedFileId') else 'none yet'}; reference: "
            f"{'yes' if existing.get('referenceFileId') else 'MISSING'}; "
            f"CT present: {File().load(existing['fileId'], force=True) is not None}")
        return {'created': False, 'name': existing['name']}

    elig, splits, guard = computeEligibility(repoRoot(root), twinsFile)
    _printEligibility(elig, out)
    cts, refs = _icxIndex()
    found = {}

    def usable(c):
        n = sqbench.imagecas_id(c)
        ct, ref, problem = _sources(n, cts, refs)
        if problem is None:
            found[c] = (ct, ref)
        return problem

    skipped = []
    try:
        pick = sqbench.draw(elig, splits, usable, skipped)
    except ValueError as exc:
        raise SystemExit(f'REFUSED: {exc}') from exc
    for line in skipped:
        out(f'  skipped {line}')
    out(f'pick: {pick.name}')
    out(f'  why: {pick.why}')
    clash = Case14().findOne({'name': pick.name})
    if clash is not None:
        raise SystemExit(f'REFUSED: a case named {pick.name} exists and is not the benchmark')
    ct, ref = found[pick.icx]
    seedItem = _seedItem(pick.imagecas_id)
    seedFile = None
    if seedItem is not None:
        from .populate import _firstFile

        seedFile = _firstFile(seedItem)
    out(f"  CT {ct['name']} ({ct.get('size', 0)} bytes, referenced in place); reference "
        f"{ref['name']}; seed {seedName(pick.imagecas_id) if seedFile else 'none yet (run seed)'}")
    from janusm.guard import GUARD_VERSION

    record = dict(pick.to_dict(), twins=elig.twins, excluded=elig.counts(),
                  skipped=skipped, guardVersion=GUARD_VERSION, pins=dict(guard.pins),
                  pickedAt=_now())
    if not apply:
        out('dry run: nothing written. --apply creates the case.')
        return {'created': False, 'name': pick.name, 'pick': record}
    case = Case14().createCase(
        name=pick.name, fileId=ct['_id'], checksum=hashStoredFile(ct),
        sizeBytes=ct.get('size', 0), creator=_admin(), priority=0, serveOrder=0,
        replicasWanted=1, tier=sqbench.TIER, dataset=sqbench.DATASET, split=pick.split,
        referenceFileId=ref['_id'],
        seedFileId=seedFile['_id'] if seedFile else None,
        seedSource=sqplan.SEED_SOURCE_TOTALSEG if seedFile else '',
        extra={'benchmark': True, 'benchmarkPick': record, 'benchmarkPending': [],
               'benchmarkInvites': []})
    out(f"created {case['name']}" + ('' if seedFile else '; it is served only once it has a '
                                                         'seed (segqueue14-benchmark seed)'))
    return {'created': True, 'name': case['name'], 'pick': record}


def _attachSeed(case, fileId, source=None):
    from .models import Case14

    result = Case14().collection.update_one(
        {'_id': case['_id'], 'seedFileId': None},
        {'$set': {'seedFileId': fileId, 'seedSource': source or sqplan.SEED_SOURCE_TOTALSEG,
                  'updated': _now()}})
    return bool(result.modified_count)


# -------------------------------------------------------------------- seed


def _grid(path):
    import SimpleITK as sitk

    reader = sitk.ImageFileReader()
    reader.SetFileName(str(path))
    reader.ReadImageInformation()
    return (tuple(reader.GetSize()), tuple(reader.GetSpacing()), tuple(reader.GetOrigin()),
            tuple(reader.GetDirection()))


def _sameGrid(a, b, tol=1e-3):
    if a[0] != b[0]:
        return False
    return all(abs(x - y) <= tol for one, two in zip(a[1:], b[1:], strict=True)
               for x, y in zip(one, two, strict=True))


def binarise(segPath, ctPath, outPath):
    """``segPath`` as a uint8 0/1 mask on ``ctPath``'s grid, written to ``outPath``.

    Refuses a mask that is not on the CT's grid or is empty. Returns its stats.
    """
    import numpy as np
    import SimpleITK as sitk

    ctGrid = _grid(ctPath)
    if not _sameGrid(_grid(segPath), ctGrid):
        raise SystemExit(f'REFUSED: the seed is not on the CT\'s grid ({ctGrid[0]} voxels)')
    seg = sitk.ReadImage(str(segPath))
    mask = (sitk.GetArrayFromImage(seg) > 0).astype(np.uint8)
    voxels = int(mask.sum())
    if not voxels:
        raise SystemExit('REFUSED: the seed is empty (TotalSegmentator found no coronary artery)')
    image = sitk.GetImageFromArray(mask)
    image.SetSpacing(ctGrid[1])
    image.SetOrigin(ctGrid[2])
    image.SetDirection(ctGrid[3])
    sitk.WriteImage(image, str(outPath), True)
    vox = float(np.prod(ctGrid[1]))
    return {'voxels': voxels, 'volume_ml': round(voxels * vox / 1000, 3)}


def _sha256(path):
    import hashlib

    digest = hashlib.sha256()
    with open(path, 'rb') as handle:
        for block in iter(lambda: handle.read(1 << 20), b''):
            digest.update(block)
    return digest.hexdigest()


def totalsegVersion(binary):
    """The TotalSegmentator version installed beside ``binary``, or None."""
    python = Path(binary).resolve().parent / 'python'
    if not python.exists():
        python = Path(binary).parent / 'python'
    try:
        done = subprocess.run(
            [str(python), '-c', 'import importlib.metadata as m; '
                                'print(m.version("TotalSegmentator"))'],
            capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.TimeoutExpired):
        return None
    if done.returncode != 0:
        return None
    return done.stdout.strip() or None


def _lowPriority():
    """``nice``/``ionice`` prefix, so annotators come first on a shared server."""
    prefix = []
    if shutil.which('nice'):
        prefix += ['nice', '-n', '19']
    if shutil.which('ionice'):
        prefix += ['ionice', '-c3']
    return prefix


def runTotalseg(binary, ctPath, outPath, workDir, out=print):
    """TotalSegmentator as the pool batch ran it; the low-memory retry on failure."""
    log = Path(workDir) / 'totalseg.log'
    for args in (TS_ARGS, TS_LOWMEM_ARGS):
        cmd = _lowPriority() + [str(binary)] + args + ['-i', str(ctPath), '-o', str(outPath)]
        out('  running: ' + ' '.join(cmd))
        with open(log, 'w') as handle:
            proc = subprocess.Popen(cmd, stdout=handle, stderr=subprocess.STDOUT,
                                    stdin=subprocess.DEVNULL, start_new_session=True)
            try:
                code = proc.wait(timeout=TS_TIMEOUT)
            except subprocess.TimeoutExpired:
                code = 'timeout'
            finally:
                try:
                    os.killpg(proc.pid, signal.SIGKILL)
                except OSError:
                    pass
                proc.wait()
        if code == 0 and Path(outPath).exists():
            return ' '.join(['TotalSegmentator'] + args)
        out(f'  TotalSegmentator exit {code}: '
            + log.read_text(errors='replace').strip()[-400:])
    raise SystemExit('REFUSED: TotalSegmentator failed twice; no seed made')


#: Label-volume files ``--from-girder`` considers (a ``.seg.nrrd`` ends in ``.nrrd``).
SEED_VOLUME_SUFFIXES = ('.nii.gz', '.nii', '.nrrd', '.nhdr')
#: Item metadata keys that may carry the TotalSegmentator version (lower-cased).
TS_VERSION_KEYS = ('totalsegmentator_version', 'totalseg_version', 'totalsegmentator',
                   'ts_version')


def _volumeSuffix(name):
    lower = name.lower()
    return next((s for s in SEED_VOLUME_SUFFIXES if lower.endswith(s)), None)


def _girderFolder(path):
    """The Girder folder at resource path ``path`` (e.g. ``user/christian/Public``)."""
    from girder.exceptions import GirderException, ResourcePathNotFound
    from girder.utility.path import lookUpPath

    clean = '/' + str(path).strip().strip('/')
    try:
        found = lookUpPath(clean, filter=False, force=True)
    except (GirderException, ResourcePathNotFound, IndexError) as exc:
        raise SystemExit(f'REFUSED: no Girder resource at {clean} ({exc})') from exc
    if found['model'] != 'folder':
        raise SystemExit(f"REFUSED: {clean} is a {found['model']}, not a folder")
    return found['document'], clean.lstrip('/')


def _girderCandidates(folder):
    """``[(path relative to folder, item, file)]`` for every volume under ``folder``."""
    from .populate import _childFolders

    out = []

    def walk(node, rel):
        from girder.models.folder import Folder
        from girder.models.item import Item

        for item in Folder().childItems(node):
            for fileDoc in Item().childFiles(item):
                if _volumeSuffix(fileDoc['name']):
                    name = fileDoc['name'] if fileDoc['name'] == item['name'] else \
                        f"{item['name']}/{fileDoc['name']}"
                    out.append((f'{rel}{name}', item, fileDoc))
        for child in _childFolders(node):
            walk(child, f"{rel}{child['name']}/")

    walk(folder, '')
    return sorted(out, key=lambda c: c[0])


def _listing(candidates):
    return '; '.join(f"{rel} ({fileDoc.get('size', 0)} bytes)"
                     for rel, _, fileDoc in candidates) or 'none'


def pickGirderSeed(candidates, n, fileName=None):
    """The one candidate to use: ``fileName`` if given, else the one whose name holds
    ``NNNN``, else the only volume. Refuses zero or several, listing them."""
    if fileName:
        chosen = [c for c in candidates
                  if fileName in (c[0], c[2]['name'], c[1]['name'])]
        why = f'named {fileName!r}'
    else:
        tag = f'{int(n):04d}'
        chosen = [c for c in candidates if tag in c[2]['name'] or tag in c[1]['name']]
        why = f'with {tag} in the name'
        if not chosen:
            chosen, why = candidates, 'there (none has the case id in its name)'
    if len(chosen) != 1:
        raise SystemExit(
            f'REFUSED: {len(chosen)} label volume(s) {why}; pass --from-girder-file <name>. '
            f'Volumes: {_listing(candidates)}')
    return chosen[0]


def tsVersionOf(path, meta=None):
    """The TotalSegmentator version recorded in the file's header or item metadata."""
    import re

    import SimpleITK as sitk

    pattern = re.compile(r'(?i)totalseg\w*\D{0,3}v?(\d+\.\d+(?:\.\d+)?)')
    for key, value in (meta or {}).items():
        if str(key).lower() in TS_VERSION_KEYS:
            match = re.search(r'\d+\.\d+(?:\.\d+)?', str(value))
            if match:
                return match.group(0)
    try:
        reader = sitk.ImageFileReader()
        reader.SetFileName(str(path))
        reader.ReadImageInformation()
        texts = [f'{k} {reader.GetMetaData(k)}' for k in reader.GetMetaDataKeys()]
    except RuntimeError:
        return None
    for text in texts:
        match = pattern.search(text)
        if match:
            return match.group(1)
    return None


def girderSeedSource(where, version):
    return (f'TotalSegmentator coronary_arteries (binary), version {version or "unknown"}, '
            f'supplied by the lead from {where}')


def runSeed(apply=False, totalseg=None, seedFile=None, fromGirder=None, fromGirderFile=None,
            out=print):
    """Give the benchmark case its seed. Returns a summary dict."""
    from girder.models.file import File
    from girder.models.item import Item
    from girder.models.upload import Upload

    from .models import Submission14
    from .populate import _firstFile

    sources = [bool(totalseg), bool(seedFile), bool(fromGirder)]
    if sum(sources) > 1:
        raise SystemExit('REFUSED: pass one of --totalseg, --seed-file or --from-girder')
    if fromGirderFile and not fromGirder:
        raise SystemExit('REFUSED: --from-girder-file needs --from-girder <folder path>')
    case = _case()
    n = sqbench.imagecas_id_of(case['name'])
    if case.get('seedFileId'):
        out(f"{case['name']} has its seed already ({case.get('seedSource') or '?'}); "
            'nothing to do.')
        return {'seed': 'present'}
    if Submission14().collection.count_documents({'caseId': case['_id']}):
        raise SystemExit('REFUSED: the case has submissions; its starting point cannot change')
    folder = _seedsFolder()
    if folder is None:
        raise SystemExit(f'REFUSED: no {LIVE_COLLECTION_NAME}/{SEEDS_FOLDER} folder')
    existing = _seedItem(n)
    if existing is not None and _firstFile(existing) is not None:
        out(f"{seedName(n)} is in {SEEDS_FOLDER} already; "
            + ('attached.' if apply else '--apply attaches it.'))
        if apply:
            _attachSeed(case, _firstFile(existing)['_id'])
        return {'seed': 'attached' if apply else 'found'}
    if not any(sources):
        raise SystemExit('REFUSED: pass --totalseg <TotalSegmentator executable>, '
                         '--seed-file <mask on the CT grid> or --from-girder <folder path>')
    picked = None
    if fromGirder:
        gFolder, gPath = _girderFolder(fromGirder)
        candidates = _girderCandidates(gFolder)
        out(f'{gPath}: {len(candidates)} label volume(s): {_listing(candidates)}')
        picked = pickGirderSeed(candidates, n, fromGirderFile)
        out(f"using {gPath}/{picked[0]} ({picked[2].get('size', 0)} bytes)")
    ct = File().load(case['fileId'], force=True)
    if ct is None:
        raise SystemExit(f"REFUSED: {case['name']}'s CT is missing from storage")

    if totalseg:
        version = totalsegVersion(totalseg)
        out(f'TotalSegmentator at {totalseg}: version {version or "not found"}')
        if version != TOTALSEG_VERSION:
            raise SystemExit(f'REFUSED: the pool seeds were made with TotalSegmentator '
                             f'{TOTALSEG_VERSION}; this is {version or "not installed"}')
        if not apply:
            out(f"dry run: would segment {ct['name']} on CPU (minutes, at nice 19) and upload "
                f'{seedName(n)}. --apply does it.')
            return {'seed': 'would run'}

    work = tempfile.mkdtemp(prefix='sq14-benchmark-')
    try:
        ctPath = Path(work) / 'ct.nii.gz'
        with open(ctPath, 'wb') as handle:
            for chunk in File().download(ct, headers=False)():
                handle.write(chunk)
        grid = _grid(ctPath)
        if float(grid[0][0]) * grid[0][1] * grid[0][2] > LARGE_VOXELS:
            raise SystemExit(f'REFUSED: {grid[0]} voxels; the pool batch made seeds this large '
                             'on a 0.8 mm copy, which this step does not do')
        seedSource, extraMeta = sqplan.SEED_SOURCE_TOTALSEG, {}
        if totalseg:
            made = Path(work) / 'seg.nii.gz'
            command = runTotalseg(totalseg, ctPath, made, work, out=out)
            source = f'TotalSegmentator {TOTALSEG_VERSION}: {command}'
        elif picked is not None:
            rel, gItem, gFile = picked
            # A copy: the lead's file is only read, never changed, moved or deleted.
            made = Path(work) / ('girder-seed' + _volumeSuffix(gFile['name']))
            with open(made, 'wb') as handle:
                for chunk in File().download(gFile, headers=False)():
                    handle.write(chunk)
            version = tsVersionOf(made, gItem.get('meta'))
            out(f'TotalSegmentator version in its metadata: {version or "unknown"}')
            where = f'{gPath}/{rel}'
            source = seedSource = girderSeedSource(where, version)
            extraMeta = {'from_girder': where, 'from_girder_file_id': str(gFile['_id']),
                         'from_girder_sha256': _sha256(made),
                         'totalseg_version': version or 'unknown'}
        else:
            made, source = Path(seedFile), f'supplied file {Path(seedFile).name}'
        final = Path(work) / seedName(n)
        stats = binarise(made, ctPath, final)
        out(f"seed: {stats['voxels']} voxels, {stats['volume_ml']} ml, on the CT's grid "
            f"({' x '.join(str(v) for v in grid[0])} voxels, spacing "
            f"{', '.join(f'{v:.4g}' for v in grid[1])} mm)")
        out(f'seedSource: {seedSource}')
        if not apply:
            out(f'dry run: would upload {seedName(n)} and attach it. --apply does it.')
            return {'seed': 'would upload', 'seedSource': seedSource, **stats}
        admin = _admin()
        with open(final, 'rb') as handle:
            fileDoc = Upload().uploadFromFile(
                handle, size=os.path.getsize(final), name=seedName(n), parentType='folder',
                parent=folder, user=admin, mimeType='application/gzip')
        item = Item().load(fileDoc['itemId'], force=True)
        Item().setMetadata(item, {
            'source': 'ImageCAS-X', 'imagecas_id': n, 'segqueue14_case': case['name'],
            'seed_source': seedSource, 'made_by': source,
            'role': 'annotator benchmark seed (D43)', **extraMeta, **stats})
        if not _attachSeed(case, fileDoc['_id'], seedSource):
            out('note: the case got a seed meanwhile; the upload is kept but not attached')
        out(f'uploaded {seedName(n)} and attached it to {case["name"]}')
        return {'seed': 'uploaded', 'seedSource': seedSource, **stats}
    finally:
        shutil.rmtree(work, ignore_errors=True)


# ------------------------------------------------------------------ assign


def _logins(text):
    return [part.strip().lower() for part in (text or '').split(',') if part.strip()]


def runAssign(exclude, logins=None, retest=False, apply=False, out=print):
    """Invite annotators to the benchmark. Returns ``{login: what happened}``."""
    from girder.models.group import Group
    from girder.models.user import User

    from .models import Assignment14, Case14

    if exclude is None:
        raise SystemExit('REFUSED: --exclude is required: name the logins that must not get '
                         'the benchmark (an empty value leaves nobody out)')
    case = _case()
    if case.get('retired'):
        raise SystemExit(f"REFUSED: {case['name']} is retired")
    if not case.get('seedFileId'):
        raise SystemExit(f"REFUSED: {case['name']} has no seed yet; run "
                         '`segqueue14-benchmark seed` first')
    excluded = set(_logins(exclude))
    unknown = sorted(login for login in excluded if User().findOne({'login': login}) is None)
    if unknown:
        raise SystemExit(f"REFUSED: no such login(s) in --exclude: {', '.join(unknown)}")
    group = Group().findOne({'name': ANNOTATOR_GROUP})
    members = {u['login'].lower(): u for u in Group().listMembers(group)} if group else {}
    wanted = _logins(logins) if logins else None
    if wanted:
        missing = sorted(login for login in wanted if login not in members)
        if missing:
            raise SystemExit(f"REFUSED: not in {ANNOTATOR_GROUP}: {', '.join(missing)}")
    pending = set(case.get('benchmarkPending') or [])
    result = {}
    for login in sorted(wanted or members):
        user = members[login]
        if login in excluded:
            if user['_id'] in pending:
                if apply:
                    Case14().collection.update_one(
                        {'_id': case['_id']}, {'$pull': {'benchmarkPending': user['_id']}})
                result[login] = 'excluded; invitation withdrawn'
            else:
                result[login] = 'excluded'
            continue
        if user.get('status') == 'disabled':
            result[login] = 'skipped: account disabled'
            continue
        history = Assignment14().benchmarkHistory(case['_id'], user['_id'])
        holding = [a for a in history if a['state'] in st.OPEN_STATES]
        done = [a for a in history if a['state'] in (st.SUBMITTED, st.UNDER_REVIEW, st.APPROVED)]
        if user['_id'] in pending:
            result[login] = 'already invited'
        elif holding:
            result[login] = f"has it now (attempt {holding[-1].get('benchmarkAttempt', '?')})"
        elif done and not retest:
            result[login] = f'benchmarked ({len(done)} attempt(s)); --retest for another'
        else:
            if apply:
                Case14().invite(case['_id'], user['_id'])
                Case14().collection.update_one({'_id': case['_id']}, {'$push': {
                    'benchmarkInvites': {'userId': user['_id'], 'login': login,
                                         'retest': bool(done), 'at': _now()}}})
            verb = 'invited' if apply else 'would invite'
            result[login] = f'{verb}' + (f' (retest; attempt {len(history) + 1})' if done else '')
    for login, what in result.items():
        out(f'  {login}: {what}')
    if not apply:
        out('dry run: nothing written. --apply sends the invitations.')
    return result


# ------------------------------------------------------------------ status


def _score(assignment):
    from .models import Submission14
    from .models.submission import ANNOTATOR

    submission = Submission14().findOne(
        {'assignmentId': assignment['_id'], 'authorRole': ANNOTATOR}, sort=[('created', -1)])
    if submission is None:
        return None, None
    ref = (submission.get('autoScore') or {}).get('reference') or {}
    perClass = {name: ((ref.get('per_structure') or {}).get(name) or {}).get('dice')
                for name in sqlabels.NAMES}
    return submission, {'mean_dice': ref.get('mean_dice'), 'per_class_dice': perClass,
                        'scored': bool(submission.get('scored')),
                        'error': ref.get('error')}


def runStatus(asJson=False, out=print):
    from girder.models.user import User

    from .models import Assignment14

    case = _case(required=False)
    if case is None:
        out('No annotator benchmark case yet.')
        return {'case': None}
    pick = case.get('benchmarkPick') or {}
    users = {}

    def login(userId):
        if userId not in users:
            users[userId] = (User().load(userId, force=True) or {}).get('login', str(userId))
        return users[userId]

    rows = []
    for a in Assignment14().benchmarkHistory(case['_id']):
        submission, score = _score(a)
        rows.append({
            'login': login(a['userId']), 'attempt': a.get('benchmarkAttempt'),
            'state': a['state'],
            'assignedAt': a.get('assignedAt').isoformat() if a.get('assignedAt') else None,
            'submittedAt': a.get('submittedAt').isoformat() if a.get('submittedAt') else None,
            'score': score})
    summary = {'case': case['name'], 'imagecasId': pick.get('imagecasId'),
               'why': pick.get('why'), 'seed': bool(case.get('seedFileId')),
               'reference': bool(case.get('referenceFileId')),
               'pending': sorted(login(u) for u in case.get('benchmarkPending') or []),
               'attempts': rows}
    if asJson:
        out(json.dumps(summary, indent=1, default=str))
        return summary
    out(f"{case['name']}: seed {'yes' if summary['seed'] else 'NO'}, reference "
        f"{'yes' if summary['reference'] else 'NO'}; {pick.get('why', '')}")
    out(f"invited, not yet served: {', '.join(summary['pending']) or 'nobody'}")
    head = ['login', 'try', 'state', 'submitted', 'mean'] + list(sqlabels.NAMES)
    out('  '.join(f'{h:>10}' for h in head))
    for row in sorted(rows, key=lambda r: (r['login'], r['attempt'] or 0)):
        score = row['score'] or {}
        dice = [score.get('mean_dice')] + [(score.get('per_class_dice') or {}).get(n)
                                           for n in sqlabels.NAMES]
        cells = [row['login'], str(row['attempt'] or '?'), row['state'],
                 (row['submittedAt'] or '-')[:10]]
        cells += ['-' if d is None else f'{d:.3f}' for d in dice]
        if score and not score.get('scored'):
            cells[4] = 'pending'
        out('  '.join(f'{c:>10}' for c in cells))
    return summary


# --------------------------------------------------------------------- CLI


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-benchmark',
        description='The annotator benchmark (D43): one fixed ImageCAS-X case, served to '
                    'every annotator but the ones excluded, scored on its own against '
                    'ImageCAS-X. Writes only with --apply.')
    sub = parser.add_subparsers(dest='step', required=True)

    def common(p, writes=True):
        p.add_argument('--repo', default=None,
                       help=f'Repository checkout with the pinned lists (default: ${REPO_ENV}, '
                            '$JANUSM_REPO, the current directory, or this install).')
        if writes:
            p.add_argument('--apply', action='store_true', help='Write. Default: a dry run.')

    p = sub.add_parser('pick', help='The draw from the repository alone; no database.')
    common(p, writes=False)
    p.add_argument('--twins-file', default=None,
                   help='ImageCAS-X cases that may be in TotalSegmentator\'s training data '
                        '(none exists in the project).')
    p = sub.add_parser('create', help='Create the benchmark case, or show the one there is.')
    common(p)
    p.add_argument('--twins-file', default=None)
    p = sub.add_parser('seed', help='Give the case its TotalSegmentator seed.')
    common(p)
    p.add_argument('--totalseg', default=None,
                   help=f'TotalSegmentator {TOTALSEG_VERSION} executable (its own venv).')
    p.add_argument('--seed-file', default=None,
                   help='A seed made elsewhere the same way, on the CT\'s grid.')
    p.add_argument('--from-girder', default=None, metavar='FOLDER',
                   help='Take the seed from this Girder folder (a resource path such as '
                        'user/christian/Public): the volume whose name holds the case\'s '
                        'ImageCAS id, else the only one. It is copied, never changed.')
    p.add_argument('--from-girder-file', default=None, metavar='NAME',
                   help='With --from-girder: the file to use, by name (or path in the folder).')
    p = sub.add_parser('assign', help='Make it the next case for annotators.')
    common(p)
    p.add_argument('--exclude', default=None, required=True,
                   help='Comma-separated logins that never get it (required; may be "").')
    p.add_argument('--login', default=None, help='Only these logins (comma-separated).')
    p.add_argument('--retest', action='store_true',
                   help='A fresh attempt for annotators who have done it already.')
    p = sub.add_parser('status', help='Who has it, and each attempt\'s Dice.')
    common(p, writes=False)
    p.add_argument('--json', action='store_true')
    return parser


def main(argv=None):  # pragma: no cover - CLI entry point
    args = buildParser().parse_args(argv)
    if args.step == 'pick':
        runPick(args.repo, args.twins_file)
        return 0
    if args.repo:
        os.environ.setdefault(REPO_ENV, args.repo)
    if args.step == 'create':
        runCreate(apply=args.apply, root=args.repo, twinsFile=args.twins_file)
    elif args.step == 'seed':
        runSeed(apply=args.apply, totalseg=args.totalseg, seedFile=args.seed_file,
                fromGirder=args.from_girder, fromGirderFile=args.from_girder_file)
    elif args.step == 'assign':
        runAssign(args.exclude, logins=args.login, retest=args.retest, apply=args.apply)
    elif args.step == 'status':
        runStatus(asJson=args.json)
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
