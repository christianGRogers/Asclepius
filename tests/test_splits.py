"""Splits. The test set staying out of training is the point of the whole file."""

import pytest

from segtrain.splits import (
    EXPECTED_COUNTS,
    SPLIT_TEST,
    CaseMeta,
    SplitError,
    build_splits,
    check_expected_counts,
    read_meta,
    resolve_preview_cases,
    select,
    training_pool,
    validate_splits,
)


def _rows(n_train=20, n_val=5, n_test=8, types=("a", "b", "c")):
    rows = []
    for i in range(n_train):
        rows.append(CaseMeta("tr%03d" % i, "train", types[i % len(types)]))
    for i in range(n_val):
        rows.append(CaseMeta("va%03d" % i, "val", types[i % len(types)]))
    for i in range(n_test):
        rows.append(CaseMeta("te%03d" % i, "test", types[i % len(types)]))
    return rows


# -- synthetic ---------------------------------------------------------------


def test_official_scheme_makes_one_fold_matching_the_published_split():
    rows = _rows()
    splits = build_splits(rows, scheme="official")
    assert len(splits) == 1
    assert sorted(splits[0]["val"]) == sorted(select(rows, "val"))
    assert len(splits[0]["train"]) == 20


def test_test_cases_never_enter_any_fold():
    rows = _rows()
    for scheme in ("official", "cv5"):
        splits = build_splits(rows, scheme=scheme)
        validate_splits(splits, select(rows, SPLIT_TEST))
        for fold in splits:
            assert not set(fold["train"]) & set(select(rows, SPLIT_TEST))
            assert not set(fold["val"]) & set(select(rows, SPLIT_TEST))


def test_cv5_folds_cover_the_pool_exactly_once():
    rows = _rows(n_train=40, n_val=10)
    splits = build_splits(rows, scheme="cv5", n_folds=5)
    seen = []
    for fold in splits:
        seen.extend(fold["val"])
    assert sorted(seen) == sorted(training_pool(rows))
    assert len(seen) == len(set(seen)), "a case appeared in two validation folds"


def test_cv5_is_deterministic_for_a_seed():
    rows = _rows(n_train=40, n_val=10)
    assert build_splits(rows, "cv5", seed=7) == build_splits(rows, "cv5", seed=7)


def test_cv5_seed_changes_the_partition():
    rows = _rows(n_train=40, n_val=10)
    assert build_splits(rows, "cv5", seed=1) != build_splits(rows, "cv5", seed=2)


def test_cv5_balances_study_types_across_folds():
    """A rare study type concentrated in one fold makes that fold's metrics junk."""
    rows = _rows(n_train=50, n_val=0, n_test=0, types=("common", "common", "common", "rare"))
    splits = build_splits(rows, "cv5", n_folds=5)
    by_type = {r.case_id: r.study_type for r in rows}
    counts = [sum(1 for c in f["val"] if by_type[c] == "rare") for f in splits]
    assert max(counts) - min(counts) <= 1, counts


def test_validate_splits_catches_train_val_overlap():
    with pytest.raises(SplitError, match="both train and val"):
        validate_splits([{"train": ["a", "b"], "val": ["b"]}], [])


def test_validate_splits_catches_test_leakage():
    with pytest.raises(SplitError, match="leaked"):
        validate_splits([{"train": ["a", "te1"], "val": ["b"]}], ["te1"])


def test_validate_splits_catches_empty_validation():
    with pytest.raises(SplitError, match="empty validation"):
        validate_splits([{"train": ["a"], "val": []}], [])


def test_unknown_scheme_is_rejected():
    with pytest.raises(SplitError, match="unknown scheme"):
        build_splits(_rows(), scheme="bogus")


def test_preview_cases_must_be_held_out():
    rows = _rows()
    splits = build_splits(rows, scheme="official")
    resolve_preview_cases(rows, ["va000"], splits, fold=0)
    with pytest.raises(SplitError, match="not in fold 0"):
        resolve_preview_cases(rows, ["tr000"], splits, fold=0)
    with pytest.raises(SplitError, match="not in meta.csv"):
        resolve_preview_cases(rows, ["nope"], splits, fold=0)


# -- against the real dataset ------------------------------------------------


@pytest.mark.needs_data
def test_real_meta_csv_matches_published_counts(meta_rows):
    assert check_expected_counts(meta_rows, strict=True) == EXPECTED_COUNTS


@pytest.mark.needs_data
def test_real_meta_csv_parses_despite_bom(cfg):
    """meta.csv ships with a UTF-8 BOM; a plain utf-8 read mangles the first column."""
    rows = read_meta(cfg.meta_csv)
    assert rows[0].case_id and not rows[0].case_id.startswith("﻿")
    assert all(r.study_type for r in rows)


@pytest.mark.needs_data
def test_real_official_split_is_1082_57(meta_rows):
    splits = build_splits(meta_rows, scheme="official")
    assert len(splits[0]["train"]) == 1082
    assert len(splits[0]["val"]) == 57
    validate_splits(splits, select(meta_rows, SPLIT_TEST))


@pytest.mark.needs_data
def test_real_training_pool_excludes_all_89_test_cases(meta_rows):
    assert len(training_pool(meta_rows)) == 1139
    assert len(select(meta_rows, SPLIT_TEST)) == 89
