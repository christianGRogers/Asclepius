"""What a training export contains, so the far end can prove it arrived intact.

The pipeline this serves has three hops -- Girder assetstore, an exported tree on
the server's disk, and ``$SCRATCH`` on Trillium -- and until this existed none of
them could answer the only question that matters at the end: *is what I have here
the same as what was sent, and is it all of it?*

``segtrain index`` counts what it finds. Nothing said what it *should* find. So a
transfer that dropped forty cases produced a smaller training set and no error,
and a transfer that truncated one volume produced a file ITK still opens. Both
are silent, and both are the kind of thing you discover from a confusing Dice
score three weeks later.

A manifest is written next to the data by whatever produced it, travels with it,
and is checked on arrival. It is deliberately boring: a sorted list of relative
paths, each with a size and a SHA-256, plus a total. That is enough to detect
every failure mode we actually see -- a missing case, a truncated file, a
corrupted byte, a half-finished rsync -- and it needs no network protocol, no
database, and no trust in the transport.

Three decisions worth stating.

**Files are grouped by case, not listed flat.** The unit that is usable or not is
a case: ``segtrain convert`` consumes one directory per case, and a case with a
CT and no segmentations is not 80% of a case, it is a broken one. A flat file
list would report three good files and one bad one where the truth is "this case
cannot be trained on".

**Size is recorded as well as the digest.** The digest is the real check, but
hashing a 65 GB tree takes minutes and a size comparison takes a stat. An
interrupted transfer almost always shows up as a short file, so the cheap check
catches the common case, and the expensive one is reserved for when correctness
has to be proven rather than assumed. :func:`verify` exposes both.

**The output is deterministic.** Cases sort by name, files by path, and the JSON
is written with sorted keys. Two manifests of the same tree are byte-identical,
so a manifest can itself be checksummed, diffed between the two ends, or
committed as a record of what a training run was built from.

Stdlib only and 3.9-clean, because this module is imported on the Girder host
that writes the export and on the cluster that receives it, and those are not the
same Python.
"""

from __future__ import annotations

import datetime
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple

from .checksum import sha256_file

#: Written at the root of an exported tree. Looked for by name, so a transfer
#: that brings the data and forgets this file is detectable as such.
MANIFEST_NAME = "manifest.json"

#: Bumped only for a change that an older reader would misread. A new *optional*
#: field is not such a change; a changed meaning of an existing one is.
MANIFEST_VERSION = 1

#: Never part of the payload. ``manifest.json`` would have to describe itself,
#: and the receipt is written by the receiver after the fact.
RESERVED_NAMES = frozenset({MANIFEST_NAME, "transfer-receipt.json"})


@dataclass(frozen=True)
class FileEntry:
    """One file, by its path relative to the tree root."""

    path: str
    size: int
    sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return {"path": self.path, "size": self.size, "sha256": self.sha256}

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> FileEntry:
        return cls(path=str(raw["path"]), size=int(raw["size"]),
                   sha256=str(raw["sha256"]))


@dataclass(frozen=True)
class CaseEntry:
    """One case, and every file that belongs to it."""

    case: str
    files: Tuple[FileEntry, ...]

    @property
    def size(self) -> int:
        return sum(f.size for f in self.files)

    def to_dict(self) -> Dict[str, Any]:
        return {"case": self.case, "files": [f.to_dict() for f in self.files]}

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> CaseEntry:
        return cls(case=str(raw["case"]),
                   files=tuple(FileEntry.from_dict(f) for f in raw["files"]))


@dataclass
class Manifest:
    """Everything an exported tree should contain."""

    cases: Tuple[CaseEntry, ...] = ()
    created: str = ""
    source: Dict[str, Any] = field(default_factory=dict)
    version: int = MANIFEST_VERSION

    # -- views ------------------------------------------------------------

    def files(self) -> Iterator[FileEntry]:
        for case in self.cases:
            yield from case.files

    def by_path(self) -> Dict[str, FileEntry]:
        return {entry.path: entry for entry in self.files()}

    def case_of(self) -> Dict[str, str]:
        """Relative path -> the case it belongs to."""
        owner = {}
        for case in self.cases:
            for entry in case.files:
                owner[entry.path] = case.case
        return owner

    @property
    def totals(self) -> Dict[str, int]:
        entries = list(self.files())
        return {"cases": len(self.cases), "files": len(entries),
                "bytes": sum(e.size for e in entries)}

    # -- serialisation ----------------------------------------------------

    def to_dict(self) -> Dict[str, Any]:
        return {
            "manifest_version": self.version,
            "created": self.created,
            "source": self.source,
            "totals": self.totals,
            "cases": [case.to_dict() for case in self.cases],
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, sort_keys=True) + "\n"

    @classmethod
    def from_dict(cls, raw: Dict[str, Any]) -> Manifest:
        version = int(raw.get("manifest_version", 0))
        if version > MANIFEST_VERSION:
            raise ManifestError(
                f"manifest version {version} is newer than this code understands "
                f"({MANIFEST_VERSION}); upgrade segtrain on this machine rather than guessing "
                "at the parts it does not recognise")
        return cls(
            cases=tuple(CaseEntry.from_dict(c) for c in raw.get("cases", ())),
            created=str(raw.get("created", "")),
            source=dict(raw.get("source", {})),
            version=version or MANIFEST_VERSION,
        )

    @classmethod
    def from_json(cls, text: str) -> Manifest:
        try:
            raw = json.loads(text)
        except ValueError as exc:
            raise ManifestError(f"manifest is not valid JSON: {exc}") from None
        if not isinstance(raw, dict):
            raise ManifestError("manifest must be a JSON object")
        return cls.from_dict(raw)

    def write(self, root) -> str:
        """Write ``manifest.json`` at the root of the tree it describes.

        Written to a temporary name and renamed, so an interrupted write leaves
        the previous manifest in place rather than a half-parsed one. A manifest
        truncated mid-write is worse than an absent one: absent is detected, and
        truncated looks like a tree that legitimately contains fewer cases.
        """
        root = str(root)
        target = os.path.join(root, MANIFEST_NAME)
        scratch = target + ".partial"
        with open(scratch, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(self.to_json())
        os.replace(scratch, target)
        return target

    @classmethod
    def read(cls, root) -> Manifest:
        path = os.path.join(str(root), MANIFEST_NAME)
        if not os.path.exists(path):
            raise ManifestError(
                f"no {MANIFEST_NAME} at {root}. An export writes one; a tree without one cannot "
                "be verified, only guessed at")
        with open(path, encoding="utf-8") as handle:
            return cls.from_json(handle.read())


class ManifestError(RuntimeError):
    """A manifest is absent, unreadable, or from a future version."""


# -- building -------------------------------------------------------------


def build(root, cases: Optional[Sequence[str]] = None, source: Optional[Dict[str, Any]] = None,
          progress=None, now: Optional[str] = None) -> Manifest:
    """Hash a tree laid out one directory per case, and describe it.

    ``cases`` restricts the walk to those case directories; the default is every
    directory at the root. ``progress`` is an optional
    ``callable(path, index, total)`` called before each file is hashed -- hashing
    a thousand CCTA volumes is minutes of apparent silence otherwise.

    Files directly at the root are ignored rather than assigned to some case.
    A manifest describes cases, and a stray note or log at the top level is not
    training data; silently adopting it into one case's file list would make that
    case fail verification on any other tree.
    """
    root = str(root)
    if not os.path.isdir(root):
        raise ManifestError(f"not a directory: {root}")

    names = sorted(cases) if cases is not None else sorted(
        name for name in os.listdir(root)
        if os.path.isdir(os.path.join(root, name)))

    discovered = []  # (case, relative path)
    for case in names:
        case_dir = os.path.join(root, case)
        if not os.path.isdir(case_dir):
            raise ManifestError(f"no such case directory: {case_dir}")
        for relative in _walk_files(case_dir):
            discovered.append((case, _posix(os.path.join(case, relative))))

    total = len(discovered)
    grouped: Dict[str, List[FileEntry]] = {}
    for index, (case, relative) in enumerate(discovered):
        if progress is not None:
            progress(relative, index, total)
        absolute = os.path.join(root, relative)
        grouped.setdefault(case, []).append(FileEntry(
            path=relative,
            size=os.path.getsize(absolute),
            sha256=sha256_file(absolute),
        ))

    entries = tuple(
        CaseEntry(case=case, files=tuple(sorted(grouped[case], key=lambda f: f.path)))
        for case in sorted(grouped)
    )
    return Manifest(cases=entries, created=now or _utc_now(), source=dict(source or {}))


def _walk_files(directory: str) -> Iterator[str]:
    """Every file under ``directory``, as a path relative to it, sorted."""
    found = []
    for current, subdirectories, filenames in os.walk(directory):
        subdirectories.sort()
        for name in sorted(filenames):
            absolute = os.path.join(current, name)
            found.append(os.path.relpath(absolute, directory))
    return iter(sorted(_posix(p) for p in found))


def _posix(path: str) -> str:
    """Manifests cross a Windows laptop, a Linux server and a cluster."""
    return path.replace(os.sep, "/").replace("\\", "/")


def _utc_now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat()


# -- verifying ------------------------------------------------------------

#: Compare sizes only. A stat per file; catches truncation, which is what an
#: interrupted transfer produces.
QUICK = "quick"

#: Compare sizes and SHA-256. Reads every byte; the only mode that proves the
#: bytes are right rather than merely the expected number of them.
FULL = "full"


@dataclass
class VerifyResult:
    """What a tree has, against what its manifest says it should have."""

    mode: str = FULL
    ok: List[str] = field(default_factory=list)
    missing: List[str] = field(default_factory=list)
    truncated: List[Tuple[str, int, int]] = field(default_factory=list)
    corrupt: List[str] = field(default_factory=list)
    extra: List[str] = field(default_factory=list)
    unreadable: List[Tuple[str, str]] = field(default_factory=list)
    owner: Dict[str, str] = field(default_factory=dict)

    @property
    def bad(self) -> List[str]:
        """Every path that is not as promised, in one list, sorted."""
        paths = list(self.missing) + [p for p, _, _ in self.truncated]
        paths += list(self.corrupt) + [p for p, _ in self.unreadable]
        return sorted(set(paths))

    @property
    def is_clean(self) -> bool:
        """No file is missing, short, corrupt or unreadable.

        ``extra`` does not count. A destination may legitimately hold a receipt,
        a log, or a previous export's leftovers, and refusing to proceed over
        something nobody asked about would make the check a nuisance rather than
        a gate.
        """
        return not self.bad

    @property
    def broken_cases(self) -> List[str]:
        """Cases with at least one file that is not as promised.

        This, not the file count, is what decides whether a training set is
        usable: ``segtrain convert`` reads cases.
        """
        return sorted({self.owner[path] for path in self.bad if path in self.owner})

    def summary(self) -> str:
        parts = [f"{len(self.ok)} ok"]
        for label, count in (("missing", len(self.missing)),
                             ("truncated", len(self.truncated)),
                             ("corrupt", len(self.corrupt)),
                             ("unreadable", len(self.unreadable)),
                             ("extra", len(self.extra))):
            if count:
                parts.append(f"{count} {label}")
        text = ", ".join(parts)
        if self.mode == QUICK:
            text += "  (sizes only -- run with --full to check contents)"
        return text


def verify(root, manifest: Manifest, mode: str = FULL, check_extra: bool = True,
           progress=None) -> VerifyResult:
    """Check a tree against its manifest.

    Nothing raises: the point is a complete report, because "which forty cases
    did not arrive" is the answer you need, and an exception at the first bad
    file tells you only that there is at least one.
    """
    if mode not in (QUICK, FULL):
        raise ValueError(f"mode must be {QUICK!r} or {FULL!r}, not {mode!r}")

    root = str(root)
    result = VerifyResult(mode=mode, owner=manifest.case_of())
    entries = list(manifest.files())

    for index, entry in enumerate(entries):
        if progress is not None:
            progress(entry.path, index, len(entries))
        absolute = os.path.join(root, entry.path.replace("/", os.sep))

        if not os.path.exists(absolute):
            result.missing.append(entry.path)
            continue
        try:
            size = os.path.getsize(absolute)
        except OSError as exc:
            result.unreadable.append((entry.path, str(exc)))
            continue
        if size != entry.size:
            result.truncated.append((entry.path, entry.size, size))
            continue
        if mode == QUICK:
            result.ok.append(entry.path)
            continue
        try:
            digest = sha256_file(absolute)
        except OSError as exc:
            result.unreadable.append((entry.path, str(exc)))
            continue
        if digest != entry.sha256:
            result.corrupt.append(entry.path)
        else:
            result.ok.append(entry.path)

    if check_extra:
        promised = set(manifest.by_path())
        result.extra = sorted(
            path for path in _tree_files(root)
            if path not in promised and os.path.basename(path) not in RESERVED_NAMES
        )
    return result


def _tree_files(root: str) -> Iterator[str]:
    for current, subdirectories, filenames in os.walk(root):
        subdirectories.sort()
        for name in sorted(filenames):
            absolute = os.path.join(current, name)
            yield _posix(os.path.relpath(absolute, root))


def needed(root, manifest: Manifest, mode: str = QUICK) -> List[str]:
    """The paths a transfer still has to fetch, cheapest check first.

    This is :func:`verify` read as a work list rather than a report, and it is
    the same computation on purpose: a transfer that decides what to copy by one
    rule and is then checked by another will eventually disagree with itself.

    ``QUICK`` by default, because deciding what to re-fetch is the step that
    runs before every attempt and hashing the whole tree to plan a retry of two
    files is the wrong trade. Verify in ``FULL`` once, at the end.
    """
    return verify(root, manifest, mode=mode, check_extra=False).bad


def diff(left: Manifest, right: Manifest) -> Dict[str, List[str]]:
    """Compare two manifests -- typically the two ends of a transfer.

    Cheap, needs neither tree on disk, and answers "did the sender and receiver
    agree about what was sent" separately from "did the bytes survive".
    """
    lhs, rhs = left.by_path(), right.by_path()
    changed = sorted(
        path for path in set(lhs) & set(rhs)
        if lhs[path].sha256 != rhs[path].sha256 or lhs[path].size != rhs[path].size
    )
    return {
        "only_in_left": sorted(set(lhs) - set(rhs)),
        "only_in_right": sorted(set(rhs) - set(lhs)),
        "changed": changed,
    }
