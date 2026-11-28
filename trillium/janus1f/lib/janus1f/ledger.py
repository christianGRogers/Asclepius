"""The looks ledger (F-A22, F-A32): `results/looks.json`, opened BEFORE anything on the locked 100 is scored.

At most two candidate looks in the track: J1F-A (look 1), then J1F-2 (look 2). J1F-A's readings are named when the
look opens: F and T, plus T_L only when F-A32 applies (the lead answered Q-F2-3 "yes" and Janus 1-L was adopted, with
its 100 maps on Fir, before this moment). A second J1F-A entry, or a third look, refuses.
"""
import datetime
import json
import os

MAX_LOOKS = 2
ORDER = ('J1F-A', 'J1F-2')


class LedgerError(RuntimeError):
    pass


def read(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        d = json.load(f)
    if not isinstance(d, list):
        raise LedgerError(f'{path} is not a list of looks; refusing')
    return d


def open_look(path, candidate, readings, fa32_applies=False, q3=None, now=None):
    """Append the look and return its entry; refuse a repeat, a third look, or a look out of order."""
    looks = read(path)
    if candidate not in ORDER:
        raise LedgerError(f'unknown candidate {candidate!r}')
    if any(e.get('candidate') == candidate for e in looks):
        raise LedgerError(f'{candidate} already opened its look on the locked 100 ({path}); a second run refuses')
    if len(looks) >= MAX_LOOKS:
        raise LedgerError(f'{len(looks)} looks already in {path}; a third look refuses (F-A22)')
    if ORDER.index(candidate) != len(looks):
        raise LedgerError(f'{candidate} cannot be look {len(looks) + 1}')
    want = ['F', 'T'] + (['T_L'] if fa32_applies else [])
    if list(readings) != want:
        raise LedgerError(f'readings must be {want} when F-A32 {"applies" if fa32_applies else "does not apply"}')
    entry = {'look': len(looks) + 1, 'candidate': candidate, 'readings': list(readings),
             'fa32_applies': bool(fa32_applies), 'q_f2_3': q3,
             'opened': (now or datetime.datetime.now(datetime.timezone.utc)).strftime('%Y-%m-%dT%H:%M:%SZ')}
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp = path + '.part'
    with open(tmp, 'w') as f:
        json.dump(looks + [entry], f, indent=1)
    os.replace(tmp, path)
    return entry
