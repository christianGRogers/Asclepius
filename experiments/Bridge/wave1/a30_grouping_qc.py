"""A30 QC: the seal's patient grouping (Round 9 heuristic) against the ingest code's patient ids. CPU, no data.

The ingest code records who a volume belongs to. ``tools/ccta/ingest_open.py``:
  * ``run_sdn_cases`` (the records in ``SDN_CASES``: Mendeley-SDN 37nnfyh3x9, 4643nn2z44, 7x9kb53262, spb25zt2c4):
    "(one patient) ... All cases share patient_id", ``patient_id=f'SDN-{did}'``; the case name is
    ``s<series>[_p<phase %>|_f<frame>]``, so ``sNNN`` is a DICOM series, not a subject;
  * the Slicer sample data: multi-phase sequences are stored "one case per phase (<name>_fNN ...)", with
    ``patient_id=name``.
The heuristic (``seal_pool.py``) knows neither: it keys these by series and does not strip ``_fNN``. This script
rebuilds the patient of every pool volume from those two facts, keeps every other source as the heuristic has it,
and lists the volumes of sealed (or extension) patients that the seal does **not** cover.

It changes nothing. A fix to the seal list is a separate, explicit PR for the PM and the lead (D27).
Usage: a30_grouping_qc.py [--out qc.json]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

corrected_key = C.corrected_key


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    seal = C.Seal()
    d = json.load(open(seal.path))
    vols = sorted(seal.pool)
    heur = {v: C.patient_key(v) for v in vols}
    corr = {v: corrected_key(v) for v in vols}
    members = defaultdict(list)
    for v in vols:
        members[corr[v]].append(v)
    sealed_vols = set(d['primary']['volumes']) | set(d['report_only']['volumes'])
    sealed_corr = {corr[v] for v in sealed_vols}
    ext = d['primary']['extension_order']
    ext_vols = {v for v in vols if heur[v] in set(ext)}
    leaked = sorted(v for v in vols if corr[v] in sealed_corr and v not in sealed_vols)
    # sealed real patients, primary only, and what the extension order really adds
    prim_sealed_corr = {corr[v] for v in d['primary']['volumes']}
    ext_corr, seen = [], set(prim_sealed_corr)
    for p in ext:
        vs = [v for v in vols if heur[v] == p]
        k = corr[vs[0]]
        if k not in seen:
            ext_corr.append(k)
            seen.add(k)
    merged = {k: sorted({heur[v] for v in vs}) for k, vs in members.items() if len({heur[v] for v in vs}) > 1}
    over = {}   # a heuristic key holding two corrected patients (over-grouping)
    hk = defaultdict(set)
    for v in vols:
        hk[heur[v]].add(corr[v])
    over = {k: sorted(s) for k, s in hk.items() if len(s) > 1}
    by_patient = defaultdict(list)
    for v in leaked:
        by_patient[corr[v]].append(v)
    out = {
        'seal': os.path.relpath(seal.path, C.REPO), 'seal_sha256': C.sha256(seal.path),
        'n_volumes': len(vols), 'patients_heuristic': len(set(heur.values())), 'patients_corrected': len(members),
        'under_grouped': merged, 'over_grouped': over,
        'sealed_primary_keys': len(d['primary']['patients']), 'sealed_primary_real_patients': len(prim_sealed_corr),
        'extension_entries': len(ext), 'extension_new_real_patients': len(ext_corr),
        'extension_entries_already_sealed_patient': sum(
            1 for p in ext if corr[next(v for v in vols if heur[v] == p)] in prim_sealed_corr),
        'leaked_volumes': len(leaked), 'leaked_by_patient': {k: v for k, v in sorted(by_patient.items())},
        'leaked_in_extension_order': sorted(set(leaked) & ext_vols),
    }
    s = json.dumps(out, indent=1)
    if a.out:
        open(a.out, 'w').write(s + '\n')
    print(json.dumps({k: (v if not isinstance(v, (dict, list)) or k in ('over_grouped',) else
                          (len(v) if isinstance(v, list) else {kk: len(vv) for kk, vv in v.items()}))
                      for k, v in out.items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
