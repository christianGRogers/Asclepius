"""Projected 4-class proxy labels: the R1 training target before any team read exists.

The binding convention ([[Human decisions]] D0, D1, D1b) is the *original ImageCAS mask* -- the
binary mask every case already carries -- split into LM / LAD / LCx / RCA, side branches taking
their parent's class (territory), ramus intermedius -> LCx. ImageCAS-X (Bransby et al.,
arXiv:2608.30404; Zenodo 10.5281/zenodo.21887809, CC BY 4.0) supplies expert per-segment names
for 800 of the 1000 cases on the same voxel grid (ImageCAS id ``n`` is our case ``c{n-1:04d}``).
Its lumen is ~3x thinner than ours, so its *names* are projected onto *our* mask:

1. every mask voxel within ``near_mm`` (2 mm) of an ImageCAS-X voxel takes that voxel's class;
2. the remaining mask voxels inherit a class by geodesic growth inside the mask;
3. mask voxels no growth reaches (specks with no named neighbour) stay background.

The 14 ImageCAS-X classes collapse to 4 by ``ICX_TO_4`` (territory + ramus -> LCx). Class 14
("Other": D3/D4/OM3/OM4) has no fixed parent and is left to step 2, so it inherits from the
vessel it hangs off.

Amendment A4 adds a QA layer: Bridge's rule namer (``segtrain.namer``) names the same mask
independently; voxels where the two disagree become nnU-Net's ``ignore`` label, cases with a
wholesale disagreement are excluded until reviewed, and a ramus-only disagreement never excludes
a case. ``qa_with_namer`` applies it when ``segtrain.namer`` is importable; without it the proxy
is written un-masked and the case record says so.

The output is a source tree in the repo's nested layout (``<case>/ct.nii.gz`` +
``<case>/labels.nii.gz``), so ``segtrain index`` and ``convert`` (task 712, label set
``coronary_branches``) consume it unchanged. Sealed cases (A14, ``trillium/sealed_test.json``)
are never written: ``build_proxy_tree`` refuses them, so a sealed case cannot enter a training
set through this module.

Ported from the experiment code that produced the R1 labels (``trillium/atlas/lib/proxy.py``).
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional

import numpy as np

# ImageCAS-X segment index -> project class (0 = background / left to geodesic growth)
#  1 LM 2 LAD 3 LCx 4 D1 5 D2 6 OM1 7 OM2 8 IM 9 RCA 10 R-PDA 11 R-PLA 12 L-PDA 13 L-PLA 14 Other
ICX_TO_4: dict[int, int] = {
    1: 1,
    2: 2,
    4: 2,
    5: 2,
    3: 3,
    6: 3,
    7: 3,
    8: 3,
    12: 3,
    13: 3,
    9: 4,
    10: 4,
    11: 4,
}
CLASS_NAMES = {
    1: "left_main",
    2: "left_anterior_descending",
    3: "left_circumflex",
    4: "right_coronary_artery",
}
IGNORE = 5

_LUT = np.zeros(256, np.uint8)
for _k, _v in ICX_TO_4.items():
    _LUT[_k] = _v


def imagecas_id_to_case(n: int) -> str:
    """ImageCAS / ImageCAS-X id ``n`` (1-based) -> tournament case id ``c{n-1:04d}``."""
    return f"c{int(n) - 1:04d}"


def case_to_imagecas_id(case: str) -> int:
    return int(case[1:]) + 1


# ------------------------------------------------------------------ case identity (A14, Echo D2)
#: Suffixes that name one read of a case rather than a case: SegQueue's export writes the second
#: read as ``<case>__r2`` (``--replicas all``); per-read training samples use ``<case>_rA``.
_READ_SUFFIX = re.compile(r"(__r\d+|_r[A-Za-z0-9]+)$")


def split_read_suffix(name: str) -> tuple[str, str]:
    """``"c0002__r2" -> ("c0002", "__r2")``; ``"c0002" -> ("c0002", "")``."""
    s = str(name).strip()
    m = _READ_SUFFIX.search(s)
    return (s[: m.start()], m.group(1)) if m else (s, "")


def canonical_case(name) -> Optional[str]:
    """The tournament case id (``cNNNN``) behind any name a case travels under, or None.

    Every sealed-test check (A14) and every ImageCAS-X lookup keys on this, never on the raw
    name. Accepted forms:

    * ``c0002`` (tournament id);
    * ``imagecas_0003`` (SegQueue's case name, 1-based ImageCAS id) -> ``c0002``;
    * ``3``, ``3.img``, ``3.label`` (the ImageCAS release's flat file stems) -> ``c0002``;
    * any of these with a read suffix (``__r2``, ``_rA``) -> the same case.
    """
    base, _ = split_read_suffix(name)
    if re.fullmatch(r"c\d{4}", base):
        return base
    m = (re.fullmatch(r"(?i:imagecas)[_-]?(\d+)", base)
         or re.fullmatch(r"(\d+)(?:\.(?:img|label))?", base))
    if m:
        n = int(m.group(1))
        if 1 <= n <= 1000:
            return imagecas_id_to_case(n)
    return None


def case_id(name) -> str:
    """The case key for any name: :func:`canonical_case` when the name maps to a case, else the
    name with its read suffix removed. Never invents a ``cNNNN`` for an unmappable name
    (``imagecas_1001`` stays ``imagecas_1001``). The one implementation of case identity in
    ``segtrain``; ``segtrain.reads`` re-exports it."""
    return canonical_case(name) or split_read_suffix(name)[0]


def read_name(name) -> str:
    """The read a folder holds: ``__rK`` -> ``rK``, ``_rX`` -> ``rX``, no suffix -> ``r1``."""
    suffix = split_read_suffix(name)[1]
    return suffix.lstrip("_") if suffix else "r1"


def sealed_reason(name, sealed: set) -> Optional[str]:
    """Why ``name`` may not enter training under a sealed list (A14), or None if it may.

    A name that maps to a sealed case is refused; with a sealed list in force, so is a name that
    maps to no case at all: an identity nobody can check is treated as sealed, never as open."""
    case = canonical_case(name)
    if case is None:
        return f"{name}: name does not map to a case id (cNNNN / imagecas_NNNN); refused under A14"
    if case in sealed:
        return f"{name}: sealed case {case} (A14)"
    return None


# ------------------------------------------------------------------ sealed test (A14)
def load_sealed(path: Optional[Path] = None) -> set[str]:
    """Case ids of the sealed test (A14). Accepts the orchestrator's JSON (``sealed_icx_test`` +
    ``sealed_quality0``) or a plain list. ``path`` defaults to ``<repo>/trillium/sealed_test.json``.
    Missing file -> error: a training path must never run without knowing what is sealed."""
    if path is None:
        path = Path(__file__).resolve().parents[2] / "trillium" / "sealed_test.json"
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(
            f"sealed-test list not found at {path}; refusing to build training data without it"
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, list):
        return {str(c) for c in data}
    out: set[str] = set()
    for key in ("sealed_icx_test", "sealed_quality0", "sealed"):
        out |= {str(c) for c in data.get(key, [])}
    if not out:
        raise ValueError(f"{path}: no sealed cases found (keys {sorted(data)})")
    return out


# ------------------------------------------------------------------ projection
@dataclass
class ProxyStats:
    mask_vox: int = 0
    icx_vox: int = 0
    near_frac: float = 0.0
    geodesic_frac: float = 0.0
    unreached_frac: float = 0.0
    class_vox: dict = field(default_factory=dict)
    empty: bool = False

    def as_dict(self) -> dict:
        return dict(self.__dict__)


def project_names(
    mask: np.ndarray, icx: np.ndarray, spacing, near_mm: float = 2.0, max_iter: int = 600
) -> tuple[np.ndarray, ProxyStats]:
    """Project ImageCAS-X names onto a binary mask on the same grid.

    ``mask``: bool/0-1 array (our ImageCAS mask). ``icx``: integer ImageCAS-X labels 0..14, same
    shape. Returns ``(label, stats)`` with ``label`` uint8 0..4.
    """
    from scipy import ndimage as ndi

    if mask.shape != icx.shape:
        raise ValueError(f"mask {mask.shape} and ImageCAS-X {icx.shape} grids differ")
    m = np.asarray(mask) > 0
    L = np.asarray(icx).astype(np.uint8)
    out = np.zeros(m.shape, np.uint8)
    st = ProxyStats(mask_vox=int(m.sum()), icx_vox=int((L > 0).sum()))
    if not m.any() or not (L > 0).any():
        st.empty = True
        return out, st
    idx = np.nonzero(m | (L > 0))
    lo = np.maximum([i.min() - 3 for i in idx], 0)
    hi = np.minimum([i.max() + 4 for i in idx], m.shape)
    sl = tuple(slice(int(a), int(b)) for a, b in zip(lo, hi))
    mc, Lc = m[sl], _LUT[L[sl]]
    named = Lc > 0
    sp = np.asarray(spacing, float)
    d, inds = ndi.distance_transform_edt(~named, sampling=sp, return_indices=True)
    near = mc & (d <= near_mm)
    lab = np.zeros(mc.shape, np.uint8)
    lab[near] = Lc[tuple(ind[near] for ind in inds)]
    del d, inds
    todo = mc & (lab == 0)
    footprint = np.ones((3, 3, 3), bool)
    for _ in range(max_iter):
        if not todo.any():
            break
        grown = ndi.grey_dilation(lab, footprint=footprint)
        new = todo & (grown > 0)
        if not new.any():
            break
        lab[new] = grown[new]
        todo &= ~new
    n = max(int(mc.sum()), 1)
    st.near_frac = float(near.sum() / n)
    st.geodesic_frac = float(((lab > 0) & ~near & mc).sum() / n)
    st.unreached_frac = float(todo.sum() / n)
    st.class_vox = {c: int((lab == c).sum()) for c in range(1, 5)}
    out[sl] = lab * mc
    return out, st


# ------------------------------------------------------------------ A4 QA via segtrain.namer
@dataclass
class QAResult:
    applied: bool
    ignore_voxels: int = 0
    excluded: bool = False
    ramus_only: bool = False
    reason: str = ""


def namer_disagreement():
    """Bridge's ``segtrain.namer.disagreement``, or RuntimeError saying why it is unavailable."""
    try:
        from segtrain import namer  # Bridge's module (A4/A7/A8)

        return namer.disagreement
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            f"A4 proxy QA unavailable: segtrain.namer.disagreement cannot be imported ({exc!r}); "
            "refusing to write proxies without it (pass apply_qa=False only to build an "
            "explicitly un-QA'd tree)") from exc


def qa_with_namer(label: np.ndarray, mask: np.ndarray, spacing) -> tuple[np.ndarray, QAResult]:
    """A4: compare the proxy with Bridge's rule namer on the same mask.

    Uses ``segtrain.namer.disagreement(label, mask, spacing)`` if the module exists. It is
    expected to return a mapping with ``ignore`` (bool array, voxels to mask), ``exclude`` (bool,
    wholesale disagreement) and ``ramus_only`` (bool). Under the ramus-only exemption, voxels are
    NOT ignored: the proxy's name is the expert's (master plan v4 §2.1).

    If the namer cannot be imported (the module, or one of its dependencies such as scipy or
    scikit-image in a fresh venv) this **raises**: a proxy written without A4 has no carina
    ``ignore`` and no wholesale-disagreement exclusion, and must never pass for a QA'd one (Round 6,
    A21a). Callers that want no QA say so with ``apply_qa=False``.
    """
    fn = namer_disagreement()
    rep = fn(label, mask, spacing)
    ramus_only = bool(rep.get("ramus_only", False))
    excluded = bool(rep.get("exclude", False)) and not ramus_only
    out = label.copy()
    n_ign = 0
    if not ramus_only and rep.get("ignore") is not None:
        ign = np.asarray(rep["ignore"], bool) & (label > 0)
        out[ign] = IGNORE
        n_ign = int(ign.sum())
    return out, QAResult(
        applied=True,
        ignore_voxels=n_ign,
        excluded=excluded,
        ramus_only=ramus_only,
        reason=str(rep.get("reason", "")),
    )


# ------------------------------------------------------------------ building a source tree for
# convert
@dataclass
class ProxyCaseRecord:
    case: str
    ok: bool
    stats: dict = field(default_factory=dict)
    qa: dict = field(default_factory=dict)
    excluded: bool = False
    error: str = ""


def make_case(
    case: str,
    ct_path: Path,
    mask_path: Path,
    icx_path: Path,
    out_root: Path,
    apply_qa: bool = True,
    near_mm: float = 2.0,
) -> ProxyCaseRecord:
    """Write one case into ``out_root`` in the nested layout ``segtrain index``/``convert`` read.

    ``<out_root>/<case>/ct.nii.gz`` is a symlink to the CT; ``<out_root>/<case>/labels.nii.gz`` is
    the uint8 proxy (0..4, plus 5 = ignore where A4 masks). Case ids stay ``cNNNN`` so the sealed
    list and splits apply unchanged. An excluded case (A4 wholesale disagreement) is not written at
    all. Never raises."""
    import nibabel as nib

    try:
        mi = nib.load(str(mask_path))
        li = nib.load(str(icx_path))
        if mi.shape[:3] != li.shape[:3] or not np.allclose(mi.affine, li.affine, atol=1e-2):
            return ProxyCaseRecord(case, False, error="mask and ImageCAS-X grids differ")
        sp = mi.header.get_zooms()[:3]
        mask = np.asarray(mi.dataobj) > 0.5
        lab, st = project_names(mask, np.asarray(li.dataobj), sp, near_mm=near_mm)
        rec = ProxyCaseRecord(case, True, stats=st.as_dict())
        if apply_qa:
            # the affine, not just spacing: the namer's left/right decisions depend on orientation
            lab, qa = qa_with_namer(lab, mask, mi.affine)
            rec.qa = dict(qa.__dict__)
            rec.excluded = qa.excluded
        if rec.excluded:
            return rec
        case_dir = Path(out_root) / case
        case_dir.mkdir(parents=True, exist_ok=True)
        img = case_dir / "ct.nii.gz"
        if not img.exists():
            os.symlink(os.path.abspath(ct_path), img)
        dst = case_dir / "labels.nii.gz"
        tmp = case_dir / "labels.tmp.nii.gz"
        out = nib.Nifti1Image(lab, mi.affine)
        out.set_data_dtype(np.uint8)
        nib.save(out, str(tmp))
        os.replace(tmp, dst)
        return rec
    except Exception as exc:  # worker boundary
        return ProxyCaseRecord(case, False, error=f"{type(exc).__name__}: {exc}")


def icx_split(icx_dir: Path) -> dict[str, list[str]]:
    """ImageCAS-X's own split as case ids.

    Reads the filelist ``train.txt`` / ``val.txt`` / ``test.txt`` / ``exclude.txt``.
    """
    out = {}
    for name in ("train", "val", "test", "exclude"):
        p = Path(icx_dir) / f"{name}.txt"
        if p.is_file():
            out[name] = [imagecas_id_to_case(int(x)) for x in p.read_text().split()]
    return out


def icx_label_path(icx_dir: Path, case: str) -> Path:
    """The ImageCAS-X label file of ``case``: flat (``<dir>/<id>.coronary.nii.gz``, the Trillium
    fetch) or as unzipped from Zenodo (``<dir>/segmentations/<id>.coronary.nii.gz``)."""
    name = f"{case_to_imagecas_id(case)}.coronary.nii.gz"
    flat = Path(icx_dir) / name
    nested = Path(icx_dir) / "segmentations" / name
    return nested if not flat.exists() and nested.exists() else flat


def build_proxy_tree(
    cases: dict[str, dict],
    icx_dir: Path,
    out_root: Path,
    sealed: set[str],
    subsets: Iterable[str] = ("train", "val"),
    workers: int = 1,
    apply_qa: bool = True,
) -> list[ProxyCaseRecord]:
    """Build the proxy source tree for every ImageCAS-X ``subsets`` case present in ``cases``.

    ``cases`` is ``{case: {"ct": path, "mask": path}}``. A sealed case among the requested subsets
    raises. Writes ``proxy_report.json`` in ``out_root``. Only ImageCAS-X train/val are proxied by
    default: the test cases (80 sealed, the rest open for evaluation) enter training only with team
    reads, and quality-0 cases have no ImageCAS-X labels at all."""
    from concurrent.futures import ProcessPoolExecutor

    if apply_qa:
        namer_disagreement()          # fail before any case is written (A21a), never per case
    split = icx_split(icx_dir)
    wanted = [c for s in subsets for c in split.get(s, [])]
    # Key the available cases by their canonical id, so a Girder/SegQueue tree named imagecas_NNNN
    # proxies the same cases as one named cNNNN (Echo D2).
    cases = {canonical_case(k) or k: v for k, v in cases.items()}
    leaked = sorted(set(wanted) & sealed)
    if leaked:
        raise ValueError(
            f"{len(leaked)} sealed case(s) in the requested subsets, e.g. {leaked[:3]}; refusing"
        )
    jobs = [c for c in wanted if c in cases]
    out_root = Path(out_root)
    args = [
        (
            c,
            cases[c]["ct"],
            cases[c]["mask"],
            icx_label_path(icx_dir, c),
            out_root,
            apply_qa,
        )
        for c in jobs
    ]
    if workers > 1:
        with ProcessPoolExecutor(max_workers=workers) as pool:
            recs = list(pool.map(make_case, *zip(*args))) if args else []
    else:
        recs = [make_case(*a) for a in args]
    out_root.mkdir(parents=True, exist_ok=True)
    (out_root / "proxy_report.json").write_text(
        json.dumps(
            dict(
                subsets=list(subsets),
                n_requested=len(wanted),
                n_present=len(jobs),
                missing=sorted(set(wanted) - set(jobs)),
                n_ok=sum(r.ok for r in recs),
                n_excluded=sum(r.excluded for r in recs),
                qa_applied=any(r.qa.get("applied") for r in recs),
                cases=[r.__dict__ for r in recs],
            ),
            indent=1,
        ),
        encoding="utf-8",
    )
    return recs
