"""Label sets and task configs -- the invariants a trained model depends on."""

import pytest

from segtrain.config import (
    ConfigError,
    LabelSet,
    list_tasks,
    load_label_set,
    load_task,
)

@pytest.mark.parametrize("name", ["placeholder"])
def test_label_indices_are_contiguous_from_one(name):
    labels = load_label_set(name)
    assert sorted(labels.labels.values()) == list(range(1, labels.n_classes + 1))
    assert 0 not in labels.labels.values(), "0 is reserved for background"


def test_names_are_in_label_order():
    labels = LabelSet("t", {"a": 1, "b": 2, "c": 3})
    assert [labels.index_of(n) for n in labels.names] == list(range(1, labels.n_classes + 1))


def test_nnunet_labels_include_background():
    block = LabelSet("t", {"a": 1, "b": 2}).to_nnunet_labels()
    assert block["background"] == 0
    assert len(block) == 3


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
    assert names
    for name in names:
        load_task(name)


@pytest.mark.parametrize("ref", [710, "710", "Coronary", "Dataset710_Coronary"])
def test_task_lookup_accepts_several_forms(ref):
    assert load_task(ref).dataset_id == 710


def test_dataset_ids_are_unique():
    ids = [load_task(n).dataset_id for n in list_tasks()]
    assert len(set(ids)) == len(ids)


def test_nnunet_name_is_zero_padded():
    assert load_task(710).nnunet_name == "Dataset710_Coronary"


def test_label_set_name_lookup_round_trips():
    labels = LabelSet("t", {"a": 1, "b": 2})
    assert labels.name_of(2) == "b"
    with pytest.raises(KeyError):
        labels.name_of(9)


def test_source_values_remap_a_single_file_dataset(tmp_path):
    """Data labelled as one integer volume rarely uses our indices."""
    (tmp_path / "s.yaml").write_text(
        "name: s\n"
        "labels:\n  left_main: 1\n  right_coronary_artery: 2\n"
        "source_values:\n  left_main: 7\n  right_coronary_artery: 3\n",
        encoding="utf-8")
    labels = load_label_set("s", labels_dir=tmp_path)
    assert labels.source_to_index() == {7: 1, 3: 2}


def test_source_values_default_to_identity():
    assert LabelSet("t", {"a": 1, "b": 2, "c": 3}).source_to_index() == {1: 1, 2: 2, 3: 3}


def test_source_values_reject_a_duplicated_value(tmp_path):
    """Two structures reading one value means one can never be produced."""
    (tmp_path / "s.yaml").write_text(
        "name: s\nlabels:\n  a: 1\n  b: 2\n"
        "source_values:\n  a: 5\n  b: 5\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="claimed by both"):
        load_label_set("s", labels_dir=tmp_path)


def test_source_values_reject_background(tmp_path):
    (tmp_path / "s.yaml").write_text(
        "name: s\nlabels:\n  a: 1\n"
        "source_values:\n  a: 0\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="background"):
        load_label_set("s", labels_dir=tmp_path)


def test_source_values_reject_unknown_structures(tmp_path):
    (tmp_path / "s.yaml").write_text(
        "name: s\nlabels:\n  a: 1\n"
        "source_values:\n  typo: 1\n", encoding="utf-8")
    with pytest.raises(ConfigError, match="not in 'labels'"):
        load_label_set("s", labels_dir=tmp_path)


def test_spacing_accepts_native(tmp_path):
    (tmp_path / "Dataset800_N.yaml").write_text(
        "dataset_id: 800\ndataset_name: N\nlabel_set: placeholder\nspacing: native\n",
        encoding="utf-8")
    task = load_task(800, tasks_dir=tmp_path)
    assert task.spacing is None
    assert task.spacing_label == "native"


def test_spacing_rejects_a_malformed_value(tmp_path):
    (tmp_path / "Dataset800_N.yaml").write_text(
        "dataset_id: 800\ndataset_name: N\nlabel_set: placeholder\nspacing: 0.4\n",
        encoding="utf-8")
    with pytest.raises(ConfigError, match="3 numbers or 'native'"):
        load_task(800, tasks_dir=tmp_path)


def _floor_task(tmp_path, floor=None):
    body = ("dataset_id: 800\ndataset_name: N\n"
            "label_set: placeholder\nspacing: native\n")
    if floor is not None:
        body += f"max_spacing_mm: {floor}\n"
    (tmp_path / "Dataset800_N.yaml").write_text(body, encoding="utf-8")
    return load_task(800, tasks_dir=tmp_path)


def test_spacing_warning_fires_when_the_plan_is_too_coarse(tmp_path):
    from segtrain.plans import spacing_warnings

    task = _floor_task(tmp_path, floor=0.5)
    assert spacing_warnings(task, [0.4, 0.35, 0.35]) == []
    assert spacing_warnings(task, [1.0, 0.35, 0.35]), "1 mm must be flagged"
    assert "coarser" in spacing_warnings(task, [1.0, 0.35, 0.35])[0]


def test_spacing_warning_is_silent_without_a_declared_floor(tmp_path):
    from segtrain.plans import spacing_warnings

    assert spacing_warnings(_floor_task(tmp_path), [9.0, 9.0, 9.0]) == []
