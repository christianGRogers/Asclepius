"""The event stream -- the only interface between the trainer and Slicer."""

import json

from segtrain.events import EventReader, EventWriter, RunState, read_run


def test_round_trip(tmp_path):
    with EventWriter(tmp_path) as w:
        w.run_start(task="T", epochs=10, class_names=["liver", "spleen"])
        w.epoch(0, train_loss=-0.2, val_loss=-0.3, pseudo_dice=[0.4, 0.5],
                lr=0.01, epoch_seconds=12.0)
        w.checkpoint(0, "checkpoint_best.pth", kind="best")
        w.preview(0, "s0001", "previews/ep0000_s0001.nii.gz", dice={"liver": 0.8})
        w.run_end(status="completed")

    state = read_run(tmp_path)
    assert state.meta["class_names"] == ["liver", "spleen"]
    assert state.total_epochs == 10
    assert state.current_epoch == 0
    assert len(state.checkpoints) == 1
    assert state.latest_preview["case"] == "s0001"
    assert state.finished and state.status == "completed"


def test_reader_is_incremental(tmp_path):
    w = EventWriter(tmp_path)
    reader = EventReader(tmp_path)
    w.run_start(task="T", epochs=3)
    assert len(reader.read_new()) == 1
    assert reader.read_new() == []
    w.epoch(0, train_loss=1.0)
    w.epoch(1, train_loss=0.5)
    assert len(reader.read_new()) == 2
    assert reader.read_new() == []
    w.close()


def test_reader_survives_a_partial_line(tmp_path):
    """A monitor can poll while an event is half-written."""
    path = tmp_path / "events.jsonl"
    path.write_text('{"t":1,"event":"epoch","epoch":0}\n{"t":2,"eve', encoding="utf-8")
    reader = EventReader(tmp_path)
    assert len(reader.read_new()) == 1

    with open(path, "a", encoding="utf-8") as fh:
        fh.write('nt":"epoch","epoch":1}\n')
    events = reader.read_new()
    assert len(events) == 1 and events[0]["epoch"] == 1


def test_reader_skips_a_corrupt_line(tmp_path):
    (tmp_path / "events.jsonl").write_text(
        '{"t":1,"event":"epoch","epoch":0}\nnot json at all\n'
        '{"t":2,"event":"epoch","epoch":1}\n', encoding="utf-8")
    assert len(EventReader(tmp_path).read_new()) == 2


def test_reader_restarts_when_the_log_is_truncated(tmp_path):
    w = EventWriter(tmp_path)
    w.epoch(0, train_loss=1.0)
    w.epoch(1, train_loss=0.9)
    w.close()
    reader = EventReader(tmp_path)
    assert len(reader.read_new()) == 2

    # A restarted run truncates and begins again; the reader must not keep
    # reading from a now-meaningless offset.
    (tmp_path / "events.jsonl").write_text(
        '{"t":9,"event":"epoch","epoch":0}\n', encoding="utf-8")
    assert len(reader.read_new()) == 1


def test_missing_file_is_not_an_error(tmp_path):
    assert EventReader(tmp_path / "nope").read_new() == []


def test_non_finite_values_become_null(tmp_path):
    """JSON has no NaN or Infinity; emitting them yields a file strict parsers reject."""
    w = EventWriter(tmp_path)
    w.epoch(0, train_loss=float("nan"), val_loss=float("inf"), lr=float("-inf"))
    w.close()
    raw = (tmp_path / "events.jsonl").read_text(encoding="utf-8")
    assert "NaN" not in raw and "Infinity" not in raw
    record = json.loads(raw.strip())
    assert record["train_loss"] is None and record["val_loss"] is None


def test_numpy_scalars_are_serialisable(tmp_path):
    np = __import__("numpy")
    w = EventWriter(tmp_path)
    w.epoch(np.int64(3), train_loss=np.float32(0.5), pseudo_dice=list(np.array([0.1, 0.2])))
    w.close()
    state = read_run(tmp_path)
    assert state.epochs[0]["epoch"] == 3


def test_unknown_event_kinds_are_ignored():
    """Older Slicer modules must not break when a new event type is added."""
    state = RunState().update([{"t": 1, "event": "something_new", "x": 1}])
    assert state.epochs == [] and state.status is None


def test_series_skips_gaps_rather_than_zero_filling(tmp_path):
    w = EventWriter(tmp_path)
    w.epoch(0, train_loss=1.0)
    w.epoch(1, train_loss=None)
    w.epoch(2, train_loss=0.5)
    w.close()
    xs, ys = read_run(tmp_path).series("train_loss")
    assert xs == [0, 2] and ys == [1.0, 0.5]


def test_eta_uses_recent_epoch_durations(tmp_path):
    w = EventWriter(tmp_path)
    w.run_start(task="T", epochs=10)
    for i in range(3):
        w.epoch(i, epoch_seconds=100.0)
    w.close()
    # Epoch indices are 0-based, so a last event of epoch=2 means 3 of the 10
    # epochs are done and 7 remain -> 700 s at 100 s each.
    assert abs(read_run(tmp_path).eta_seconds() - 700.0) < 1.0


def test_preview_helpers(tmp_path):
    w = EventWriter(tmp_path)
    w.preview(0, "a", "previews/a0.nii.gz", dice={"liver": 0.5})
    w.preview(0, "b", "previews/b0.nii.gz", dice={"liver": 0.6})
    w.preview(1, "a", "previews/a1.nii.gz", dice={"liver": 0.7})
    w.close()
    state = read_run(tmp_path)
    assert state.preview_cases() == ["a", "b"]
    assert len(state.previews_for("a")) == 2
    assert state.previews_for("a")[-1]["epoch"] == 1


def test_previews_directory_is_created(tmp_path):
    EventWriter(tmp_path).close()
    assert (tmp_path / "previews").is_dir()
