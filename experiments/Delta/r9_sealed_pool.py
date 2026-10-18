"""Delta v9 P4 (a proposal for the lead): a sealed acceptance set for D6, drawn from the SegQueue14 pool before any
read exists. D6 compares the model with inter-read tF1 on team reads; under D22/D23 team reads exist only for the 675
pool volumes, so the A14 sealed set (80 ImageCAS-X test + 20 quality-0 cases) can never carry two team reads.

Rule (fixed here, before any read or prediction exists):
  * candidates: the 'QC annotatable' section of configs/segqueue14/pool-2026-10.txt (242 volumes);
  * patient = <Source>__<Case> (D22 naming), with a trailing _tp<k> (time point) removed; one volume per patient,
    the first in serve order;
  * rank patients by sha256('asclepius-sealed-round9-pool:' + patient); the first N are sealed (default N = 60).
Usage: r9_sealed_pool.py <pool list> <out.json> [N]"""
import hashlib, json, re, sys

pool, out = sys.argv[1], sys.argv[2]
N = int(sys.argv[3]) if len(sys.argv) > 3 else 60
sec, first = None, {}
for line in open(pool):
    s = line.strip()
    if s.startswith('# ---'):
        sec = s
        continue
    if not s or s.startswith('#') or 'QC annotatable' not in (sec or ''):
        continue
    p = s.replace('.nii.gz', '').split('__')
    patient = p[0] + '__' + re.sub(r'_tp\d+$', '', p[1]) if len(p) > 1 else p[0]
    first.setdefault(patient, s)
rank = sorted(first, key=lambda k: hashlib.sha256(('asclepius-sealed-round9-pool:' + k).encode()).hexdigest())
sealed = [first[k] for k in rank[:N]]
by_src = {}
for v in sealed:
    by_src[v.split('__')[0]] = by_src.get(v.split('__')[0], 0) + 1
json.dump({'rule': __doc__.split('Rule')[1].split('Usage')[0].strip(), 'status': 'PROPOSAL (Delta v9 P4), not in force',
           'n_candidates_patients': len(first), 'n_sealed': len(sealed), 'by_source': by_src, 'sealed_volumes': sealed},
          open(out, 'w'), indent=1)
print(len(first), 'patients;', len(sealed), 'sealed;', by_src)
