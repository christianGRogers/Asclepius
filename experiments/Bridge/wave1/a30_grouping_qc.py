"""A30 QC: does a seal file seal every volume of every sealed patient? CPU, no data.

A patient is the real one, ``segtrain.pool_seal.ingest_patient``: the ingest code's patient id where the name rule
is wrong (the single-patient Mendeley-SDN records, Slicer 4D frames; ``tools/ccta/ingest_open.py``), then D33's
alias. For the given seal file this lists the pool volumes of sealed patients that the file does **not** list,
and counts real patients in the sealed set and in the extension order.

Run on the D27 file (``git show 4469ed4:experiments/Bridge/r9/sealed_pool_proposal.json``) it gives the #87
finding (``a30_grouping_qc_d27.json``: 133 real patients, 60 volumes outside the file; D33 adds the RIDER twin).
Run on the seal in force (D32) it must find none (``a30_grouping_qc.json``). It changes nothing.
Usage: a30_grouping_qc.py [--seal FILE] [--out qc.json]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402

corrected_key = C.corrected_key


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--seal', default=None)
    ap.add_argument('--out')
    a = ap.parse_args(argv)
    path = a.seal or C.seal_path()
    d = json.load(open(path))
    vols = sorted(l.strip() for l in open(C.POOL_LIST) if l.strip() and not l.startswith('#'))
    real = {v: corrected_key(v) for v in vols}
    heur = {v: C.patient_key(v) for v in vols}
    members = defaultdict(list)
    for v in vols:
        members[real[v]].append(v)

    def real_of(entry):   # an entry is a name-rule key (D27 file) or a real patient id (D32 file)
        hit = next((v for v in vols if heur[v] == entry or real[v] == entry), None)
        return real[hit] if hit else None

    listed = set(d['primary']['volumes']) | set(d['report_only']['volumes'])
    sealed_real = {real[v] for v in listed if v in real}
    prim_real = {real[v] for v in d['primary']['volumes'] if v in real}
    leaked = sorted(v for v in vols if real[v] in sealed_real and v not in listed)
    by_patient = defaultdict(list)
    for v in leaked:
        by_patient[real[v]].append(v)
    ext = d['primary']['extension_order']
    ext_real, seen = [], set(prim_real)
    for e in ext:
        r = real_of(e)
        if r and r not in seen:
            ext_real.append(r)
            seen.add(r)
    hk = defaultdict(set)
    for v in vols:
        hk[heur[v]].add(real[v])
    out = {
        'seal': os.path.relpath(path, C.REPO) if path.startswith(C.REPO) else path, 'seal_sha256': C.sha256(path),
        'n_volumes': len(vols), 'patients_name_rule': len(set(heur.values())), 'patients_real': len(members),
        'under_grouped_by_name_rule': {k: sorted({heur[v] for v in vs}) for k, vs in members.items()
                                       if len({heur[v] for v in vs}) > 1},
        'over_grouped_by_name_rule': {k: sorted(s) for k, s in hk.items() if len(s) > 1},
        'sealed_primary_entries': len(d['primary']['patients']), 'sealed_primary_real_patients': len(prim_real),
        'extension_entries': len(ext), 'extension_new_real_patients': len(ext_real),
        'extension_entries_of_sealed_patients': sum(1 for e in ext if real_of(e) in prim_real),
        'leaked_volumes': len(leaked), 'leaked_by_patient': dict(sorted(by_patient.items())),
    }
    if a.out:
        open(a.out, 'w').write(json.dumps(out, indent=1) + '\n')
    print(json.dumps({k: (len(v) if isinstance(v, (dict, list)) else v) for k, v in out.items()}, indent=1))
    return 0


if __name__ == '__main__':
    sys.exit(main())
