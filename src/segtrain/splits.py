"""Train/val/test splits derived from the dataset's own meta.csv.

The dataset ships an official ``split`` column (1082 train / 57 val / 89 test).
Honouring it matters: it is what makes our numbers comparable to published
TotalSegmentator results, and it keeps the 89 test cases out of every training
and model-selection decision. Those 89 never enter ``imagesTr`` at all, so there
is no path by which nnU-Net can peek at them.

Two schemes are offered:

``official`` (default)
    One fold, exactly the published split. This is what Stage 1 and Stage 2 use.
    splits_final.json contains a single entry, which nnU-Net accepts.

``cv5``
    Standard 5-fold cross-validation over the 1139 non-test cases, stratified by
    study type. Use only when you actually intend to train five models and
    ensemble; it discards the official train/val boundary, so results are no
    longer directly comparable to the published split.
"""

from __future__ import annotations

import csv
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from random import Random
from typing import Iterable, Optional

SPLIT_TRAIN = "train"
SPLIT_VAL = "val"
SPLIT_TEST = "test"

# Sizes published with TotalSegmentator v2.0.1. Asserted on load so a truncated
# or wrong-version meta.csv fails immediately rather than after preprocessing.
EXPECTED_COUNTS = {SPLIT_TRAIN: 1082, SPLIT_VAL: 57, SPLIT_TEST: 89}


class SplitError(RuntimeError):
    pass


@dataclass(frozen=True)
class CaseMeta:
    """One row of meta.csv, narrowed to the fields the pipeline uses."""

    case_id: str
    split: str
    study_type: str
    institute: str = ""
    manufacturer: str = ""

    @property
    def is_test(self) -> bool:
        return self.split == SPLIT_TEST


def read_meta(meta_csv: Path) -> list[CaseMeta]:
    """Parse meta.csv.

    Two file-format quirks are handled here rather than at every call site: the
    file is semicolon-delimited, and it carries a UTF-8 BOM which makes the first
    column come back as '\\ufeffimage_id' under a plain utf-8 read.
    """
    path = Path(meta_csv)
    if not path.is_file():
        raise SplitError(f"meta.csv not found: {path}")

    with open(path, newline="", encoding="utf-8-sig") as fh:
        reader = csv.DictReader(fh, delimiter=";")
        if reader.fieldnames is None or "image_id" not in reader.fieldnames:
            raise SplitError(
                f"{path}: expected a ';'-delimited CSV with an 'image_id' column, "
                f"got columns {reader.fieldnames}"
            )
        rows = [
            CaseMeta(
                case_id=r["image_id"].strip(),
                split=(r.get("split") or "").strip(),
                study_type=(r.get("study_type") or "unknown").strip(),
                institute=(r.get("institute") or "").strip(),
                manufacturer=(r.get("manufacturer") or "").strip(),
            )
            for r in reader
            if (r.get("image_id") or "").strip()
        ]

    if not rows:
        raise SplitError(f"{path}: no data rows")

    ids = [r.case_id for r in rows]
    if len(set(ids)) != len(ids):
        dupes = sorted({i for i in ids if ids.count(i) > 1})
        raise SplitError(f"{path}: duplicate image_id values: {dupes[:5]}")

    unknown = sorted({r.split for r in rows} - set(EXPECTED_COUNTS))
    if unknown:
        raise SplitError(f"{path}: unexpected split values {unknown}")

    return rows


def check_expected_counts(rows: Iterable[CaseMeta], strict: bool = False) -> dict[str, int]:
    """Compare observed split sizes against the published ones.

    Non-strict by default so a deliberately subsetted dataset still works; strict
    is used by the test suite against the real dataset.
    """
    counts: dict[str, int] = defaultdict(int)
    for r in rows:
        counts[r.split] += 1
    counts = dict(counts)
    if strict and counts != EXPECTED_COUNTS:
        raise SplitError(f"split sizes {counts} do not match published {EXPECTED_COUNTS}")
    return counts


def select(rows: Iterable[CaseMeta], split: str) -> list[str]:
    """Case ids belonging to one split, in meta.csv order."""
    return [r.case_id for r in rows if r.split == split]


def training_pool(rows: Iterable[CaseMeta]) -> list[str]:
    """Every non-test case: what goes into imagesTr."""
    return [r.case_id for r in rows if r.split != SPLIT_TEST]


def _stratified_folds(rows: list[CaseMeta], n_folds: int, seed: int) -> list[list[str]]:
    """Partition into n_folds validation blocks, balanced by study type.

    Study type varies enormously across this dataset -- 'ct angiography head'
    covers a completely different anatomy than 'ct thorax-abdomen-pelvis'. A
    naive random split can concentrate a rare type in one fold and make that
    fold's metrics meaningless. Dealing each type's cases round-robin keeps every
    fold proportionally representative.
    """
    rng = Random(seed)
    by_type: dict[str, list[str]] = defaultdict(list)
    for r in rows:
        by_type[r.study_type].append(r.case_id)

    blocks: list[list[str]] = [[] for _ in range(n_folds)]
    # Deal the largest strata first, and offset each stratum's starting fold so
    # small strata (some have fewer members than there are folds) don't all pile
    # into fold 0.
    cursor = 0
    for study_type in sorted(by_type, key=lambda t: (-len(by_type[t]), t)):
        members = sorted(by_type[study_type])
        rng.shuffle(members)
        for case_id in members:
            blocks[cursor % n_folds].append(case_id)
            cursor += 1

    return [sorted(b) for b in blocks]


def build_splits(
    rows: list[CaseMeta],
    scheme: str = "official",
    n_folds: int = 5,
    seed: int = 12345,
) -> list[dict[str, list[str]]]:
    """Build the nnU-Net splits_final.json structure."""
    pool = set(training_pool(rows))
    if not pool:
        raise SplitError("no non-test cases available")

    if scheme == "official":
        val = [c for c in select(rows, SPLIT_VAL) if c in pool]
        if not val:
            raise SplitError(
                "meta.csv contains no 'val' cases; use --scheme cv5 to generate folds instead"
            )
        train = sorted(pool - set(val))
        return [{"train": train, "val": sorted(val)}]

    if scheme == "cv5":
        pool_rows = [r for r in rows if r.case_id in pool]
        blocks = _stratified_folds(pool_rows, n_folds, seed)
        splits = []
        for i in range(n_folds):
            val = blocks[i]
            train = sorted(pool - set(val))
            splits.append({"train": train, "val": sorted(val)})
        return splits

    raise SplitError(f"unknown scheme {scheme!r}; expected 'official' or 'cv5'")


def validate_splits(splits: list[dict[str, list[str]]], test_ids: Iterable[str]) -> None:
    """Fail loudly on leakage. Cheap here, invisible and fatal later."""
    test = set(test_ids)
    for i, fold in enumerate(splits):
        train, val = set(fold["train"]), set(fold["val"])
        overlap = train & val
        if overlap:
            raise SplitError(f"fold {i}: {len(overlap)} cases in both train and val: "
                             f"{sorted(overlap)[:5]}")
        leaked = (train | val) & test
        if leaked:
            raise SplitError(f"fold {i}: test cases leaked into training pool: "
                             f"{sorted(leaked)[:5]}")
        if not val:
            raise SplitError(f"fold {i}: empty validation set")


def write_splits_final(path: Path, splits: list[dict[str, list[str]]]) -> Path:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(splits, fh, indent=2)
        fh.write("\n")
    return path


def summarize(rows: list[CaseMeta], splits: list[dict[str, list[str]]]) -> str:
    counts = check_expected_counts(rows)
    lines = [
        f"meta.csv: {sum(counts.values())} cases "
        f"({counts.get(SPLIT_TRAIN, 0)} train / {counts.get(SPLIT_VAL, 0)} val / "
        f"{counts.get(SPLIT_TEST, 0)} test)",
        f"held out of imagesTr entirely: {counts.get(SPLIT_TEST, 0)} test cases",
        f"folds written: {len(splits)}",
    ]
    for i, fold in enumerate(splits):
        lines.append(f"  fold {i}: {len(fold['train'])} train / {len(fold['val'])} val")
    return "\n".join(lines)


def load_splits(path: Path) -> list[dict[str, list[str]]]:
    with open(Path(path), encoding="utf-8") as fh:
        return json.load(fh)


def resolve_preview_cases(
    rows: list[CaseMeta],
    requested: Iterable[str],
    splits: Optional[list[dict[str, list[str]]]] = None,
    fold: int = 0,
) -> list[str]:
    """Check that requested preview cases are genuinely held out for this fold.

    A preview rendered on a training case looks great and means nothing. This is
    easy to get wrong by hand, so it is checked rather than trusted.
    """
    known = {r.case_id for r in rows}
    val_ids = set(splits[fold]["val"]) if splits and fold < len(splits) else None

    resolved = []
    for case_id in requested:
        if case_id not in known:
            raise SplitError(f"preview case {case_id!r} is not in meta.csv")
        if val_ids is not None and case_id not in val_ids:
            raise SplitError(
                f"preview case {case_id!r} is not in fold {fold}'s validation set; "
                "previews must use held-out cases"
            )
        resolved.append(case_id)
    return resolved
