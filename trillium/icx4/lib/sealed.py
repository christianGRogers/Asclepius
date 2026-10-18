"""The one sealed-case filter for icx4 (A14, issue #55). Every stage that scores, summarises or inspects an
ImageCAS-X test case takes its case list from `scored_groups()` here, and nothing else:

  * open36  `open_icx_test`              never sealed, never used in development: the decisive group;
  * dev44   `excluded_dev_cases_in_test` never sealed, but inspected by an advocate: reported apart;
  * the 80 `sealed_icx_test` and 20 `sealed_quality0` cases are never scored, summarised or copied into
    results/. They are still predicted (the SegQueue prelabels need all 1000 cases).

A missing, unreadable or malformed sealed list is an error, never "score everything". The ImageCAS-X test split
must be exactly sealed-80 + open-36 + dev-44; anything else means the seal no longer describes the data, and the
run refuses. Standard library only (the login node checks it before the venv exists).

CLI (exit 0 = ok, 3 = refused):
  sealed.py check <sealed_test.json> [<icx_dir> [<layout.json>]]   print the filter and the group counts"""
import json
import os
import sys

GROUPS = ('open36', 'dev44')
KEYS = {'sealed_icx_test': 80, 'open_icx_test': 36, 'sealed_quality0': 20, 'excluded_dev_cases_in_test': 44}


class SealedError(RuntimeError):
    """The sealed list is missing, malformed, or does not partition the ImageCAS-X test split."""


def load(path):
    """Read and validate sealed_test.json; raise SealedError on any doubt."""
    try:
        with open(path) as f:
            S = json.load(f)
    except (OSError, ValueError) as e:
        raise SealedError(f'sealed list {path} is missing or unreadable ({e!r}); refusing to run') from e
    if not isinstance(S, dict):
        raise SealedError(f'sealed list {path} is not a JSON object')
    for k, n in KEYS.items():
        v = S.get(k)
        if not isinstance(v, list) or len(v) != n or len(set(v)) != n or \
                not all(isinstance(c, str) and len(c) == 5 and c[0] == 'c' and c[1:].isdigit() for c in v):
            raise SealedError(f'sealed list {path}: {k!r} must be {n} distinct case ids (c0000 style)')
    sets = {k: set(S[k]) for k in KEYS}
    ks = list(KEYS)
    for i, a in enumerate(ks):
        for b in ks[i + 1:]:
            if sets[a] & sets[b]:
                raise SealedError(f'sealed list {path}: {a} and {b} overlap ({sorted(sets[a] & sets[b])[:3]})')
    return S


def sealed_set(S):
    return set(S['sealed_icx_test']) | set(S['sealed_quality0'])


def icx_test_ids(icx_dir):
    """ImageCAS-X's own test split as case ids (filelist/test.txt holds 1-based ImageCAS ids)."""
    p = os.path.join(icx_dir, 'test.txt')
    try:
        return ['c%04d' % (int(x) - 1) for x in open(p).read().split()]
    except (OSError, ValueError) as e:
        raise SealedError(f'ImageCAS-X test list {p} is missing or unreadable ({e!r})') from e


def scored_groups(S, icx_test, present=None):
    """{'open36': [...], 'dev44': [...]}: the only ImageCAS-X test cases that may be scored, sorted.

    ``icx_test`` is ImageCAS-X's test split; it must be exactly sealed + open + dev (else SealedError).
    ``present`` (optional) restricts each group to the cases found in cases/."""
    test = set(icx_test)
    parts = set(S['sealed_icx_test']) | set(S['open_icx_test']) | set(S['excluded_dev_cases_in_test'])
    if len(test) != len(icx_test) or test != parts:
        raise SealedError(f'the ImageCAS-X test split ({len(test)} cases) is not sealed-80 + open-36 + dev-44 '
                          f'({len(test - parts)} unknown, {len(parts - test)} missing); refusing to score')
    out = {'open36': sorted(S['open_icx_test']), 'dev44': sorted(S['excluded_dev_cases_in_test'])}
    if present is not None:
        out = {g: [c for c in v if c in present] for g, v in out.items()}
    refuse_sealed([c for v in out.values() for c in v], S, 'scored_groups')
    return out


def group_of(groups):
    return {c: g for g, v in groups.items() for c in v}


def refuse_sealed(cases, S, who):
    """Raise SealedError if any case in ``cases`` is sealed. Returns the cases as a list."""
    cases = list(cases)
    bad = sorted(set(cases) & sealed_set(S))
    if bad:
        raise SealedError(f'[{who}] REFUSING: {len(bad)} sealed case(s) requested (A14), e.g. {bad[:3]}')
    return cases


def describe(S, groups=None, n_test=None):
    L = [f'sealed filter (A14): {len(S["sealed_icx_test"])} sealed ImageCAS-X test + '
         f'{len(S["sealed_quality0"])} sealed quality-0 cases are predicted but never scored']
    if groups is not None:
        L.append(f'scored: open-36 {len(groups["open36"])} cases, dev-44 {len(groups["dev44"])} cases'
                 + (f' (of {n_test} ImageCAS-X test)' if n_test is not None else ''))
    return '\n'.join('[icx4] ' + x for x in L)


def main(argv):
    if len(argv) < 2 or argv[0] != 'check':
        print(__doc__)
        return 2
    try:
        S = load(argv[1])
        groups = n = None
        if len(argv) > 2:
            test = icx_test_ids(argv[2])
            present = None
            if len(argv) > 3:
                with open(argv[3]) as f:
                    present = set(json.load(f)['cases'])
            groups, n = scored_groups(S, test, present), len(test)
            if present is not None:
                full = scored_groups(S, test)
                for g in GROUPS:
                    if len(groups[g]) < len(full[g]):
                        print(f'[icx4] WARNING: {len(full[g]) - len(groups[g])} {g} case(s) not in cases/: '
                              f'{sorted(set(full[g]) - set(groups[g]))[:5]}')
        print(describe(S, groups, n))
    except SealedError as e:
        print(f'[icx4] ERROR: {e}', file=sys.stderr)
        return 3
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
