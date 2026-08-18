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

# Phase 1. Hand-written rather than generated, because TotalSegmentator -- the
# source every other label set is derived from -- has no coronary structures.
CORONARY = ["coronary", "coronary_ext"]
CORONARY_SIZES = {"coronary": 4, "coronary_ext": 6}


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


@pytest.mark.parametrize("group", GROUPS + CORONARY + ["all117"])
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


@pytest.mark.parametrize("ref", [710, "710", "Coronary", "Dataset710_Coronary"])
def test_task_lookup_accepts_several_forms(ref):
    assert load_task(ref).dataset_id == 710


def test_no_low_resolution_task_exists():
    """The project trains high-resolution models only.

    A coronary artery is 1.5-4 mm across, so anything coarser than about 1 mm
    describes the vessel with fewer voxels than it has dimensions. A downsampled
    overview model would be trained to predict sub-voxel structures.
    """
    for name in list_tasks():
        task = load_task(name)
        if task.spacing is None:
            continue
        assert max(task.spacing) <= 1.5, f"{name} is coarser than 1.5 mm"


def test_coronary_is_the_phase1_task_and_runs_at_native_spacing():
    task = load_task(710)
    assert task.spacing is None, "phase 1 must not override nnU-Net's target spacing"
    assert task.configuration == "3d_fullres"
    assert task.label_set.name == "coronary"


def test_phase2_region_tasks_are_at_native_resolution():
    for name in list_tasks():
        task = load_task(name)
        if task.dataset_id == 710:
            continue
        assert task.spacing == (1.5, 1.5, 1.5), name


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


# ------------------------------------------------------------------- coronary


@pytest.mark.parametrize("name", CORONARY)
def test_coronary_set_sizes(name):
    assert load_label_set(name).n_classes == CORONARY_SIZES[name]


def test_coronary_ext_extends_coronary_without_renumbering():
    """The extended set must share a channel prefix with the base set.

    If `coronary_ext` reordered or renumbered the four main branches, a model
    trained on one vocabulary would keep loading happily against the other and
    predict the wrong vessel for every voxel -- with nothing to detect it.
    """
    base = load_label_set("coronary").labels
    ext = load_label_set("coronary_ext").labels
    for structure, index in base.items():
        assert ext[structure] == index, structure
    assert set(base) < set(ext)


def test_coronary_has_no_totalsegmentator_structures():
    """The two label vocabularies are disjoint, and must stay that way.

    A name appearing in both would be ambiguous the moment a phase 2 region
    model and the coronary model are ensembled.
    """
    coronary = set(load_label_set("coronary_ext").labels)
    assert not (coronary & set(load_label_set("all117").labels))


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
    assert load_label_set("coronary").source_to_index() == {1: 1, 2: 2, 3: 3, 4: 4}


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
        "dataset_id: 800\ndataset_name: N\nlabel_set: coronary\nspacing: native\n",
        encoding="utf-8")
    task = load_task(800, tasks_dir=tmp_path)
    assert task.spacing is None
    assert task.spacing_label == "native"


def test_spacing_rejects_a_malformed_value(tmp_path):
    (tmp_path / "Dataset800_N.yaml").write_text(
        "dataset_id: 800\ndataset_name: N\nlabel_set: coronary\nspacing: 0.4\n",
        encoding="utf-8")
    with pytest.raises(ConfigError, match="3 numbers or 'native'"):
        load_task(800, tasks_dir=tmp_path)


def test_coronary_task_sets_a_spacing_floor():
    """`spacing: native` needs a floor, or a thick-slice case can coarsen it."""
    assert load_task(710).max_spacing_mm == 0.5


def test_spacing_warning_fires_when_the_plan_is_too_coarse():
    from segtrain.plans import spacing_warnings

    task = load_task(710)
    assert spacing_warnings(task, [0.4, 0.35, 0.35]) == []
    assert spacing_warnings(task, [1.0, 0.35, 0.35]), "1 mm must be flagged"
    assert "coarser" in spacing_warnings(task, [1.0, 0.35, 0.35])[0]


def test_spacing_warning_is_silent_without_a_declared_floor():
    from segtrain.plans import spacing_warnings

    assert spacing_warnings(load_task(702), [9.0, 9.0, 9.0]) == []
