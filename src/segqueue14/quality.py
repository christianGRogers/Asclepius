"""The figures of the SegQueue14 annotation quality report (#296), without a database.

``girder_segqueue14.report`` reads the reads, the stored scores and the files; this
module turns them into numbers and plain-text tables. Stdlib-only at import, like
the rest of the package (numpy is imported where an array is needed), so the
figures are tested without Girder or MongoDB.
"""

from __future__ import annotations

import statistics

from . import labels

#: A class keeping more than this fraction of the seed is barely trimmed; two or
#: more such classes in one read mean it was probably submitted untrimmed.
UNTRIMMED_KEEP = 0.90
#: A class whose Dice with the seed is at least this is a near-identical copy of it.
COPY_DICE = 0.90
#: The pair flag when the setting does not say (``settings.DEFAULT_REFERENCE``).
DEFAULT_PAIR_FLAG = 0.60
#: The step summary keeps the last 200 lines of the step's output.
MAX_LINES = 180
#: Rows in each of the "worth a reviewer's eye" lists.
EYE_ROWS = 5

NAMES = list(labels.NAMES)

#: ``(text in the flag, reason)``, first match wins: the flags the worker writes
#: (``segqueue14.scoring``, ``girder_segqueue14.scoring``).
FLAG_REASONS = (
    ('could not be compared with the other read', 'pair not comparable'),
    ('against the other read', 'low pair Dice'),
    ('required class empty', 'empty required class'),
    ('could not be scored against ImageCAS-X', 'reference not scorable'),
    ('against ImageCAS-X', 'low reference Dice'),
)
OTHER_REASON = 'other'
REASONS = [reason for _, reason in FLAG_REASONS] + [OTHER_REASON]
#: Column headings for the reasons.
SHORT_REASONS = {'pair not comparable': 'pair n/a', 'low pair Dice': 'low pair',
                 'empty required class': 'empty req', 'reference not scorable': 'ref n/a',
                 'low reference Dice': 'low ref', OTHER_REASON: 'other'}


def flagReason(flag):
    """The group a worker flag belongs to."""
    for text, reason in FLAG_REASONS:
        if text in (flag or ''):
            return reason
    return OTHER_REASON


def usable(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value


def seedComparison(masks, seed=None, names=None):
    """Figures for one read: ``masks`` is ``(class, z, y, x)``, ``seed`` a 3D mask
    on the same grid (or None when the case has no seed).

    Returns ``{counts, overlapFraction, seedVoxels, kept, seedDice, copies,
    keptAbove, untrimmed}``. ``kept[c]`` is the fraction of the seed's voxels class
    ``c`` keeps; ``seedDice[c]`` its Dice with the seed; ``copies`` the classes
    whose Dice with the seed is at least ``COPY_DICE``; ``keptAbove`` the classes
    keeping more than ``UNTRIMMED_KEEP`` of it; ``untrimmed`` is two or more of those.
    """
    import numpy as np

    names = list(NAMES if names is None else names)
    masks = np.asarray(masks) != 0
    counts = {name: int(np.count_nonzero(masks[i])) for i, name in enumerate(names)}
    layers = masks.sum(axis=0, dtype=np.uint8)
    labelled = int(np.count_nonzero(layers))
    shared = int(np.count_nonzero(layers >= 2))
    out = {'counts': counts,
           'overlapFraction': round(shared / labelled, 4) if labelled else 0.0,
           'seedVoxels': None, 'kept': None, 'seedDice': None, 'copies': [],
           'keptAbove': [], 'untrimmed': False}
    if seed is None:
        return out
    seed = np.asarray(seed) != 0
    if seed.shape != masks.shape[1:]:
        raise ValueError(f'seed shape {seed.shape} != read shape {masks.shape[1:]}')
    seedN = int(np.count_nonzero(seed))
    out['seedVoxels'] = seedN
    if not seedN:
        return out
    kept, dice = {}, {}
    for i, name in enumerate(names):
        inSeed = int(np.count_nonzero(masks[i] & seed))
        kept[name] = round(inSeed / seedN, 4)
        dice[name] = round(2.0 * inSeed / (counts[name] + seedN), 4)
    out['kept'], out['seedDice'] = kept, dice
    out['copies'] = [n for n in names if dice[n] >= COPY_DICE]
    out['keptAbove'] = [n for n in names if kept[n] > UNTRIMMED_KEEP]
    out['untrimmed'] = len(out['keptAbove']) >= 2
    return out


def summary(values):
    values = [v for v in values if usable(v)]
    if not values:
        return {'n': 0, 'mean': None, 'median': None, 'min': None, 'max': None}
    return {'n': len(values), 'mean': round(statistics.fmean(values), 4),
            'median': round(statistics.median(values), 4),
            'min': round(min(values), 4), 'max': round(max(values), 4)}


def meanOf(values):
    values = [v for v in values if usable(v)]
    return round(statistics.fmean(values), 4) if values else None


# ---------------------------------------------------------------- printing


def _cell(value, digits=2):
    if value is None:
        return '-'
    if isinstance(value, float):
        return f'{value:.{digits}f}'
    return str(value)


def table(head, rows):
    """Plain-text columns: the first left-aligned, the rest right-aligned."""
    cells = [list(map(str, head))] + [[_cell(v) for v in row] for row in rows]
    widths = [max(len(r[i]) for r in cells) for i in range(len(head))]
    out = []
    for r in cells:
        out.append('  '.join(r[0].ljust(widths[0]) if i == 0 else r[i].rjust(widths[i])
                             for i in range(len(r))).rstrip())
    out.insert(1, '  '.join('-' * w for w in widths))
    return out


def render(report, benchmarkLines=()):
    """The report as plain-text lines, at most ``MAX_LINES``."""
    t, people = report['totals'], report['annotators']
    lines = ['SegQueue14 annotation quality (read-only). Pool reads only; the benchmark '
             'is at the end.',
             f"{t['reads']} annotator reads; files opened for the {t['analysed']} newest "
             f"(--limit {t['limit']})."]
    if not people:
        lines.append('No pool reads yet.')
    else:
        lines += ['', 'Reads']
        lines += table(['login', 'reads', 'approved', 'sent back', 'in review',
                        'revised', 'median min'],
                       [[n, p['reads'], p['approved'], p['sentBack'], p['underReview'],
                         p['revisedByReviewer'],
                         None if p['medianSeconds'] is None else p['medianSeconds'] / 60]
                        for n, p in people.items()])
        lines += ['', f"Pair agreement (two-read cases, stored scores; flag < {t['pairFlag']:.2f})"]
        lines += table(['login', 'pairs', 'mean', 'median', 'min', 'max'] + NAMES + ['< flag'],
                       [[n, p['pairs']['n'], p['pairs']['mean'], p['pairs']['median'],
                         p['pairs']['min'], p['pairs']['max']]
                        + [p['pairs']['perClass'][c] for c in NAMES] + [p['pairs']['below']]
                        for n, p in people.items()])
        lines += ['', 'Flags (reads flagged, by reason)']
        lines += table(['login', 'flagged'] + [SHORT_REASONS[r] for r in REASONS],
                       [[n, p['flagged']] + [p['flags'][r] for r in REASONS]
                        for n, p in people.items()])
        lines += ['', f'Seeds (opened reads on seeded cases): mean fraction of the seed each '
                      f'class keeps; untrimmed = 2+ classes keep > {UNTRIMMED_KEEP:.0%}']
        lines += table(['login', 'seeded'] + [f'kept {c}' for c in NAMES]
                       + ['2+ copies', 'untrimmed'],
                       [[n, p['seeded']] + [p['keptMean'][c] for c in NAMES]
                        + [p['copies2'], p['untrimmed']] for n, p in people.items()])
        lines += ['', 'Overlap (opened reads: fraction of labelled voxels in 2+ classes) '
                      'and empty classes (all reads)']
        lines += table(['login', 'opened', 'overlap>0', 'median', 'max']
                       + [f'empty {c}' for c in NAMES],
                       [[n, p['analysed'], p['overlapReads'], p['overlapMedian'],
                         p['overlapMax']] + [p['empty'][c] for c in NAMES]
                        for n, p in people.items()])
    lines += ['', f"Project: {t['cases']} pool cases -- {t['reads0']} with no read, "
                  f"{t['reads1']} with one, {t['reads2']} with two or more; "
                  f"{t['pairsScored']} pairs scored."]
    eye = report['eye']
    lines += ['', f"Worth a reviewer's eye (case, login): pairs below {t['pairFlag']:.2f}, "
                  "most overlap, likely untrimmed"]
    for row in eye['lowestPairDice']:
        lines.append(f"  low pair Dice {row['meanDice']:.2f}: {row['case']} "
                     f"({', '.join(row['logins'])})")
    for row in eye['mostOverlap']:
        lines.append(f"  overlap {row['overlapFraction']:.0%}: {row['case']} ({row['login']})")
    for row in eye['likelyUntrimmed']:
        lines.append(f"  likely untrimmed ({', '.join(row['classes'])} keep the seed): "
                     f"{row['case']} ({row['login']})")
    if not any(eye.values()):
        lines.append('  nothing stands out')
    if benchmarkLines:
        lines += ['', 'Benchmark (segqueue14-benchmark status)'] + list(benchmarkLines)
    if len(lines) > MAX_LINES:
        cut = len(lines) - MAX_LINES + 1
        lines = lines[:MAX_LINES - 1] + [f'... {cut} more lines: run with --json for all.']
    return lines
