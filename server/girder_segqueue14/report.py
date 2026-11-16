"""``segqueue14-report quality`` -- how good are the annotations coming in (#296);
``segqueue14-report readers`` -- which cases have more annotators than they want, and
why (#334; see ``collectReaders``).

Read-only. It reads SegQueue14's Mongo collections through plain ``find`` queries
(no Girder model is instantiated for the pool part, so not even an index is
created) and reads segmentation and seed files straight from the assetstore; it
never writes to Mongo or to the assetstore. Run on the server, like
``segqueue14-benchmark status``::

    segqueue14-report quality [--limit N] [--exclude LOGIN,...] [--json]
    segqueue14-report readers [--min N] [--json]

**Per annotator** (Girder login), over annotator submissions to pool cases; the
annotator benchmark (D43) is left out of every pool number and shown on its own at
the end, as ``segqueue14-benchmark status`` prints it:

* reads submitted, approved, sent back (rejected by a reviewer), under review, and
  revised by a reviewer; median ``annotationSeconds`` per read;
* pair agreement on two-read cases, from the stored scores
  (``autoScore.duplicate``): mean, median and range of the pair mean Dice, mean
  per-class Dice, and how many pairs fall below the ``duplicate_mean_dice_flag``;
* flags, grouped by reason (``autoScore.flags``);
* seeds left untrimmed (the D39 risk): each class mask compared with the case's
  seed -- the fraction of the seed it keeps and its Dice with the seed. A read in
  which two or more classes keep more than ``UNTRIMMED_KEEP`` of the seed was
  probably submitted untrimmed (the figures and tables: ``segqueue14.quality``);
* overlap: the fraction of labelled voxels in two or more classes, per read;
* empty classes: reads with an empty LM, LAD, LCx or RCA;
* extended reads: reads with the optional extended classes (D44). Every figure
  here is over the four classes: an extended read is collapsed first, each branch
  into its parent (``labels.collapse_to_four``);
* PDA/PLB/SN fallbacks (D47 Q1): in the collapse, PDA, PLB and SN go to the vessel
  they leave, by contact; ``rca fallback`` counts the scored reads with a
  component that touched neither RCA nor LCx (or both equally) and so went to RCA,
  from the stored scores (``autoScore.branchParents``).

**Project:** assignments by state, overall and per login; each pool case's
``approvedCount`` against its number of approved assignments (a mismatch is an
accounting problem, not an annotation one); cases with 0, 1 or 2+ reads; pairs
scored; and the reads most worth a reviewer's eye.

``--exclude`` leaves logins out entirely (#299): their submissions, assignments and
sent-back reviews are dropped before anything is counted, a pair whose partner is
excluded is not scored (the case counts as single-read), and the benchmark table
drops them too. The ``approvedCount`` check alone still runs over every login: it is
a data-integrity check, not a quality figure.

The seed and overlap figures need the files, so only the ``--limit`` newest reads
are opened (``DEFAULT_LIMIT``; 0 opens none); everything else comes from the
database. The deploy step runs this at nice 19 / ionice idle.

Output names cases and logins only: no patient identifiers beyond the case names,
no file names, no image data.
"""

import argparse
import contextlib
import json
import os
import shutil
import statistics
import sys
import tempfile

from segqueue import states as st
from segqueue14 import labelfile, labels
from segqueue14 import plan as sqplan
from segqueue14.quality import (
    ASSIGNMENT_STATES,
    DEFAULT_PAIR_FLAG,
    EYE_ROWS,
    NAMES,
    REASONS,
    flagReason,
    meanOf,
    render,
    seedComparison,
    summary,
    usable,
)

from .constants import SETTING_REFERENCE

#: Reads whose files are opened, newest first, unless ``--limit`` says otherwise.
DEFAULT_LIMIT = 100
ANNOTATOR = 'annotator'
REVIEWER = 'reviewer'


# ---------------------------------------------------------- the database


def _objectId(value):
    from bson import ObjectId
    from bson.errors import InvalidId

    try:
        return ObjectId(str(value))
    except (InvalidId, TypeError):
        return None


def pairScore(submission):
    """The stored pair score of a submission (``autoScore.duplicate``), if usable."""
    pair = (submission.get('autoScore') or {}).get('duplicate') or {}
    if pair.get('error') or not usable(pair.get('mean_dice')):
        return None
    return pair


# ---------------------------------------------------------- the database


def _database():
    """Girder's database, as a plain pymongo handle (no model, so no index writes)."""
    from girder.models import getDbConnection

    return getDbConnection().get_database()


def _pairFlag(db):
    stored = (db['setting'].find_one({'key': SETTING_REFERENCE}) or {}).get('value') or {}
    flag = stored.get('duplicate_mean_dice_flag')
    return float(flag) if usable(flag) else DEFAULT_PAIR_FLAG


def _suffix(name):
    name = (name or '').lower()
    for suffix in ('.seg.nrrd', '.nii.gz', '.nrrd', '.nii'):
        if name.endswith(suffix):
            return suffix
    return '.nrrd'


@contextlib.contextmanager
def localFile(db, fileId):
    """A path to a Girder file's bytes, named with its type's suffix (ITK reads by it).

    A filesystem assetstore's file is linked, never copied; any other assetstore
    is streamed to a temporary file. Neither touches the assetstore or Mongo.
    """
    fileDoc = db['file'].find_one({'_id': fileId})
    if fileDoc is None:
        raise LookupError('file missing')
    store = db['assetstore'].find_one({'_id': fileDoc.get('assetstoreId')})
    if store is None:
        raise LookupError('assetstore missing')
    work = tempfile.mkdtemp(prefix='sq14-report-')
    path = os.path.join(work, 'f' + _suffix(fileDoc.get('name')))
    try:
        from girder.constants import AssetstoreType

        if store.get('type') == AssetstoreType.FILESYSTEM and fileDoc.get('path'):
            os.symlink(os.path.join(store['root'], fileDoc['path']), path)
        else:
            from girder.utility.assetstore_utilities import getAssetstoreAdapter

            stream = getAssetstoreAdapter(store).downloadFile(fileDoc, headers=False)
            with open(path, 'wb') as out:
                for chunk in stream():
                    out.write(chunk)
        yield path
    finally:
        shutil.rmtree(work, ignore_errors=True)


def _readImage(db, fileId):
    import SimpleITK as sitk

    with localFile(db, fileId) as path:
        if labelfile.sniff(path) == labelfile.FORMAT_CLASS_STACK:
            from .scoring import classStackImages

            return classStackImages(path)
        return sitk.ReadImage(path)


def analyseRead(db, submission, case, seedCache=None):
    """``seedComparison`` of one stored read against its case's seed, on the seed's grid."""
    import numpy as np
    import SimpleITK as sitk

    from .scoring import _gridOf, masksOnGrid

    read = _readImage(db, submission['fileId'])
    seedId = case.get('seedFileId')
    seedImage = None
    if seedId is not None:
        cache = seedCache if seedCache is not None else {}
        if seedId not in cache:
            cache.clear()  # one seed in memory at a time
            cache[seedId] = _readImage(db, seedId)
        seedImage = cache[seedId]
        if isinstance(seedImage, list):
            seedImage = seedImage[0]
    grid = seedImage if seedImage is not None else _gridOf(read)
    masks = masksOnGrid(read, grid)
    seed = None
    if seedImage is not None:
        seed = np.asarray(sitk.GetArrayViewFromImage(seedImage)) != 0
    return seedComparison(masks, seed)


def collect(db, limit=DEFAULT_LIMIT, analyse=None, exclude=()):
    """Every figure of the report, as one dict. ``analyse(submission, case)`` opens a
    read's files (default ``analyseRead``); it is called for the ``limit`` newest.
    ``exclude``: logins left out of every figure but the approvedCount check."""
    excluded = set(exclude or ())
    logins = {}

    def login(userId):
        if userId not in logins:
            doc = db['user'].find_one({'_id': userId}, {'login': 1}) or {}
            logins[userId] = doc.get('login') or str(userId)
        return logins[userId]

    def kept(userId):
        return not excluded or login(userId) not in excluded

    benchmarkIds = [c['_id'] for c in db['segqueue14_case'].find({'benchmark': True}, {'_id': 1})]
    cases = {c['_id']: c for c in db['segqueue14_case'].find(
        {'benchmark': {'$ne': True}},
        {'name': 1, 'seedFileId': 1, 'replicasWanted': 1, 'retired': 1, 'approvedCount': 1})}
    pool = {'kind': {'$ne': sqplan.KIND_BENCHMARK}, 'caseId': {'$nin': benchmarkIds}}
    submissions = list(db['segqueue14_submission'].find(pool, {
        'assignmentId': 1, 'caseId': 1, 'userId': 1, 'authorRole': 1, 'revisionOf': 1,
        'fileId': 1, 'annotationSeconds': 1, 'voxelCounts': 1, 'autoScore': 1,
        'created': 1, 'reopenedAt': 1}, sort=[('created', -1), ('_id', -1)]))
    submissions = [s for s in submissions if s['caseId'] in cases]
    # Every pool submission, excluded logins' too: to tell whose a pair partner is.
    everyById = {s['_id']: s for s in submissions}
    # A read reopened for its annotator's own revision (#315) is history, not a
    # read, until the resubmission replaces it.
    submissions = [s for s in submissions if kept(s['userId']) and not s.get('reopenedAt')]
    reads = [s for s in submissions if s.get('authorRole', ANNOTATOR) == ANNOTATOR]
    revisions = [s for s in submissions if s.get('authorRole') == REVIEWER]
    everyAssignment = [a for a in db['segqueue14_assignment'].find(
        pool, {'userId': 1, 'state': 1, 'caseId': 1}) if a['caseId'] in cases]
    assignments = [a for a in everyAssignment if kept(a['userId'])]
    sentBack = [r for r in db['segqueue14_review'].find(
        {'verdict': 'reject', 'caseId': {'$nin': benchmarkIds}}, {'annotatorId': 1})
        if r.get('annotatorId') is None or kept(r['annotatorId'])]

    def pairOf(submission):
        """``pairScore``, unless the partner read is an excluded login's."""
        pair = pairScore(submission)
        if pair is None:
            return pair
        partner = everyById.get(_objectId(pair.get('partnerSubmissionId')))
        if partner is not None and partner.get('reopenedAt'):
            return None  # paired with a reopened read (#315): not a pair any more
        if partner is not None and excluded and not kept(partner['userId']):
            return None
        return pair

    people = {}

    def person(userId):
        return people.setdefault(login(userId), {
            'reads': 0, 'approved': 0, 'sentBack': 0, 'underReview': 0, 'revised': 0,
            'seconds': [], 'pairs': [], 'flagged': 0, 'extended': 0, 'branchFallback': 0,
            'flags': {reason: 0 for reason in REASONS}, 'analysed': [],
            'empty': {name: 0 for name in NAMES}})

    # Who submitted, approved, was sent back, is waiting, was revised.
    submittedAssignments = {s['assignmentId'] for s in reads}
    for a in assignments:
        if a['_id'] not in submittedAssignments:
            continue
        if a['state'] == st.APPROVED:
            person(a['userId'])['approved'] += 1
        elif a['state'] in (st.SUBMITTED, st.UNDER_REVIEW):
            person(a['userId'])['underReview'] += 1
    for review in sentBack:
        if review.get('annotatorId') is not None:
            person(review['annotatorId'])['sentBack'] += 1
    byId = {s['_id']: s for s in submissions}
    for revision in revisions:
        original = byId.get(revision.get('revisionOf'))
        if original is not None:
            person(original['userId'])['revised'] += 1

    # Every pool assignment by state, overall and per login.
    states = {'all': {state: 0 for state in ASSIGNMENT_STATES}}
    for a in assignments:
        for key in ('all', login(a['userId'])):
            row = states.setdefault(key, {state: 0 for state in ASSIGNMENT_STATES})
            row[a['state']] = row.get(a['state'], 0) + 1
    # The case's approvedCount should be the number of its approved assignments. A
    # data-integrity check, so over every login, excluded ones too.
    approvedByCase = {}
    for a in everyAssignment:
        if a['state'] == st.APPROVED:
            approvedByCase[a['caseId']] = approvedByCase.get(a['caseId'], 0) + 1
    mismatched = sorted(
        (c['name'], int(c.get('approvedCount') or 0), approvedByCase.get(c['_id'], 0))
        for c in cases.values()
        if int(c.get('approvedCount') or 0) != approvedByCase.get(c['_id'], 0))
    consistency = {'mismatches': len(mismatched),
                   'examples': [{'case': n, 'approvedCount': have, 'approvedAssignments': want}
                                for n, have, want in mismatched[:EYE_ROWS]]}

    # One latest read per (annotator, case) for the pair figures.
    latest = {}
    for s in reads:  # newest first
        latest.setdefault((s['userId'], s['caseId']), s)
    pairFlag = _pairFlag(db)
    pairKeys = set()
    lowPairs = []
    for s in latest.values():
        pair = pairOf(s)
        if pair is None:
            continue
        perClass = {n: ((pair.get('per_structure') or {}).get(n) or {}).get('dice') for n in NAMES}
        person(s['userId'])['pairs'].append({'mean': pair['mean_dice'], 'perClass': perClass})
        key = frozenset((str(s['_id']), str(pair.get('partnerSubmissionId'))))
        if key not in pairKeys:
            pairKeys.add(key)
            partner = byId.get(_objectId(pair.get('partnerSubmissionId')))
            who = sorted({login(s['userId'])}
                         | ({login(partner['userId'])} if partner else set()))
            if pair['mean_dice'] < pairFlag:
                lowPairs.append((pair['mean_dice'], cases[s['caseId']]['name'], who))

    # Per read: time, flags, empty classes; files for the newest `limit`.
    if analyse is None:
        seedCache = {}

        def analyse(sub, case):
            return analyseRead(db, sub, case, seedCache)

    perRead = []
    for index, s in enumerate(reads):
        p = person(s['userId'])
        p['reads'] += 1
        # Reads with the optional extended classes (D44); scored collapsed to four.
        if s.get('extended') or labels.is_extended(s.get('classes') or ()):
            p['extended'] += 1
        # PDA/PLB/SN that went to RCA only because they touched neither vessel (D47).
        if ((s.get('autoScore') or {}).get('branchParents') or {}).get('fallback'):
            p['branchFallback'] += 1
        if usable(s.get('annotationSeconds')) and s['annotationSeconds'] > 0:
            p['seconds'].append(float(s['annotationSeconds']))
        score = s.get('autoScore') or {}
        flags = score.get('flags') or []
        if flags:
            p['flagged'] += 1
            for reason in sorted({flagReason(f) for f in flags}):
                p['flags'][reason] += 1
        row = {'case': cases[s['caseId']]['name'], 'login': login(s['userId']),
               'created': s.get('created').isoformat() if s.get('created') else None,
               'flags': sorted({flagReason(f) for f in flags}),
               'pairMeanDice': (pairOf(s) or {}).get('mean_dice')}
        figures = None
        if limit and index < limit and s.get('fileId') is not None:
            try:
                figures = analyse(s, cases[s['caseId']])
            except Exception as exc:  # report it, never stop the report
                row['error'] = type(exc).__name__
        if figures is not None:
            row.update(figures)
            p['analysed'].append(figures)
            counts = figures['counts']
        else:
            counts = score.get('voxelCounts') or s.get('voxelCounts') or {}
        row['empty'] = [n for n in NAMES if n in counts and not counts[n]]
        for name in row['empty']:
            p['empty'][name] += 1
        perRead.append(row)

    # Project totals: readers per pool case.
    readers = {}
    for s in reads:
        readers.setdefault(s['caseId'], set()).add(s['userId'])
    live = [c for c in cases.values() if not c.get('retired')]
    totals = {'cases': len(live),
              'reads0': sum(1 for c in live if not readers.get(c['_id'])),
              'reads1': sum(1 for c in live if len(readers.get(c['_id'], ())) == 1),
              'reads2': sum(1 for c in live if len(readers.get(c['_id'], ())) >= 2),
              'pairsScored': len(pairKeys), 'reads': len(reads),
              'analysed': sum(1 for r in perRead if 'counts' in r), 'limit': limit,
              'pairFlag': pairFlag}

    annotators = {}
    for name, p in sorted(people.items()):
        means = [x['mean'] for x in p['pairs']]
        analysed = p['analysed']
        seeded = [f for f in analysed if f.get('kept')]
        annotators[name] = {
            'reads': p['reads'], 'approved': p['approved'], 'sentBack': p['sentBack'],
            'underReview': p['underReview'], 'revisedByReviewer': p['revised'],
            'extended': p['extended'], 'branchFallback': p['branchFallback'],
            'medianSeconds': round(statistics.median(p['seconds']), 1) if p['seconds'] else None,
            'pairs': dict(summary(means), below=sum(1 for m in means if m < pairFlag),
                          perClass={n: meanOf([x['perClass'][n] for x in p['pairs']])
                                    for n in NAMES}),
            'flagged': p['flagged'], 'flags': p['flags'],
            'analysed': len(analysed), 'seeded': len(seeded),
            'keptMean': {n: meanOf([f['kept'][n] for f in seeded]) for n in NAMES},
            'copies2': sum(1 for f in seeded if len(f['copies']) >= 2),
            'untrimmed': sum(1 for f in seeded if f['untrimmed']),
            'overlapReads': sum(1 for f in analysed if f['overlapFraction'] > 0),
            'overlapMedian': (round(statistics.median([f['overlapFraction'] for f in analysed]), 4)
                              if analysed else None),
            'overlapMax': max((f['overlapFraction'] for f in analysed), default=None),
            'empty': p['empty'],
        }

    eye = {
        'lowestPairDice': [{'case': c, 'logins': who, 'meanDice': m}
                           for m, c, who in sorted(lowPairs)[:EYE_ROWS]],
        'mostOverlap': [{'case': r['case'], 'login': r['login'],
                         'overlapFraction': r['overlapFraction']}
                        for r in sorted((r for r in perRead if r.get('overlapFraction')),
                                        key=lambda r: -r['overlapFraction'])[:EYE_ROWS]],
        'likelyUntrimmed': [{'case': r['case'], 'login': r['login'],
                             'classes': r['keptAbove']}
                            for r in perRead if r.get('untrimmed')][:2 * EYE_ROWS],
    }
    report = {'annotators': annotators, 'totals': totals, 'eye': eye, 'reads': perRead,
              'assignmentStates': states, 'approvedCount': consistency}
    if excluded:
        report['excluded'] = sorted(excluded)
    return report


def runQuality(limit=DEFAULT_LIMIT, asJson=False, out=print, db=None, analyse=None,
               exclude=()):
    db = _database() if db is None else db
    report = collect(db, limit=limit, analyse=analyse, exclude=exclude)
    from . import benchmark

    benchmarkLines = []
    if asJson:
        report['benchmark'] = benchmark.runStatus(asJson=True, out=lambda _: None,
                                                  exclude=exclude)
        out(json.dumps(report, indent=1, default=str))
        return report
    benchmark.runStatus(out=benchmarkLines.append, exclude=exclude)
    for line in render(report, benchmarkLines):
        out(line)
    return report


# ---------------------------------------------------- readers (#334)

#: How a case's slot came free, in the order the report names them.
CAUSES = ('return-to-pool', 'release', 'expired', 'reopen', 'benchmark', 'other/unexplained')
#: A case with no more annotators than it wants (only with ``--min`` at or below
#: ``replicasWanted``): nothing to explain.
WITHIN_WANTED = 'within-replicasWanted'
DEFAULT_MIN_READERS = 3
#: What the lease sweep records (``policy.reclaim_reason``, ``maintenance.sweep``).
EXPIRE_REASONS = ('lease of ', 'no heartbeat for ', 'lease lapsed')
#: What ``rest/review.py`` ``returnToPool`` records when the reviewer gives no reason.
RETURN_REASON = 'returned to the pool'
STATE_LABELS = {'return-to-pool': 'returned to pool', 'release': 'released',
                'expired': 'expired'}
TIME_ZONE = 'America/New_York'


def _eastern(dt):
    """A Mongo datetime (naive means UTC) as ``YYYY-MM-DD HH:MM EST``, or None."""
    if dt is None:
        return None
    import datetime
    from zoneinfo import ZoneInfo

    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return dt.astimezone(ZoneInfo(TIME_ZONE)).strftime('%Y-%m-%d %H:%M %Z')


def _sortKey(dt):
    """Naive and aware datetimes compare as UTC; None sorts last."""
    import datetime

    if dt is None:
        return (1, 0.0)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=datetime.timezone.utc)
    return (0, dt.timestamp())


def freedBy(assignment):
    """How a released assignment gave up its slot: ``return-to-pool``, ``expired`` or
    ``release``; None if it has not (it is open, or approved).

    The assignment does not store its last event, so this reads what each path
    leaves: ``returnToPool`` sets ``reviewerId`` (and, without a reason, its default
    ``releaseReason``); the lease sweep's ``releaseReason`` is
    ``policy.reclaim_reason``'s; anything else released is an annotator's release
    (or an admin's, which is the same ``release`` event).
    """
    if assignment.get('state') != st.RELEASED:
        return None
    reason = assignment.get('releaseReason') or ''
    if assignment.get('reviewerId') is not None or reason.startswith(RETURN_REASON):
        return 'return-to-pool'
    if reason.startswith(EXPIRE_REASONS):
        return 'expired'
    return 'release'


def collectReaders(db, minLogins=DEFAULT_MIN_READERS):
    """Cases with at least ``minLogins`` distinct annotator logins, and why (#334).

    Read-only: plain ``find`` queries, nothing written, no index created.
    """
    logins = {}

    def login(userId):
        if userId not in logins:
            doc = db['user'].find_one({'_id': userId}, {'login': 1}) or {}
            logins[userId] = doc.get('login') or str(userId)
        return logins[userId]

    cases = {c['_id']: c for c in db['segqueue14_case'].find({}, {
        'name': 1, 'replicasWanted': 1, 'activeCount': 1, 'approvedCount': 1,
        'benchmark': 1, 'retired': 1})}
    byCase = {}
    for a in db['segqueue14_assignment'].find({}, {
            'caseId': 1, 'userId': 1, 'state': 1, 'assignedAt': 1, 'submittedAt': 1,
            'decidedAt': 1, 'releasedAt': 1, 'releaseReason': 1, 'reviewerId': 1,
            'reopenedAt': 1, 'attempt': 1}):
        byCase.setdefault(a['caseId'], []).append(a)
    reads = {}  # assignmentId -> annotator submissions, oldest first
    for s in db['segqueue14_submission'].find(
            {'authorRole': {'$ne': REVIEWER}},
            {'assignmentId': 1, 'created': 1, 'reopenedAt': 1},
            sort=[('created', 1), ('_id', 1)]):
        reads.setdefault(s['assignmentId'], []).append(s)

    # activeCount against the assignments still holding a slot (st.ACTIVE_STATES:
    # assigned, downloaded, submitted, under_review, and a legacy rejected).
    mismatches = []
    for caseId, case in cases.items():
        open_ = sum(1 for a in byCase.get(caseId, ()) if a['state'] in st.ACTIVE_STATES)
        have = int(case.get('activeCount') or 0)
        if have != open_:
            mismatches.append({'case': case.get('name'), 'activeCount': have,
                               'openAssignments': open_})
    mismatches.sort(key=lambda m: str(m['case']))
    mismatched = {m['case'] for m in mismatches}

    listed = []
    for caseId, assignments in byCase.items():
        case = cases.get(caseId)
        if case is None:
            continue
        assignments.sort(key=lambda a: (_sortKey(a.get('assignedAt')), str(a['_id'])))
        if len({a['userId'] for a in assignments}) < minLogins:
            continue

        def reopened(a):
            return a.get('reopenedAt') is not None or any(
                s.get('reopenedAt') for s in reads.get(a['_id'], ()))

        rows = []
        for a in assignments:
            subs = reads.get(a['_id'], [])
            freed = freedBy(a)
            submitted = a.get('submittedAt') or (subs[-1].get('created') if subs else None)
            rows.append({
                'login': login(a['userId']),
                'state': STATE_LABELS.get(freed, a['state']),
                'claimed': _eastern(a.get('assignedAt')),
                'submitted': _eastern(submitted),
                'decided': _eastern(a.get('decidedAt') or a.get('releasedAt')),
                'releaseReason': a.get('releaseReason') or None,
                'submission': bool(subs),
                'reopened': reopened(a),
            })

        # The first assignment of each login, in order; those past replicasWanted
        # are the extra annotators. Each came in through a slot freed before it was
        # claimed: the earliest one not already used by an earlier extra.
        wanted = max(1, int(case.get('replicasWanted') or 1))
        arrivals, seen = [], set()
        for a in assignments:
            if a['userId'] not in seen:
                seen.add(a['userId'])
                arrivals.append(a)
        freedSlots = sorted((a for a in assignments if freedBy(a)),
                            key=lambda a: (_sortKey(a.get('releasedAt')), str(a['_id'])))
        used, causes = set(), []
        for extra in arrivals[wanted:]:
            if case.get('benchmark'):
                causes.append('benchmark')
                continue
            at = _sortKey(extra.get('assignedAt'))
            slot = next((f for f in freedSlots if f['_id'] not in used
                         and f['_id'] != extra['_id']
                         and _sortKey(f.get('assignedAt')) < at
                         and _sortKey(f.get('releasedAt')) <= at), None)
            if slot is None:
                causes.append('other/unexplained')
                continue
            used.add(slot['_id'])
            how = freedBy(slot)
            # A read reopened for its annotator (#315) that she then let go: the
            # reopen is what put the slot back in play.
            causes.append('reopen' if how != 'return-to-pool' and reopened(slot) else how)
        if case.get('benchmark'):
            cause = 'benchmark'
        elif not causes:
            cause = WITHIN_WANTED
        elif 'other/unexplained' in causes:
            cause = 'other/unexplained'
        else:
            cause = causes[0]
        submittedLogins = {a['userId'] for a in assignments if reads.get(a['_id'])}
        listed.append({
            'case': case.get('name'), 'replicasWanted': wanted,
            'activeCount': int(case.get('activeCount') or 0),
            'approvedCount': int(case.get('approvedCount') or 0),
            'benchmark': bool(case.get('benchmark')),
            'logins': len(seen), 'submittedLogins': len(submittedLogins),
            'cause': cause, 'causes': causes,
            'activeCountMismatch': case.get('name') in mismatched,
            'assignments': rows,
        })
    listed.sort(key=lambda c: str(c['case']))

    totals = {c: 0 for c in CAUSES + (WITHIN_WANTED,)}
    for c in listed:
        totals[c['cause']] += 1
    return {
        'min': minLogins, 'cases': listed, 'causeTotals': totals,
        'threeOrMoreSubmitted': sum(1 for c in listed if c['submittedLogins'] >= 3),
        'unexplained': [c for c in listed if c['cause'] == 'other/unexplained'],
        'activeCount': {'mismatches': len(mismatches), 'cases': mismatches},
    }


def renderReaders(report):
    """The readers report as lines of text: case names and logins only."""
    lines = [f"Cases with at least {report['min']} distinct annotator logins "
             '(segqueue14-report readers, #334). Read-only; times are US Eastern.', '']
    for c in report['cases']:
        why = c['cause'] if len(set(c['causes'])) <= 1 else \
            f"{c['cause']} ({', '.join(c['causes'])})"
        lines.append(
            f"{c['case']}: {'benchmark' if c['benchmark'] else 'pool'}, "
            f"replicasWanted {c['replicasWanted']}, activeCount {c['activeCount']}, "
            f"approvedCount {c['approvedCount']}, {c['logins']} logins -- cause: {why}")
        for r in c['assignments']:
            lines.append(
                f"  {r['login']}: {r['state']}; claimed {r['claimed'] or '-'}, "
                f"submitted {r['submitted'] or '-'}, decided {r['decided'] or '-'}; "
                f"reason {r['releaseReason'] or '-'}; "
                f"submission {'yes' if r['submission'] else 'no'}"
                f"{', reopened' if r['reopened'] else ''}")
        lines.append('')
    totals = ', '.join(f'{k} {v}' for k, v in report['causeTotals'].items() if v) or 'none'
    lines.append(f"Cases: {len(report['cases'])}; by cause: {totals}")
    lines.append('Cases with 3+ submitted annotator reads (distinct logins): '
                 f"{report['threeOrMoreSubmitted']}")
    if report['unexplained']:
        lines.append('Unexplained (no freed slot before the extra annotator came in; '
                     'a counter drift, a race or the D36 consolidation):')
        for c in report['unexplained']:
            who = ', '.join(f"{r['login']} {r['state']} {r['claimed'] or '-'}"
                            for r in c['assignments'])
            lines.append(f"  {c['case']}: activeCount {c['activeCount']}, "
                         f"replicasWanted {c['replicasWanted']}; {who}")
    else:
        lines.append('Unexplained: none')
    check = report['activeCount']
    if check['mismatches']:
        lines.append(f"activeCount check: {check['mismatches']} case(s) where activeCount "
                     'is not the number of open assignments: ' + ', '.join(
                         f"{m['case']} ({m['activeCount']} vs {m['openAssignments']})"
                         for m in check['cases']))
    else:
        lines.append('activeCount check: every case matches its open assignments')
    return lines


def runReaders(minLogins=DEFAULT_MIN_READERS, asJson=False, out=print, db=None):
    db = _database() if db is None else db
    report = collectReaders(db, minLogins=minLogins)
    if asJson:
        out(json.dumps(report, indent=1, default=str))
    else:
        for line in renderReaders(report):
            out(line)
    return report


def buildParser():
    parser = argparse.ArgumentParser(
        prog='segqueue14-report',
        description='Read-only reports on SegQueue14. Writes nothing.')
    sub = parser.add_subparsers(dest='report', required=True)
    p = sub.add_parser('quality', help='Annotation quality per annotator (#296).')
    p.add_argument('--limit', type=int, default=DEFAULT_LIMIT,
                   help=f'Open the files of only the N newest reads (default {DEFAULT_LIMIT}; '
                        '0 opens none).')
    p.add_argument('--exclude', type=logins, default=(), metavar='LOGIN,...',
                   help='Leave these logins out of every figure (their reads, assignments '
                        'and pairs) but the approvedCount check (#299).')
    p.add_argument('--json', action='store_true', help='Everything, as JSON.')
    r = sub.add_parser('readers', help='Cases with more annotators than they want, and why '
                                       '(#334).')
    r.add_argument('--min', type=int, default=DEFAULT_MIN_READERS, dest='minLogins',
                   help='List cases with at least N distinct annotator logins '
                        f'(default {DEFAULT_MIN_READERS}).')
    r.add_argument('--json', action='store_true', help='Everything, as JSON.')
    return parser


def logins(value):
    """``a,b`` -> ``('a', 'b')``; blanks dropped."""
    return tuple(sorted({x.strip() for x in value.split(',') if x.strip()}))


def main(argv=None):  # pragma: no cover - CLI entry point
    args = buildParser().parse_args(argv)
    if args.report == 'readers':
        if args.minLogins < 1:
            raise SystemExit('--min must be 1 or more')
        runReaders(minLogins=args.minLogins, asJson=args.json)
        return 0
    if args.limit < 0:
        raise SystemExit('--limit must be 0 or more')
    runQuality(limit=args.limit, asJson=args.json, exclude=args.exclude)
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
