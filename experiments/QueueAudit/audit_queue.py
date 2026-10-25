"""Queue-size audit of SegQueue14 on janus (#126), from the 2026-10-25 snapshot and repository files only.

CPU only, standard library only. Opens no image and no read: it compares names.

    python3 -I experiments/QueueAudit/audit_queue.py            # prints the report, writes audit_2026-10-25.json

Inputs (all in the repository):
- snapshot-2026-10-25/: the queue table (GET /segqueue14/review/cases, every page) and the item names in
  SegQueue/cases and SegQueue/seeds-totalseg, pulled read-only by the PM;
- configs/segqueue14/pool-2026-10.txt (D23) and sealed-pool-2026-10.json (D27/D32/D33);
- the ingest QC table, vault/Research/Datasets and benchmarks/CCTA sourcing 2026-10/QC volume reports.csv;
- the Round 10 D35 draws (A33: Delta adopted subject to Q1; Atlas the fallback; Bridge the third candidate;
  Crucible and Foxtrot reported for completeness);
- segtrain.pool_seal.ingest_patient, the project's patient rule (D32/D33).
"""

from __future__ import annotations

import collections
import csv
import hashlib
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
SNAP = os.path.join(HERE, 'snapshot-2026-10-25')
sys.path.insert(0, os.path.join(REPO, 'src'))
from segtrain.pool_seal import ingest_patient  # noqa: E402  (stdlib-only module)

POOL_LIST = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
QC = os.path.join(REPO, 'vault', 'Research', 'Datasets and benchmarks', 'CCTA sourcing 2026-10',
                  'QC volume reports.csv')
DRAWS = {   # name -> (file, how its patient list is reached)
    'Delta (A33, adopted subject to Q1)': ('experiments/Delta/r10/d35_decision_set_proposal.json', ('patients',)),
    'Atlas (A33 fallback if Q1 declined)': ('experiments/Atlas/r10/decision_set_proposal.json',
                                            ('decision_set', 'patients')),
    'Bridge (Q1 option b)': ('experiments/Bridge/r10/decision_set_proposal.json', ('patients',)),
    'Crucible (not adopted)': ('experiments/Crucible/r10/d35_proposal.json', ('patients',)),
    'Foxtrot (refused)': ('experiments/Foxtrot/r10/d35_proposal.json', ('proposed_d35', 'patients')),
}
Q1_CANDIDATES = ('Delta (A33, adopted subject to Q1)', 'Atlas (A33 fallback if Q1 declined)',
                 'Bridge (Q1 option b)')
SUSPECT_SOURCES = ('ImageALCAPA', 'HOCMvalvesSeg', 'CCA200-HF')   # D23's third block, D29
PENDING_SOURCES = ('PLOS-Peng2016-CCTA-JPEG',)                     # burned-in text, pending
SEED_SUFFIX = '__totalseg-coronary.nii.gz'                         # D22/D23 seed name


def sha(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def stem(name):
    return name[:-len('.nii.gz')] if name.endswith('.nii.gz') else name


def source(name):
    return name.split('__', 1)[0]


def read_pool_list():
    sections, order, cur = {}, [], None
    for line in open(POOL_LIST, encoding='utf-8'):
        line = line.strip()
        if line.startswith('# ---'):
            cur = line[5:].split(':')[0].strip()
            sections[cur] = []
        elif line and not line.startswith('#'):
            order.append(line)
            sections[cur].append(line)
    return order, sections


def dig(d, path):
    for k in path:
        d = d[k]
    return d


def main():
    out = {'inputs': {}}
    for p in (POOL_LIST, SEAL, QC) + tuple(os.path.join(REPO, f) for f, _ in DRAWS.values()):
        out['inputs'][os.path.relpath(p, REPO)] = sha(p)
    for f in sorted(os.listdir(SNAP)):
        out['inputs'][os.path.relpath(os.path.join(SNAP, f), REPO)] = sha(os.path.join(SNAP, f))

    queue = list(csv.DictReader(open(os.path.join(SNAP, 'segqueue14_queue_2026-10-25.csv'), encoding='utf-8')))
    cases_items = [l.strip() for l in open(os.path.join(SNAP, 'segqueue_cases_items_2026-10-25.txt')) if l.strip()]
    seed_items = [l.strip() for l in open(os.path.join(SNAP, 'segqueue_seeds_items_2026-10-25.txt')) if l.strip()]
    order, sections = read_pool_list()
    qc = {r['name']: r for r in csv.DictReader(open(QC, encoding='utf-8'))}
    seal = json.load(open(SEAL))
    problems = []

    # ---- 1. the queue against the pool list ------------------------------------------------------
    qvol = [r['volumeName'] for r in queue]
    c1 = {
        'queue_rows': len(queue), 'queue_distinct_volumes': len(set(qvol)),
        'queue_distinct_case_names': len({r['caseName'] for r in queue}),
        'pool_list_entries': len(order), 'pool_list_distinct': len(set(order)),
        'in_queue_not_in_list': sorted(set(qvol) - set(order)),
        'in_list_not_in_queue': sorted(set(order) - set(qvol)),
        'case_name_is_volume_stem': sum(r['caseName'] + '.nii.gz' == r['volumeName'] for r in queue),
        'dataset_is_name_prefix': sum(r['dataset'] == source(r['caseName']) for r in queue),
        'sections': {k: len(v) for k, v in sections.items()},
        'fields': {k: dict(collections.Counter(r[k] for r in queue))
                   for k in ('tier', 'replicasWanted', 'approvedCount', 'activeCount', 'retired',
                             'blindDuplicate', 'hasReference', 'prelabelVersion')},
        'serve_order_in_snapshot': False,
    }
    # Sections against the QC verdicts they claim.
    sec_names = list(sections)
    want = {sec_names[0]: lambda n: qc[n]['annotatable'] == 'yes' and source(n) not in SUSPECT_SOURCES,
            sec_names[1]: lambda n: qc[n]['annotatable'] == 'limited' and source(n) not in SUSPECT_SOURCES,
            sec_names[2]: lambda n: source(n) in SUSPECT_SOURCES and qc[n]['annotatable'] != 'no'}
    c1['section_violations'] = {k: [n for n in v if n not in qc or not want[k](n)] for k, v in sections.items()}
    c1['section_qc_mix'] = {k: dict(collections.Counter(qc[n]['annotatable'] for n in v if n in qc))
                            for k, v in sections.items()}
    # Order within each section: by source then name? report whether sorted.
    c1['sections_sorted_by_name'] = {k: v == sorted(v) for k, v in sections.items()}
    if c1['in_queue_not_in_list'] or c1['in_list_not_in_queue'] or len(set(qvol)) != len(qvol):
        problems.append('queue and pool list differ')
    out['1_queue_vs_pool_list'] = c1

    # ---- 2. CT and seed for every queued case --------------------------------------------------
    cset, sset = set(cases_items), set(seed_items)
    c2 = {
        'cases_items': len(cases_items), 'cases_items_distinct': len(cset),
        'seeds_items': len(seed_items), 'seeds_items_distinct': len(sset),
        'queued_without_ct': sorted(v for v in qvol if v not in cset),
        'queued_without_seed': sorted(v for v in qvol if stem(v) + SEED_SUFFIX not in sset),
        'seeds_not_for_a_queued_case': sorted(s for s in sset
                                              if s[:-len(SEED_SUFFIX)] + '.nii.gz' not in set(qvol)),
        'seeds_with_other_name_form': sorted(s for s in sset if not s.endswith(SEED_SUFFIX)),
    }
    out['2_ct_and_seed'] = c2

    # ---- 3. the 904 pool CTs and the 229 left out ------------------------------------------------
    imagecas = [n for n in cases_items if source(n) == 'ImageCAS']
    pool_cts = [n for n in cases_items if source(n) != 'ImageCAS']
    left = sorted(set(pool_cts) - set(qvol))
    reason = {}
    for n in left:
        if n not in qc:
            reason[n] = 'no QC line'
        elif source(n) in PENDING_SOURCES:
            reason[n] = f"PLOS-Peng2016 burned-in text, pending (QC {qc[n]['annotatable']})"
        elif qc[n]['annotatable'] == 'no':
            reason[n] = 'QC not annotatable'
        else:
            reason[n] = f"UNEXPLAINED (QC {qc[n]['annotatable']})"
    by = collections.defaultdict(collections.Counter)
    for n, r in reason.items():
        by[source(n)][r] += 1
    no_reasons = collections.Counter()
    for n, r in reason.items():
        if r == 'QC not annotatable':
            q = qc[n]
            no_reasons[f"coronaries={q['coronaries_visible']}; heart_in_fov={q['heart_in_fov']}; "
                       f"contrast={q['contrast']}"] += 1
    c3 = {
        'imagecas_items': len(imagecas),
        'imagecas_ct': len([n for n in imagecas if not n.endswith('__mask.nii.gz')]),
        'imagecas_masks': len([n for n in imagecas if n.endswith('__mask.nii.gz')]),
        'pool_cts': len(pool_cts), 'qc_lines': len(qc),
        'pool_cts_without_qc_line': sorted(set(pool_cts) - set(qc)),
        'qc_lines_without_pool_ct': sorted(set(qc) - set(pool_cts)),
        'queued': len(set(pool_cts) & set(qvol)), 'left_out': len(left),
        'left_out_by_reason': dict(collections.Counter(reason.values())),
        'left_out_by_source': {s: dict(c) for s, c in sorted(by.items())},
        'not_annotatable_by_what_qc_saw': dict(no_reasons.most_common()),
        'unexplained': sorted(n for n, r in reason.items() if r.startswith('UNEXPLAINED')),
        'queued_but_qc_no': sorted(n for n in qvol if n in qc and qc[n]['annotatable'] == 'no'),
        'left_out_list': reason,
    }
    if c3['unexplained'] or c3['queued_but_qc_no']:
        problems.append('left-out set does not match QC')
    out['3_left_out'] = c3

    # ---- 4. real patients -------------------------------------------------------------------------
    pat = {v: ingest_patient(stem(v)) for v in qvol}
    patients = collections.defaultdict(list)
    for v, p in pat.items():
        patients[p].append(v)
    primary_sealed = set(seal['primary']['patients'])
    report_sealed = set(seal['report_only']['patients'])
    sealed_vols = set(seal['primary']['volumes']) | set(seal['report_only']['volumes'])
    ext = list(seal['primary']['extension_order'])

    def stratum(p):
        s = source(p)
        if s == 'ImageCHD':
            return 'report_only (ImageCHD, D29)'
        if s in SUSPECT_SOURCES:
            return 'excluded (spacing suspect, D29)'
        return 'primary'

    draws = {}
    for name, (f, path) in DRAWS.items():
        lst = dig(json.load(open(os.path.join(REPO, f))), path)
        draws[name] = set(lst)
    a33_d35 = draws[Q1_CANDIDATES[0]]
    reserve_100 = set(ext[:100])                                   # Bridge wave-1 EXTENSION_RESERVED = 100
    reserve_a34 = [p for p in ext if p not in a33_d35]             # A34: the order skipping D35 patients
    frozen_until_q1 = set().union(*(draws[k] for k in Q1_CANDIDATES)) | set(ext)

    def cls(p, d35, reserve):
        if p in primary_sealed:
            return 'sealed (primary, A10)'
        if p in report_sealed:
            return 'sealed (ImageCHD report-only)'
        if p in d35:
            return 'D35 decision set'
        if p in reserve:
            return 'reserve'
        return 'open'

    def table(d35, reserve):
        pc, vc = collections.Counter(), collections.Counter()
        for p, vs in patients.items():
            k = (cls(p, d35, reserve), stratum(p)) if cls(p, d35, reserve) == 'open' else (cls(p, d35, reserve),)
            k = ' / '.join(k)
            pc[k] += 1
            vc[k] += len(vs)
        return {k: {'patients': pc[k], 'volumes': vc[k], 'reads': 2 * vc[k]} for k in sorted(pc)}

    by_source = collections.defaultdict(lambda: [0, 0])
    for p, vs in patients.items():
        by_source[source(p)][0] += 1
        by_source[source(p)][1] += len(vs)

    c4 = {
        'patients': len(patients), 'seal_file_says': seal['n_patients'],
        'by_stratum': dict(collections.Counter(stratum(p) for p in patients)),
        'by_source_[patients,volumes]': dict(sorted(by_source.items())),
        'multi_volume_patients': sum(len(v) > 1 for v in patients.values()),
        'sealed_primary_patients_in_queue': len(primary_sealed & set(patients)),
        'sealed_report_only_patients_in_queue': len(report_sealed & set(patients)),
        'sealed_volumes_listed': len(sealed_vols),
        'sealed_volumes_missing_from_queue': sorted(sealed_vols - set(qvol)),
        'sealed_patients_missing_from_queue': sorted((primary_sealed | report_sealed) - set(patients)),
        'scoring_volumes_missing_from_queue': sorted(
            v for d in (seal['primary']['scoring_volume'], seal['report_only']['scoring_volume'])
            for v in d.values() if (v if v.endswith('.nii.gz') else v + '.nii.gz') not in set(qvol)),
        'queued_volumes_of_sealed_patients_not_in_seal_file': sorted(
            v for v in qvol if pat[v] in primary_sealed | report_sealed and v not in sealed_vols),
        'extension_order': {'entries': len(ext), 'in_queue': sum(p in patients for p in ext),
                            'sealed': sum(p in primary_sealed for p in ext),
                            'primary': sum(stratum(p) == 'primary' for p in ext if p in patients)},
        'draws': {},
        'accounting_A33_Delta_with_A34_reserve': table(a33_d35, set(reserve_a34)),
        'accounting_Atlas_fallback_with_reserve_100': table(draws[Q1_CANDIDATES[1]], reserve_100),
        'frozen_now_until_Q1 (union of three draws + whole extension order)': {
            'patients': len(frozen_until_q1 & set(patients)),
            'volumes': sum(len(patients[p]) for p in frozen_until_q1 & set(patients)),
        },
        'reserve_A34_patients': len(reserve_a34),
        'reserve_100_patients': len(reserve_100),
    }
    for name, d in draws.items():
        c4['draws'][name] = {
            'patients': len(d), 'in_queue': len(d & set(patients)),
            'missing_from_queue': sorted(d - set(patients)),
            'volumes_in_queue': sum(len(patients[p]) for p in d & set(patients)),
            'sealed': sorted(d & (primary_sealed | report_sealed)),
            'not_primary': sorted(p for p in d if stratum(p) != 'primary'),
            'in_extension_order_1_100': sum(p in reserve_100 for p in d),
            'in_extension_order_101': sum(p in ext[100:] for p in d),
        }
    if c4['sealed_volumes_missing_from_queue'] or c4['sealed_patients_missing_from_queue']:
        problems.append('sealed volumes missing from the queue')
    out['4_patients'] = c4

    # ---- 5. reads ---------------------------------------------------------------------------------
    reads = sum(int(r['replicasWanted']) for r in queue)
    out['5_reads'] = {
        'total': reads,
        'A33_Delta': {k: v['reads'] for k, v in c4['accounting_A33_Delta_with_A34_reserve'].items()},
        'Atlas_fallback': {k: v['reads'] for k, v in c4['accounting_Atlas_fallback_with_reserve_100'].items()},
    }

    # ---- 6. anything else -------------------------------------------------------------------------
    note = lambda n: qc.get(n, {}).get('note', '')  # noqa: E731
    flagged = {
        'corrupt': ['VMR-Coronary__0157_H_CORO_SVGD_1.nii.gz', 'VMR-Coronary__0157_H_CORO_SVGD_2.nii.gz'],
        'rotated_180': ['VMR-Coronary__0148_H_CORO_SVGD.nii.gz', 'VMR-Coronary__0157_H_CORO_SVGD_0.nii.gz'],
    }
    c6 = {'qc_report_flags': {}}
    for k, names in flagged.items():
        c6['qc_report_flags'][k] = {n: {'queued': n in set(qvol), 'qc': qc.get(n, {}).get('annotatable'),
                                        'orientation': qc.get(n, {}).get('orientation')} for n in names}
    c6['queued_orientation_not_ok'] = {n: (qc[n]['orientation'], note(n)) for n in qvol
                                       if n in qc and qc[n]['orientation'] != 'ok'}
    c6['queued_contrast_none_or_weak'] = {n: (qc[n]['contrast'], note(n)) for n in qvol
                                          if n in qc and qc[n]['contrast'] in ('none', 'no', 'weak')}
    c6['queued_coronaries_not_visible'] = sorted(n for n in qvol if n in qc and qc[n]['coronaries_visible'] == 'no')
    c6['queued_qc_note_mentions_duplicate_or_spacing'] = {
        n: note(n) for n in qvol if re.search(r'duplicat|identical|same as|stretch|spacing', note(n), re.I)}
    c6['queued_qc_note_mentions_corrupt_or_constant'] = {
        n: note(n) for n in qvol if re.search(r'corrupt|constant|blank|empty', note(n), re.I)}
    # Names that collide when case and punctuation are folded.
    fold = collections.defaultdict(list)
    for v in qvol:
        fold[re.sub(r'[^a-z0-9]', '', v.lower())].append(v)
    c6['names_colliding_when_folded'] = [v for v in fold.values() if len(v) > 1]
    # Sources the QC kept (yes/limited) that the queue lacks.
    kept_sources = {source(n) for n, r in qc.items() if r['annotatable'] != 'no'}
    c6['qc_kept_sources_absent_from_queue'] = sorted(kept_sources - {source(v) for v in qvol})
    c6['seal_file_pool_list_counts'] = {'n_volumes': seal['n_volumes'], 'n_patients': seal['n_patients']}
    out['6_other'] = c6
    out['problems'] = problems

    with open(os.path.join(HERE, 'audit_2026-10-25.json'), 'w') as fh:
        json.dump(out, fh, indent=1, sort_keys=False)
    json.dump({k: v for k, v in out.items() if k != 'inputs'}, sys.stdout, indent=1, default=str)
    print()
    return 0


if __name__ == '__main__':
    sys.exit(main())
