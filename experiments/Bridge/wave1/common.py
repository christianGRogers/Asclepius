"""Shared pieces of the wave-1 tools (Round 9 A31): the pool seal, patient keys, refusal, bootstrap.

The seal (D27, A30) is the canonical ``configs/segqueue14/sealed-pool-2026-10.json`` once #84 lands, else
``experiments/Bridge/r9/sealed_pool_proposal.json`` (#84 copies it byte for byte; if both exist they must match).

**What is refused.** Every volume of a patient in the seal (150 primary + 20 ImageCHD report-only) **and** every
volume of the first 100 patients of the pre-registered extension order. Those 100 are the patients the seal grows
into at 200 and 250 (A30/A31), so their reads must stay uninspected too, or an extension would add patients whose
reads were already looked at. Names that are not in the pool list are refused as well: a name we cannot place is a
name we cannot prove unsealed.
"""
from __future__ import annotations

import hashlib
import json
import os
import re

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
CANONICAL_SEAL = os.path.join(REPO, 'configs', 'segqueue14', 'sealed-pool-2026-10.json')
PROPOSAL_SEAL = os.path.join(REPO, 'experiments', 'Bridge', 'r9', 'sealed_pool_proposal.json')
POOL_LIST = os.path.join(REPO, 'configs', 'segqueue14', 'pool-2026-10.txt')
TF1_PIN = '24441cf8df0f000bd956c7dd9d8ae1daac866cfb14df1d174441d00e54f05254'   # A1c (Round 8, kept by A32)
EXTENSION_RESERVED = 100          # the seal can grow to 250 = 150 + the first 100 of the extension order
CLASSES = {1: 'LM', 2: 'LAD', 3: 'LCx', 4: 'RCA'}

# The same heuristic as experiments/Bridge/r9/seal_pool.py (pinned by a test against the seal file).
_SUFFIX = re.compile(r'(_tp\d+|_p\d+|_(diast|syst)|_s\d+)$', re.I)
_REPLICA = re.compile(r'__r\d+$')


def volume_name(entry: str) -> str:
    """An export folder or file name -> the pool volume name '<Source>__<Case>[__<Part>].nii.gz'.
    Strips a SegQueue replica suffix (``__r2``), a seed suffix and the extension."""
    base = os.path.basename(entry.rstrip('/'))
    for ext in ('.nii.gz', '.nii', '.nrrd'):
        if base.endswith(ext):
            base = base[:-len(ext)]
    base = base.replace('__totalseg-coronary', '')
    base = _REPLICA.sub('', base)
    return base + '.nii.gz'


def patient_key(volume: str) -> str:
    parts = volume[:-len('.nii.gz')].split('__') if volume.endswith('.nii.gz') else volume.split('__')
    src, case = parts[0], parts[1] if len(parts) > 1 else parts[0]
    return f'{src}__{_SUFFIX.sub("", case)}'


# A30 QC (a30_grouping_qc.py): the ingest code's patient ids where the name heuristic is wrong.
# tools/ccta/ingest_open.py: the SDN_CASES records are one patient each (patient_id=f'SDN-{did}'; sNNN is a series),
# and Slicer multi-phase sequences are stored one case per frame (<name>_fNN, patient_id=name).
SDN_ONE_PATIENT = {'37nnfyh3x9', '4643nn2z44', '7x9kb53262', 'spb25zt2c4'}
_FRAME = re.compile(r'_f\d+$')


def corrected_key(volume: str) -> str:
    """The patient a volume belongs to according to the ingest code (else the heuristic)."""
    src = source_of(volume)
    rec = src[len('Mendeley-SDN-'):] if src.startswith('Mendeley-SDN-') else None
    if rec in SDN_ONE_PATIENT:
        return f'{src}__SDN-{rec}'
    if src == 'Slicer-SampleData':
        return f'{src}__{_FRAME.sub("", volume[:-len(".nii.gz")].split("__")[1])}'
    return patient_key(volume)


def source_of(volume: str) -> str:
    return volume.split('__')[0]


def sha256(path: str) -> str:
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def seal_path() -> str:
    if os.path.exists(CANONICAL_SEAL):
        if os.path.exists(PROPOSAL_SEAL) and sha256(CANONICAL_SEAL) != sha256(PROPOSAL_SEAL):
            raise RuntimeError('the canonical seal and the Round 9 proposal differ: a seal change must be an '
                               'explicit PR flagged to the PM (D27); refusing to guess which one holds')
        return CANONICAL_SEAL
    return PROPOSAL_SEAL


class Seal:
    """The patients whose volumes the wave-1 tools must never open."""

    def __init__(self, path: str | None = None, pool_list: str | None = POOL_LIST):
        self.path = path or seal_path()
        d = json.load(open(self.path))
        self.sealed = set(d['primary']['patients']) | set(d['report_only']['patients'])
        self.extension_order = list(d['primary']['extension_order'])
        self.reserved = set(self.extension_order[:EXTENSION_RESERVED])
        self.sealed_volumes = set(d['primary']['volumes']) | set(d['report_only']['volumes'])
        self.pool = None
        if pool_list:
            self.pool = {l.strip() for l in open(pool_list) if l.strip() and not l.startswith('#')}
        # A30: refuse by the ingest code's patient too, so a volume of a sealed person that the heuristic split off
        # (60 volumes on the Round 9 seal) is never opened. Stricter than the seal file; the file is not changed.
        pool = self.pool or self.sealed_volumes
        self.sealed_corrected = {corrected_key(v) for v in pool if patient_key(v) in self.sealed} | {
            corrected_key(v) for v in self.sealed_volumes}
        self.reserved_corrected = {corrected_key(v) for v in pool if patient_key(v) in self.reserved}

    def reason(self, volume: str) -> str | None:
        """Why ``volume`` must not be opened, or None."""
        if self.pool is not None and volume not in self.pool:
            return 'not in the pool list (cannot prove it unsealed)'
        if volume in self.sealed_volumes or patient_key(volume) in self.sealed:
            return 'sealed (D27 acceptance set)'
        if corrected_key(volume) in self.sealed_corrected:
            return 'same patient as a sealed volume (A30 QC: the seal file under-groups this patient)'
        if patient_key(volume) in self.reserved or corrected_key(volume) in self.reserved_corrected:
            return 'reserved for the pre-registered seal extension (200/250)'
        return None


class SealedVolumeError(RuntimeError):
    pass


def check_tf1_pin() -> str:
    h = sha256(os.path.join(REPO, 'src', 'segtrain', 'tf1.py'))
    if h != TF1_PIN:
        raise RuntimeError(f'src/segtrain/tf1.py sha256 {h} is not the A1c pin {TF1_PIN}: refusing to score')
    return h


def boot_ci(x, n_boot: int = 2000, seed: int = 0, stat=np.mean):
    """(estimate, [lo, hi] 95 % percentile bootstrap, n). None for an empty sample."""
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    if len(x) == 0:
        return None, None, 0
    est = float(stat(x))
    if len(x) < 3:
        return round(est, 4), None, len(x)
    rng = np.random.default_rng(seed)
    b = np.array([stat(x[rng.integers(0, len(x), len(x))]) for _ in range(n_boot)])
    return round(est, 4), [round(float(np.percentile(b, 2.5)), 4), round(float(np.percentile(b, 97.5)), 4)], len(x)


def sd(x) -> float | None:
    x = np.asarray([v for v in x if v is not None and np.isfinite(v)], float)
    return float(x.std(ddof=1)) if len(x) >= 3 else None
