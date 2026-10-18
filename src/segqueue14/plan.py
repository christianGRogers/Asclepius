"""What each SegQueue14 case wants: how many reads, in what order, and when its
prelabel may be swapped. Pure functions of names and counters, so every decision
the population and prelabel tools make can be tested without Girder.

Decisions implemented here (vault/Plans/Human decisions.md):

* **D11** -- ImageCAS-X cases want one read, with ~10 % of them served to a
  second annotator as blind duplicates; the 200 cases ImageCAS-X does not cover
  want two reads.
* **D14 / D16** -- serve order: ImageCAS-X train/val cases first, then the 200
  unlabelled ImageCAS cases, then the 160 ImageCAS-X test cases last.
* **D15 / D16** -- one prelabel refresh, only on cases nobody has submitted, and
  never on the held-out test cases.
* **D17** -- new CCTA datasets arrive as further cases with two reads and a
  dataset tag.

The order is *data*: a priority number on each case (``/next`` serves the
highest first) and a replica count, written by ``segqueue14-populate``. Nothing
here or in the server names a case id.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

# ----------------------------------------------------------- case identity

#: The live SegQueue names its ImageCAS cases ``imagecas_NNNN`` with NNNN the
#: ImageCAS id (1..1000). The tournament and the 4-class model use ``cNNNN`` with
#: NNNN = id - 1 (trillium/icx4/lib/layout.py); ImageCAS-X names its files
#: ``<id>.coronary.nii.gz``.
_CASE_RE = re.compile(r"^imagecas_(\d{1,4})$")
_TOURNAMENT_RE = re.compile(r"^c(\d{4})$")
_ICX_FILE_RE = re.compile(r"^(\d{1,4})\.coronary\.nii(?:\.gz)?$")

#: Suffixes stripped when a prediction file is mapped back to a case name.
_VOLUME_SUFFIXES = (".prelabel.nii.gz", ".nii.gz", ".nii", ".nrrd", ".seg.nrrd",
                    ".mha", ".nhdr")
#: The same, longest first, so ``.seg.nrrd`` is stripped whole before ``.nrrd``.
_SUFFIXES_LONGEST_FIRST = tuple(sorted(_VOLUME_SUFFIXES, key=len, reverse=True))


def imagecas_id(case_name: str) -> Optional[int]:
    """``imagecas_0002`` -> 2. None for a name that is not an ImageCAS case."""
    m = _CASE_RE.match(case_name or "")
    if not m:
        return None
    n = int(m.group(1))
    return n if 1 <= n <= 1000 else None


def case_name_for_imagecas_id(n: int) -> str:
    """2 -> ``imagecas_0002``; the inverse of ``imagecas_id``."""
    return f"imagecas_{int(n):04d}"


def strip_volume_suffix(filename: str) -> str:
    """The file's name without its directory or a known volume extension.

    ``cases/c0001.seg.nrrd`` -> ``c0001``. Matched case-insensitively; an unknown
    extension is left on.
    """
    base = filename.rsplit("/", 1)[-1]
    lower = base.lower()
    for suffix in _SUFFIXES_LONGEST_FIRST:
        if lower.endswith(suffix):
            return base[: -len(suffix)]
    return base


def case_name_for_prediction(filename: str) -> str:
    """The SegQueue14 case a prediction file belongs to.

    ``c0001.nii.gz`` (the model's own naming, id - 1) -> ``imagecas_0002``;
    ``imagecas_0002.nii.gz`` -> ``imagecas_0002``; anything else -> its stem, which
    is how a prediction for a non-ImageCAS case (D17) is named after that case.
    """
    stem = strip_volume_suffix(filename)
    m = _TOURNAMENT_RE.match(stem)
    if m:
        n = int(m.group(1)) + 1
        if 1 <= n <= 1000:
            return case_name_for_imagecas_id(n)
    return stem


def case_name_for_reference(item_name: str, meta: Optional[Mapping] = None) -> Optional[str]:
    """The case an ImageCAS-X segmentation item belongs to.

    The item's ``segqueue_case`` metadata wins when present (that is what it is
    for); otherwise ``<id>.coronary.nii.gz`` -> ``imagecas_<id>``.
    """
    if meta:
        named = meta.get("segqueue_case")
        if isinstance(named, str) and named.strip():
            return named.strip()
    m = _ICX_FILE_RE.match(item_name or "")
    if m:
        n = int(m.group(1))
        if 1 <= n <= 1000:
            return case_name_for_imagecas_id(n)
    return None


# ------------------------------------------------------------------ splits

TRAIN, VAL, TEST, EXCLUDE = "train", "val", "test", "exclude"
SPLITS = (TRAIN, VAL, TEST, EXCLUDE)

#: Spellings seen in ImageCAS-X file lists and metadata, normalised.
_SPLIT_ALIASES = {
    "train": TRAIN, "training": TRAIN, "tr": TRAIN,
    "val": VAL, "valid": VAL, "validation": VAL,
    "test": TEST, "testing": TEST, "ts": TEST,
    "exclude": EXCLUDE, "excluded": EXCLUDE, "none": EXCLUDE,
}


def normalise_split(value: Any) -> Optional[str]:
    """Any spelling in ``_SPLIT_ALIASES`` -> its split constant; None otherwise."""
    if value is None:
        return None
    return _SPLIT_ALIASES.get(str(value).strip().lower())


def parse_id_list(text: str) -> List[int]:
    """ImageCAS ids from an ImageCAS-X file list.

    The lists are whitespace or comma separated integers (``train.txt``); also
    accepted: ``imagecas_0002``, ``c0001`` and ``2.coronary.nii.gz`` tokens, so a
    hand-made list in any of the project's spellings means the same thing.
    """
    out = []
    for token in re.split(r"[\s,;]+", text or ""):
        token = token.strip()
        if not token or token.startswith("#"):
            continue
        if token.isdigit():
            out.append(int(token))
            continue
        name = case_name_for_prediction(token)
        n = imagecas_id(name)
        if n is None:
            m = _ICX_FILE_RE.match(token)
            n = int(m.group(1)) if m else None
        if n is not None:
            out.append(n)
    return out


def splits_from_lists(lists: Mapping[str, str]) -> Dict[int, str]:
    """``{"train": "<text of train.txt>", ...}`` -> ``{imagecas id: split}``.

    Raises ``ValueError`` when an id is in two lists: ImageCAS-X's own lists are
    disjoint, so overlap means a wrong file, and guessing which list wins could put
    a held-out test case at the front of the queue.
    """
    out: Dict[int, str] = {}
    for key, text in lists.items():
        split = normalise_split(key)
        if split is None:
            continue
        for n in parse_id_list(text):
            previous = out.get(n)
            if previous is not None and previous != split:
                raise ValueError(
                    f"ImageCAS id {n} is in both the {previous} and the {split} list")
            out[n] = split
    return out


def split_list_name(filename: str) -> Optional[str]:
    """``train.txt`` / ``test_list.txt`` / ``val.csv`` -> the split, else None."""
    stem = filename.rsplit("/", 1)[-1].lower()
    for suffix in (".txt", ".csv", ".lst", ".list"):
        if stem.endswith(suffix):
            stem = stem[: -len(suffix)]
            break
    else:
        return None
    for tail in ("_list", "-list", "_ids", "-ids", "list", "_split"):
        if stem.endswith(tail) and stem != tail:
            stem = stem[: -len(tail)]
            break
    return normalise_split(stem)


# --------------------------------------------------------------- the tiers

#: Serve tiers, highest priority first. ``/next`` sorts by priority descending.
TIER_ICX_TRAINVAL = "icx-trainval"
TIER_UNLABELLED = "imagecas-unlabelled"
TIER_NEW_DATASET = "new-dataset"
TIER_ICX_TEST = "icx-test"

#: Default priority per tier. Gaps of 100 leave room for an admin to slot a
#: batch in between without renumbering anything.
DEFAULT_PRIORITIES = {
    TIER_ICX_TRAINVAL: 400,
    TIER_UNLABELLED: 300,
    TIER_NEW_DATASET: 200,
    TIER_ICX_TEST: 100,
}

#: Reads wanted per tier (D11, D17). ImageCAS-X cases get one, plus the blind
#: duplicates chosen by ``choose_duplicates``.
DEFAULT_REPLICAS = {
    TIER_ICX_TRAINVAL: 1,
    TIER_UNLABELLED: 2,
    TIER_NEW_DATASET: 2,
    TIER_ICX_TEST: 1,
}

#: Fraction of ImageCAS-X cases served to a second annotator (D11: ~10 %).
DEFAULT_DUPLICATE_FRACTION = 0.10

#: Dataset tag for cases made from the live SegQueue's ImageCAS cases.
DATASET_IMAGECAS = "imagecas"

#: Assignment / submission kinds. Server-side only, never shown to annotators.
KIND_REFERENCE = "reference"   # the case has an ImageCAS-X reference
KIND_PAIRED = "paired"         # a two-read case without a reference
KIND_NORMAL = "normal"


def tier_for_split(split: Optional[str]) -> str:
    """The serve tier of an ImageCAS case, from its ImageCAS-X split (D14, D16)."""
    if split in (TRAIN, VAL):
        return TIER_ICX_TRAINVAL
    if split == TEST:
        return TIER_ICX_TEST
    return TIER_UNLABELLED


def duplicate_rank(name: str, seed: str = "segqueue14") -> int:
    """A stable pseudo-random rank for a case name; lower ranks are duplicated."""
    return int(hashlib.sha256(f"{seed}:{name}".encode()).hexdigest()[:12], 16)


def choose_duplicates(names_by_group: Mapping[str, Sequence[str]],
                      fraction: float = DEFAULT_DUPLICATE_FRACTION,
                      seed: str = "segqueue14") -> set:
    """Pick ``round(fraction * n)`` names from each group, deterministically.

    Per group (one per ImageCAS-X split) rather than overall, so each split gets
    its share -- 56 of the 560 train, 8 of the 80 val, 16 of the 160 test at the
    default 10 %. Deterministic in the names and the seed, so a re-run of the
    population tool picks the same cases.
    """
    if not 0.0 <= fraction <= 1.0:
        raise ValueError(f"duplicate fraction must be in [0, 1], got {fraction!r}")
    chosen = set()
    for _group, names in sorted(names_by_group.items()):
        ordered = sorted(set(names), key=lambda n: (duplicate_rank(n, seed), n))
        k = int(round(fraction * len(ordered)))
        chosen.update(ordered[:k])
    return chosen


@dataclass
class CasePlan:
    """Everything the population tool writes onto one SegQueue14 case."""

    name: str
    tier: str
    priority: int
    replicas: int
    dataset: str = DATASET_IMAGECAS
    split: Optional[str] = None
    blind_duplicate: bool = False
    has_reference: bool = False
    notes: List[str] = field(default_factory=list)

    @property
    def kind(self) -> str:
        if self.has_reference:
            return KIND_REFERENCE
        if self.replicas >= 2:
            return KIND_PAIRED
        return KIND_NORMAL


def plan_imagecas_cases(names: Iterable[str], splits: Mapping[int, str],
                        reference_names: Iterable[str] = (),
                        duplicate_fraction: float = DEFAULT_DUPLICATE_FRACTION,
                        priorities: Optional[Mapping[str, int]] = None,
                        seed: str = "segqueue14") -> Tuple[List[CasePlan], List[str]]:
    """Plan the SegQueue14 cases made from the live SegQueue's ImageCAS cases.

    Returns ``(plans, problems)``. ``plans`` is in serve order (tier, then name),
    which is also the order the cases should be created in so that ties within a
    tier break by name. ``problems`` are cases that were left out, each with the
    reason -- the caller prints them and a dry run shows them before anything is
    written.

    A case with an ImageCAS-X reference but no known split is a problem, not a
    guess: putting it in train/val by default could serve a held-out test case
    first, which is the one thing D16 rules out.
    """
    prio = dict(DEFAULT_PRIORITIES)
    prio.update(priorities or {})
    refs = set(reference_names)

    plans: List[CasePlan] = []
    problems: List[str] = []
    for name in sorted(set(names)):
        n = imagecas_id(name)
        if n is None:
            problems.append(f"{name}: not an imagecas_NNNN case name; skipped "
                            "(add non-ImageCAS cases with --extra-folder)")
            continue
        split = splits.get(n)
        has_ref = name in refs
        if split in (TRAIN, VAL, TEST) and not has_ref:
            problems.append(f"{name}: ImageCAS-X lists it as {split} but there is no "
                            "reference segmentation for it; skipped")
            continue
        if has_ref and split not in (TRAIN, VAL, TEST):
            problems.append(f"{name}: has an ImageCAS-X reference but no train/val/test "
                            "split; skipped rather than guessing its place in the queue")
            continue
        tier = tier_for_split(split)
        plans.append(CasePlan(
            name=name, tier=tier, priority=int(prio[tier]),
            replicas=DEFAULT_REPLICAS[tier], dataset=DATASET_IMAGECAS,
            split=split if split in (TRAIN, VAL, TEST) else EXCLUDE,
            has_reference=has_ref))

    groups: Dict[str, List[str]] = {}
    for plan in plans:
        if plan.has_reference:
            groups.setdefault(plan.split or "", []).append(plan.name)
    duplicates = choose_duplicates(groups, duplicate_fraction, seed)
    for plan in plans:
        if plan.name in duplicates:
            plan.blind_duplicate = True
            plan.replicas = 2
    plans.sort(key=lambda p: (-p.priority, p.name))
    return plans, problems


def plan_new_dataset_case(name: str, dataset: str, priority: Optional[int] = None,
                          replicas: Optional[int] = None) -> CasePlan:
    """A case from another CCTA dataset (D17): two reads, tagged, no reference."""
    if not dataset or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$", dataset):
        raise ValueError(f"dataset tag {dataset!r} must be a short identifier")
    return CasePlan(
        name=name, tier=TIER_NEW_DATASET,
        priority=int(DEFAULT_PRIORITIES[TIER_NEW_DATASET] if priority is None else priority),
        replicas=int(DEFAULT_REPLICAS[TIER_NEW_DATASET] if replicas is None else replicas),
        dataset=dataset, split=None, has_reference=False)


def new_case_name(dataset: str, item_name: str) -> str:
    """``<dataset>_<stem>``, safe for a folder name in an export."""
    stem = _folder_safe(strip_volume_suffix(item_name))
    if stem.startswith(dataset + "_"):
        return stem
    return f"{dataset}_{stem}"


# ----------------------------------------------------- the pooled new data

#: Suffix the seed masks carry next to their CT's name (D23):
#: ``<CT name without extension>__totalseg-coronary.nii.gz``.
SEED_SUFFIX = "__totalseg-coronary"
#: What a pooled case's seed is, recorded on the case.
SEED_SOURCE_TOTALSEG = "TotalSegmentator 2.18.0 coronary_arteries (binary)"


def read_include_list(text: str) -> List[str]:
    """Volume names from a pool list, in order: one per line, ``#`` comments and
    blank lines ignored, duplicates dropped (first kept)."""
    names, seen = [], set()
    for line in text.splitlines():
        name = line.split("#", 1)[0].strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names


def pool_case_name(item_name: str) -> str:
    """A pooled volume's case name: its item name without the extension.

    The pool's item names are already ``<Source>__<Case>[__<Part>]`` (D22), so
    they are kept as they are, made safe for a folder name in an export.
    """
    return _folder_safe(strip_volume_suffix(item_name))


def _folder_safe(stem: str) -> str:
    """``stem`` with every run of unsafe characters as ``_``, trimmed; else ``case``."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._-") or "case"


def pool_dataset(item_name: str, meta: Optional[dict] = None) -> str:
    """The dataset tag of a pooled volume: its ``source`` metadata, else the part
    of its name before the first ``__``."""
    source = str((meta or {}).get("source") or "").strip()
    if not source:
        stem = strip_volume_suffix(item_name)
        source = stem.split("__", 1)[0] if "__" in stem else ""
    tag = re.sub(r"[^A-Za-z0-9_.-]+", "-", source).strip("._-")
    return tag or "pool"


def seed_name_for(item_name: str) -> str:
    """The seed mask item name that belongs to a pooled CT item name."""
    return strip_volume_suffix(item_name) + SEED_SUFFIX + ".nii.gz"


def plan_pool_case(item_name: str, meta: Optional[dict] = None,
                   priority: Optional[int] = None,
                   replicas: Optional[int] = None) -> CasePlan:
    """A volume from the pooled new datasets (D23): no reference, so two reads
    (D11, as for every unlabelled case); its dataset from its own name."""
    return plan_new_dataset_case(pool_case_name(item_name), pool_dataset(item_name, meta),
                                 priority=priority, replicas=replicas)


# ---------------------------------------------------------- prelabel rules

ATTACH = "attach"
REFRESH = "refresh"
SKIP = "skip"


@dataclass(frozen=True)
class PrelabelDecision:
    """What ``prelabel_decision`` says to do (``ATTACH``/``REFRESH``/``SKIP``), and why."""

    action: str
    reason: str = ""


def prelabel_decision(case: Mapping, version: str, submissions: int = 0,
                      working_assignments: int = 0,
                      include_test: bool = False) -> PrelabelDecision:
    """Whether a prelabel of ``version`` may be put on ``case``.

    * no prelabel yet -> attach;
    * the same version -> skip (idempotent);
    * a different version -> refresh (D15), but only if nobody has submitted the
      case, nobody is working from the old prelabel right now, and the case is
      not a held-out ImageCAS-X test case (D16) unless ``include_test``.

    ``working_assignments`` counts assignments that have downloaded the case and
    not finished it -- an annotator mid-correction keeps the prelabel they
    started from.
    """
    if not version or not str(version).strip():
        return PrelabelDecision(SKIP, "no model version given")
    current = case.get("prelabelVersion") or ""
    if not case.get("prelabelFileId"):
        return PrelabelDecision(ATTACH, "no prelabel yet")
    if current == version:
        return PrelabelDecision(SKIP, f"already has {version}")
    if submissions > 0:
        return PrelabelDecision(SKIP, f"has {submissions} submission(s); keeps {current}")
    if working_assignments > 0:
        return PrelabelDecision(SKIP, "an annotator is working from the current "
                                      f"prelabel ({current})")
    if case.get("tier") == TIER_ICX_TEST and not include_test:
        return PrelabelDecision(SKIP, "held-out ImageCAS-X test case (D16); keeps "
                                      f"{current}")
    return PrelabelDecision(REFRESH, f"{current} -> {version}")


def validate_model_version(version: str) -> str:
    """A model version is a folder name under prelabels/: keep it tame."""
    version = (version or "").strip()
    if not re.match(r"^[A-Za-z0-9][A-Za-z0-9_.+-]{0,63}$", version):
        raise ValueError(
            f"model version {version!r} must be 1-64 characters of letters, digits "
            "and ._+- (it becomes a folder name)")
    return version
