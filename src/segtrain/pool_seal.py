"""The D27 pool seal: SegQueue14 pool patients no training, prelabel or analysis export may use.

D27 adopts Bridge's Round 9 A30 proposal as the acceptance set: 150 pool patients (216 volumes)
plus 20 ImageCHD patients scored report-only. Until acceptance scoring, no volume of a listed
patient is trained on, prelabelled or inspected, and no read of one is exported for analysis.
Annotators still read them like any other case (D23); nothing here touches the queue.

The list is ``configs/segqueue14/sealed-pool-2026-10.json``, a byte-for-byte copy of
``experiments/Bridge/r9/sealed_pool_proposal.json``, pinned by :data:`SEAL_SHA256`. Every load
checks that hash, so a seal file found through ``--seal-file`` or ``SEGTRAIN_POOL_SEAL`` is the
same seal. Extending it (the pre-registered ``extension_order``, to 200-250 patients) is a later,
explicit change to the file and the hash, never something a caller does.

A name is sealed when, after its directory, volume extension (``.nii.gz``, nnU-Net's ``_0000``
channel) and read suffix (``__r2``) are removed, it is a sealed volume's stem or a sealed patient
id, or its patient key (Bridge's rule: ``<Source>__<case>`` without ``_tp0`` / ``_p06`` /
``_diast`` / ``_s1``) is a sealed patient, **or its patient as the ingest assigns it**
(:func:`ingest_patient`) is the patient of any sealed volume. Several volumes of one patient
are all sealed or none.

The last rule is A30's grouping QC (#87): Bridge's name rule under-groups six patients, 60 pool
volumes. Each single-patient Mendeley-SDN record is one patient (``patient_id=SDN-<did>`` in
``tools/ccta/ingest_open.py``; ``sNNN`` is a series), and a Slicer 4D sequence is stored one case
per frame (``<name>_fNN``, ``patient_id=<name>``). The seal file stays Bridge's list byte for byte
(changing it needs the lead); the guard refuses by patient.

Three modes for a caller holding a list of names (:func:`apply`):

* ``refuse`` (the default everywhere): any sealed name raises :class:`SealedPoolError`;
* ``exclude``: sealed names are dropped and the count is logged;
* ``acceptance``: kept, and logged, for acceptance scoring only.

Standard library only: the SegQueue14 export imports it inside Girder, which has no numpy.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

log = logging.getLogger("segtrain.pool_seal")

#: Repository-relative path of the canonical seal file.
SEAL_RELPATH = "configs/segqueue14/sealed-pool-2026-10.json"
#: sha256 of that file. Changing the seal means changing this, in its own reviewed PR.
SEAL_SHA256 = "8f529842934bfb72883a7da593b128ad6c091aecb8228005e9792cd8d92c1183"
#: Environment variable naming the seal file, for an installed (non-checkout) package.
SEAL_ENV = "SEGTRAIN_POOL_SEAL"

REFUSE, EXCLUDE, ACCEPTANCE = "refuse", "exclude", "acceptance"
MODES = (REFUSE, EXCLUDE, ACCEPTANCE)

_VOLUME_SUFFIXES = (".seg.nrrd", ".nii.gz", ".nrrd", ".nii", ".mha", ".mhd", ".npz", ".npy",
                    ".pkl", ".b2nd")
_CHANNEL = re.compile(r"_\d{4}$")                      # nnU-Net imagesTr channel suffix
_READ_SUFFIX = re.compile(r"(__r\d+|_r[A-Za-z0-9]+)$")  # as segtrain.proxy
# Bridge's patient rule (experiments/Bridge/r9/seal_pool.py): time point, phase, series.
_PATIENT_SUFFIX = re.compile(r"(_tp\d+|_p\d+|_(diast|syst)|_s\d+)$", re.I)


#: Mendeley-SDN records that hold one patient (``SDN_CASES`` in tools/ccta/ingest_open.py,
#: ``patient_id=f'SDN-{did}'``). ``cy54ttk3fj`` is not one: 40 patients, ``P<NN>_diast/_syst``.
SDN_SINGLE_PATIENT_RECORDS = frozenset({"7x9kb53262", "37nnfyh3x9", "4643nn2z44", "spb25zt2c4"})
#: The source whose sequences are stored one case per frame (``run_slicer``, ``patient_id=name``).
SLICER_SOURCE = "Slicer-SampleData"
_FRAME = re.compile(r"_f\d+$")


def ingest_patient(stem: str) -> Optional[str]:
    """The patient behind a pool volume stem, as ``tools/ccta/ingest_open.py`` assigns it;
    Bridge's name rule for every other source. None for a name with no ``<Source>__``."""
    parts = stem.split("__")
    if len(parts) < 2:
        return None
    src, case = parts[0], parts[1]
    if src.startswith("Mendeley-SDN-") and src[len("Mendeley-SDN-"):] in SDN_SINGLE_PATIENT_RECORDS:
        return src
    if src == SLICER_SOURCE:
        return f"{src}__{_FRAME.sub('', case)}"
    return _patient_key(stem)


class SealedPoolError(RuntimeError):
    """A sealed pool volume reached a path that may not use it (D27)."""


def _stem(name: str) -> str:
    base = str(name).strip().replace("\\", "/").rsplit("/", 1)[-1]
    lower = base.lower()
    for suffix in _VOLUME_SUFFIXES:
        if lower.endswith(suffix):
            return base[: -len(suffix)]
    return base


def _patient_key(stem: str) -> Optional[str]:
    parts = stem.split("__")
    if len(parts) < 2:
        return None
    return f"{parts[0]}__{_PATIENT_SUFFIX.sub('', parts[1])}"


@dataclass(frozen=True)
class PoolSeal:
    """The loaded seal. ``volumes`` are stems (no ``.nii.gz``); ``patients`` include report-only."""

    path: str
    sha256: str
    volumes: frozenset
    patients: frozenset
    report_only_patients: frozenset
    extension_order: tuple
    ingest_patients: frozenset = frozenset()

    def reason(self, name) -> Optional[str]:
        """Why ``name`` is sealed (D27), or None if it is not."""
        stem = _stem(name)
        forms = {stem}
        for s in list(forms):
            forms.add(_CHANNEL.sub("", s))
        for s in list(forms):
            forms.add(_READ_SUFFIX.sub("", s))
        for s in sorted(forms):
            if s in self.volumes:
                return f"{name}: sealed pool volume {s} (D27)"
            if s in self.patients:
                return f"{name}: sealed pool patient {s} (D27)"
            key = _patient_key(s)
            if key and key in self.patients:
                return f"{name}: volume of sealed pool patient {key} (D27)"
            ingest = ingest_patient(s)
            if ingest and ingest in self.ingest_patients:
                return f"{name}: volume of sealed pool patient {ingest} (ingest patient id; D27)"
        return None

    def is_sealed(self, name) -> bool:
        return self.reason(name) is not None

    def split(self, names: Iterable) -> tuple:
        """``(kept, sealed_reasons)``, order kept."""
        kept, sealed = [], []
        for n in names:
            why = self.reason(n)
            (sealed.append(why) if why else kept.append(n))
        return kept, sealed


def default_path() -> Path:
    """``$SEGTRAIN_POOL_SEAL``, else the checkout's file, else ``./configs/...``."""
    env = os.environ.get(SEAL_ENV)
    if env:
        return Path(env)
    repo = Path(__file__).resolve().parents[2] / SEAL_RELPATH
    if repo.is_file():
        return repo
    return Path.cwd() / SEAL_RELPATH


def load_pool_seal(path=None) -> PoolSeal:
    """Load and verify the seal. A missing file or a wrong hash is an error, never a pass."""
    p = Path(path) if path else default_path()
    if not p.is_file():
        raise FileNotFoundError(
            f"D27 pool seal not found at {p}; refusing to go on without it. Point --seal-file or "
            f"{SEAL_ENV} at {SEAL_RELPATH} in a checkout.")
    raw = p.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != SEAL_SHA256:
        raise SealedPoolError(
            f"{p}: sha256 {digest} is not the pinned D27 seal {SEAL_SHA256}; a seal change is an "
            "explicit PR to the seal file and segtrain.pool_seal.SEAL_SHA256")
    data = json.loads(raw.decode("utf-8"))
    prim, rep = data["primary"], data["report_only"]
    vols = frozenset(_stem(v) for v in list(prim["volumes"]) + list(rep["volumes"]))
    pats = frozenset(list(prim["patients"]) + list(rep["patients"]))
    if not vols or not pats:
        raise SealedPoolError(f"{p}: no sealed volumes or patients")
    return PoolSeal(path=str(p), sha256=digest, volumes=vols, patients=pats,
                    report_only_patients=frozenset(rep["patients"]),
                    extension_order=tuple(prim.get("extension_order", ())),
                    ingest_patients=frozenset(filter(None, map(ingest_patient, vols))))


def apply(names: Iterable, mode: str = REFUSE, what: str = "this step",
          seal: Optional[PoolSeal] = None) -> list:
    """Apply the seal to ``names`` for ``what``; return the names that may go on.

    ``refuse`` raises on any sealed name; ``exclude`` drops them and logs the count;
    ``acceptance`` keeps them and logs the count (acceptance scoring only)."""
    if mode not in MODES:
        raise ValueError(f"pool seal mode {mode!r} is not one of {MODES}")
    names = list(names)
    seal = seal if seal is not None else load_pool_seal()
    kept, sealed = seal.split(names)
    if not sealed:
        return names
    if mode == REFUSE:
        raise SealedPoolError(
            f"refusing {what}: {len(sealed)} of {len(names)} name(s) are sealed pool volumes "
            f"(D27), e.g. {sealed[:3]}. Pass the explicit exclude-sealed mode to drop them.")
    if mode == EXCLUDE:
        log.warning("%s: excluded %d sealed pool volume(s) of %d (D27)", what, len(sealed),
                    len(names))
        return kept
    log.warning("%s: ACCEPTANCE mode, %d sealed pool volume(s) of %d included (D27)", what,
                len(sealed), len(names))
    return names
