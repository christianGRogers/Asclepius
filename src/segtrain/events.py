"""Append-only JSONL event stream: the one interface between trainer and monitor.

The trainer never talks to Slicer. It appends newline-delimited JSON to
``<run_dir>/events.jsonl`` and writes preview segmentations next to it; the
Slicer module polls that file and reads whatever is new. Everything follows from
that choice:

* the same code path works for a local run, an SSH-mounted run and a SLURM job
* the monitor can attach late, detach, crash, or reconnect without the trainer
  noticing or caring
* the full history of a run survives as a plain file you can replay, diff, or
  hand to someone else -- which is also how the Slicer UI gets developed on a
  laptop with no GPU

**This module must stay importable from Slicer's Python 3.9 with stdlib only.**
No numpy, no torch, no yaml. The Slicer module imports it directly.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Iterator, Optional

EVENTS_FILENAME = "events.jsonl"
PREVIEWS_DIRNAME = "previews"

# Event kinds. Readers must ignore kinds they don't recognise so that adding a
# new one never breaks an older Slicer module.
RUN_START = "run_start"
EPOCH = "epoch"
CHECKPOINT = "checkpoint"
PREVIEW = "preview"
LOG = "log"
RUN_END = "run_end"


def _now() -> float:
    return time.time()


class EventWriter:
    """Appends events to a run's events.jsonl.

    Opened in append mode and flushed on every write. The flush matters: without
    it a monitor polling over SSH sees nothing for minutes at a time, which reads
    as a hung run.
    """

    def __init__(self, run_dir: Path, fsync: bool = False):
        self.run_dir = Path(run_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        (self.run_dir / PREVIEWS_DIRNAME).mkdir(exist_ok=True)
        self.path = self.run_dir / EVENTS_FILENAME
        # fsync is off by default: it is a real cost per epoch on network
        # storage, and a lost tail on a hard crash costs nothing we can't
        # recover from the checkpoint.
        self._fsync = fsync
        self._fh = open(self.path, "a", encoding="utf-8")

    def emit(self, event: str, **payload: Any) -> dict:
        record = {"t": _now(), "event": event}
        record.update(payload)
        line = json.dumps(record, default=_json_default, ensure_ascii=False)
        self._fh.write(line + "\n")
        self._fh.flush()
        if self._fsync:
            os.fsync(self._fh.fileno())
        return record

    # Convenience wrappers so call sites stay readable and field names stay
    # consistent across the trainer, the preview daemon and the Slicer reader.

    def run_start(self, **payload: Any) -> dict:
        return self.emit(RUN_START, **payload)

    def epoch(
        self,
        epoch: int,
        train_loss: Optional[float] = None,
        val_loss: Optional[float] = None,
        pseudo_dice: Optional[list] = None,
        lr: Optional[float] = None,
        epoch_seconds: Optional[float] = None,
        **extra: Any,
    ) -> dict:
        return self.emit(
            EPOCH,
            epoch=int(epoch),
            train_loss=_maybe_float(train_loss),
            val_loss=_maybe_float(val_loss),
            pseudo_dice=[_maybe_float(x) for x in pseudo_dice] if pseudo_dice else None,
            lr=_maybe_float(lr),
            epoch_seconds=_maybe_float(epoch_seconds),
            **extra,
        )

    def checkpoint(self, epoch: int, path: str, kind: str = "latest", **extra: Any) -> dict:
        return self.emit(CHECKPOINT, epoch=int(epoch), path=str(path), kind=kind, **extra)

    def preview(
        self,
        epoch: int,
        case: str,
        seg: str,
        dice: Optional[dict] = None,
        reference_image: Optional[str] = None,
        **extra: Any,
    ) -> dict:
        return self.emit(
            PREVIEW,
            epoch=int(epoch),
            case=case,
            seg=str(seg),
            dice={k: _maybe_float(v) for k, v in (dice or {}).items()},
            reference_image=reference_image,
            **extra,
        )

    def log(self, message: str, level: str = "info", **extra: Any) -> dict:
        return self.emit(LOG, message=str(message), level=level, **extra)

    def run_end(self, status: str = "completed", **payload: Any) -> dict:
        return self.emit(RUN_END, status=status, **payload)

    def close(self) -> None:
        try:
            self._fh.close()
        except Exception:
            pass

    def __enter__(self) -> "EventWriter":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()


def _maybe_float(x: Any) -> Optional[float]:
    if x is None:
        return None
    try:
        v = float(x)
    except (TypeError, ValueError):
        return None
    # JSON has no NaN/Infinity; emitting them produces a file that strict parsers
    # (including Qt's, in Slicer) reject. A diverged loss becomes null instead.
    if v != v or v in (float("inf"), float("-inf")):
        return None
    return v


def _json_default(obj: Any) -> Any:
    """Last-resort encoder for numpy scalars, Paths, etc."""
    if isinstance(obj, Path):
        return str(obj)
    for attr in ("item", "tolist"):
        fn = getattr(obj, attr, None)
        if callable(fn):
            try:
                return fn()
            except Exception:
                pass
    return str(obj)


class EventReader:
    """Incremental reader that remembers where it stopped.

    Call :meth:`read_new` repeatedly; each call returns only events appended
    since the previous call. A partially-written final line (the trainer was
    mid-write) is left in the buffer and re-read next time rather than being
    dropped or raising.
    """

    def __init__(self, run_dir: Path):
        self.run_dir = Path(run_dir)
        self.path = self.run_dir / EVENTS_FILENAME
        self._offset = 0
        self._partial = ""

    @property
    def exists(self) -> bool:
        return self.path.is_file()

    def reset(self) -> None:
        """Re-read from the beginning, e.g. after the run directory changed."""
        self._offset = 0
        self._partial = ""

    def read_new(self) -> list[dict]:
        if not self.path.is_file():
            return []

        # Deliberately NOT gated on stat().st_size. On Windows the directory
        # entry's size can lag well behind data that has already been written and
        # flushed while the trainer still holds the file open -- observed on a
        # real run, where the file reported 0 bytes for minutes while containing
        # several complete events. Gating on that stale size makes a healthy run
        # look dead. Seeking to our offset and reading costs nothing when there
        # is nothing new, and always sees the true contents.
        try:
            with open(self.path, "r", encoding="utf-8", errors="replace") as fh:
                fh.seek(0, 2)
                end = fh.tell()
                if end < self._offset:
                    # File shrank: the run restarted and truncated its log. Start
                    # over rather than reading garbage from a stale offset.
                    self.reset()
                fh.seek(self._offset)
                chunk = fh.read()
                self._offset = fh.tell()
        except OSError:
            # Transient sharing violation or a half-copied remote file; the next
            # poll will pick it up.
            return []

        if not chunk:
            return []

        data = self._partial + chunk
        lines = data.split("\n")
        self._partial = lines.pop()  # trailing fragment, complete or not

        out = []
        for line in lines:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                # A corrupt line should not stop the stream; the next epoch's
                # event will arrive fine.
                continue
        return out

    def read_all(self) -> list[dict]:
        self.reset()
        return self.read_new()

    def __iter__(self) -> Iterator[dict]:
        return iter(self.read_new())


class RunState:
    """Folds an event stream into the current state of a run.

    The Slicer module keeps one of these and feeds it whatever ``read_new``
    returns, so the UI never has to re-parse history.
    """

    def __init__(self) -> None:
        self.started_at: Optional[float] = None
        self.finished: bool = False
        self.status: Optional[str] = None
        self.meta: dict = {}
        self.epochs: list[dict] = []
        self.checkpoints: list[dict] = []
        self.previews: list[dict] = []
        self.messages: list[dict] = []
        self.last_event_time: Optional[float] = None

    def update(self, events: list[dict]) -> "RunState":
        for e in events:
            kind = e.get("event")
            self.last_event_time = e.get("t", self.last_event_time)
            if kind == RUN_START:
                self.started_at = e.get("t")
                self.meta = {k: v for k, v in e.items() if k not in ("t", "event")}
                self.finished = False
                self.status = "running"
            elif kind == EPOCH:
                self.epochs.append(e)
            elif kind == CHECKPOINT:
                self.checkpoints.append(e)
            elif kind == PREVIEW:
                self.previews.append(e)
            elif kind == LOG:
                self.messages.append(e)
            elif kind == RUN_END:
                self.finished = True
                self.status = e.get("status", "completed")
            # Unknown kinds are ignored on purpose: forward compatibility.
        return self

    @property
    def current_epoch(self) -> Optional[int]:
        return self.epochs[-1].get("epoch") if self.epochs else None

    @property
    def total_epochs(self) -> Optional[int]:
        return self.meta.get("epochs")

    @property
    def latest_preview(self) -> Optional[dict]:
        return self.previews[-1] if self.previews else None

    def previews_for(self, case: str) -> list[dict]:
        return [p for p in self.previews if p.get("case") == case]

    def preview_cases(self) -> list[str]:
        seen: list[str] = []
        for p in self.previews:
            c = p.get("case")
            if c and c not in seen:
                seen.append(c)
        return seen

    def series(self, key: str) -> tuple[list[int], list[float]]:
        """(epochs, values) for a scalar epoch field, skipping nulls.

        Nulls are skipped rather than zero-filled so a gap in the log shows as a
        gap in the plot instead of a spike to zero.
        """
        xs, ys = [], []
        for e in self.epochs:
            v = e.get(key)
            if v is None:
                continue
            xs.append(e.get("epoch"))
            ys.append(float(v))
        return xs, ys

    def mean_pseudo_dice(self) -> tuple[list[int], list[float]]:
        xs, ys = [], []
        for e in self.epochs:
            pd = e.get("pseudo_dice")
            if not pd:
                continue
            vals = [float(v) for v in pd if v is not None]
            if not vals:
                continue
            xs.append(e.get("epoch"))
            ys.append(sum(vals) / len(vals))
        return xs, ys

    def eta_seconds(self) -> Optional[float]:
        """Rough time remaining, from a trailing mean of recent epoch durations."""
        total = self.total_epochs
        cur = self.current_epoch
        if not total or cur is None:
            return None
        recent = [e.get("epoch_seconds") for e in self.epochs[-20:]]
        recent = [float(x) for x in recent if x]
        if not recent:
            return None
        return (total - cur - 1) * (sum(recent) / len(recent))


def read_run(run_dir: Path) -> RunState:
    """Convenience: fold an entire existing run into a RunState in one call."""
    return RunState().update(EventReader(run_dir).read_all())
