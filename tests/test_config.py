"""Label sets and task configs -- the invariants a trained model depends on."""

import pytest

from segtrain.config import (
    ConfigError,
    LabelSet,
    list_tasks,
    load_label_set,
    load_task,
)

GROUPS = ["organs", "vertebrae", "cardiac", "muscles", "bones"]
EXPECTED_SIZES = {"organs": 26, "vertebrae": 25, "cardiac": 18, "muscles": 10, "bones": 38}


def test_all117_has_117_structures():
    assert load_label_set("all117").n_classes == 117


@pytest.mark.parametrize("group", GROUPS)
def test_group_sizes(group):
    assert load_label_set(group).n_classes == EXPECTED_SIZES[group]


def test_groups_partition_all117_exactly():
    """No structure may be missing from, or duplicated across, the group models.

    A structure in two groups would be predicted twice by the final ensemble; one
    in none would silently never be learned. Both are invisible until evaluation.
    """
    everything = set(load_label_set("all117").labels)
    seen = set()
    for group in GROUPS:
        members = set(load_label_set(group).labels)
        assert not (seen & members), f"structures in two groups: {seen & members}"
        seen |= members
    assert seen == everything, f"not partitioned: {seen ^ everything}"


@pytest.mark.parametrize("group", GROUPS + ["all117"])
def test_label_indices_are_contiguous_from_one(group):
    labels = load_label_set(group)
    assert sorted(labels.labels.values()) == list(range(1, labels.n_classes + 1))
    assert 0 not in labels.labels.values(), "0 is reserved for background"


def test_names_are_in_label_order():
    labels = load_label_set("organs")
    assert [labels.index_of(n) for n in labels.names] == list(range(1, labels.n_classes + 1))


def test_nnunet_labels_include_background():
    block = load_label_set("muscles").to_nnunet_labels()
    assert block["background"] == 0
    assert len(block) == 11


def test_rejects_non_contiguous_indices(tmp_path):
    (tmp_path / "broken.yaml").write_text(
        "name: broken\nlabels:\n  a: 1\n  b: 3\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="contiguous"):
        load_label_set("broken", labels_dir=tmp_path)


def test_rejects_count_mismatch(tmp_path):
    (tmp_path / "broken.yaml").write_text(
        "name: broken\ncount: 5\nlabels:\n  a: 1\n  b: 2\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="declared count"):
        load_label_set("broken", labels_dir=tmp_path)


def test_unknown_label_set_lists_alternatives():
    with pytest.raises(ConfigError, match="available"):
        load_label_set("no_such_group")


def test_all_tasks_load():
    names = list_tasks()
    assert len(names) == 6
    for name in names:
        load_task(name)


@pytest.mark.parametrize("ref", [701, "701", "Total3mm", "Dataset701_Total3mm"])
def test_task_lookup_accepts_several_forms(ref):
    assert load_task(ref).dataset_id == 701


def test_stage1_is_the_only_3mm_task():
    at_3mm = [t for t in list_tasks() if load_task(t).spacing == (3.0, 3.0, 3.0)]
    assert at_3mm == ["Dataset701_Total3mm"]


def test_stage2_tasks_are_at_native_resolution():
    for name in list_tasks():
        task = load_task(name)
        if task.dataset_id == 701:
            continue
        assert task.spacing == (1.5, 1.5, 1.5), name


def test_dataset_ids_are_unique():
    ids = [load_task(n).dataset_id for n in list_tasks()]
    assert len(set(ids)) == len(ids)


def test_nnunet_name_is_zero_padded():
    assert load_task(701).nnunet_name == "Dataset701_Total3mm"


def test_label_set_name_lookup_round_trips():
    labels = LabelSet("t", {"a": 1, "b": 2})
    assert labels.name_of(2) == "b"
    with pytest.raises(KeyError):
        labels.name_of(9)
