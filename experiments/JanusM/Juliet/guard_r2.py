"""Juliet's Round 2 held-out gate, used until the shared JA12 guard (#138) lands on dev.

Every Round 2 experiment script calls `gate()` first, before it reads or opens anything. The gate:
  1. builds the coronary hold-out set from the committed Round 1 guard (`exclusion.py`, strict mode: pool seal and
     report-only seal, the reserve / extension order, every Round 10 D35 candidate draw, D33 merged aliases),
     plus the A14 sealed 100, the ImageCAS-X test split (open 36, dev 44) and the pool's TotalSegmentator s-numbers;
  2. refuses any case id the script asks to open that matches a hold-out (by patient key, as exclusion.py does);
  3. after the script writes its outputs, `scan_outputs()` searches them for any hold-out id or pool s-number.

Round 2's experiments (E5-E7) are synthetic phantoms and simulations: they ask to open **no** public or project case,
so step 2 is called with an empty list and must pass trivially. Step 3 is the real check on what gets committed.
"""
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(HERE))
import exclusion  # noqa: E402  (Round 1 guard, committed)


def heldout():
    f = set(exclusion.forbidden_patients('strict'))
    S = json.loads((REPO / 'trillium/icx4/sealed_test.json').read_text())
    icx = set()
    for k in ('sealed_icx_test', 'open_icx_test', 'sealed_quality0', 'excluded_dev_cases_in_test',
              'excluded_dev_cases_in_quality0'):
        v = S.get(k, [])
        icx |= set(v if isinstance(v, list) else v.get('cases', v.get('patients', [])) if isinstance(v, dict) else [])
    sp = json.loads((REPO / 'trillium-results/icx14/results/splits.json').read_text())
    icx |= set(sp['val']) | set(sp['test'])          # val 80 and the ImageCAS-X test split
    snums = set(re.findall(r'TotalSegmentator-cardiac__(s\d{4})',
                           (REPO / 'configs/segqueue14/pool-2026-10.txt').read_text()))
    return f, icx, snums


def gate(case_ids=()):
    f, icx, snums = heldout()
    if len(snums) != 16 or len(f) < 300:
        sys.exit(f'GUARD: hold-out lists look wrong ({len(f)} patient keys, {len(snums)} s-numbers); refusing to run')
    hits = [c for c in case_ids if exclusion.is_forbidden(c, f) or c in icx or any(s in c for s in snums)]
    if hits:
        sys.exit(f'GUARD: refused {len(hits)} held-out cases: {hits[:5]}')
    print(f'guard: {len(f)} pool patient keys, {len(icx)} ImageCAS-X held-out ids, {len(snums)} pool s-numbers; '
          f'{len(case_ids)} cases requested, 0 refused')
    return f, icx, snums


def scan_outputs(paths):
    f, icx, snums = heldout()
    keys = [k for k in f if len(k) > 6] + sorted(icx) + sorted(snums)
    bad = []
    for p in paths:
        t = Path(p).read_text()
        bad += [(str(p), k) for k in keys if k in t]
    print(f'scan: {len(paths)} output files, {len(keys)} hold-out keys searched, {len(bad)} matches')
    if bad:
        sys.exit(f'GUARD: hold-out ids found in outputs: {bad[:5]}')


if __name__ == '__main__':
    gate()
    scan_outputs(sorted(HERE.glob('*.json')))
