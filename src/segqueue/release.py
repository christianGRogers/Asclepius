"""Which published release is newer than the one an annotator is running.

The Slicer extension checks GitHub for a newer build every time it is opened and
offers a one-press update. The *decision* part of that -- parse a version, order
two of them, pick the newest release out of a list, find the archive attached to
it -- lives here rather than in the extension, for the reason everything else in
this package does: it is pure logic over data, so it can be unit-tested on any
Python without Slicer, Qt or a network in the room. ``SegQueueLib/updater.py``
owns the parts that talk to the world.

Two decisions worth stating.

**Releases are matched by tag prefix, not by "latest".** GitHub's
``/releases/latest`` returns the newest release in the repository, and this
repository holds a training pipeline as well as this extension; a tagged
training release would otherwise be offered to annotators as a Slicer update.
Only tags shaped ``segqueue-v<version>`` are considered.

**An unparseable version is not newer.** The update path rewrites files inside a
working Slicer install. Anything ambiguous -- a hand-made tag, a draft, a release
with no archive attached -- resolves to "no update available", because the cost
of missing an update for a day is a day, and the cost of a bad swap is an
annotator who cannot work at all.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

#: Tags this extension answers to. Everything else in the repository is somebody
#: else's release.
TAG_PREFIX = "segqueue-v"

#: The archive attached to a release, as ``build-extension.py`` names it:
#: ``SegQueue-0.3.0-Slicer-5.8.zip``. Matched rather than assumed so that a
#: release carrying several assets (a checksum file, notes, a second Slicer
#: version) still resolves to the right one.
ASSET_PATTERN = re.compile(
    r"^SegQueue-(?P<version>[0-9][0-9A-Za-z.\-+]*)-Slicer-(?P<slicer>[0-9]+\.[0-9]+)\.zip$")

#: ``1.2.3`` and ``1.2`` and ``1.2.3.4``. Anything after the numbers -- ``-rc1``,
#: ``+build7`` -- is kept as a string and used only to break ties.
_VERSION_PATTERN = re.compile(r"^(?P<numbers>[0-9]+(?:\.[0-9]+)*)(?P<rest>.*)$")


def parse_version(text: Optional[str]) -> Optional[Tuple[Tuple[int, ...], str]]:
    """``"0.3.0"`` -> ``((0, 3, 0), "")``. ``None`` when it is not a version.

    The tag prefix is stripped if present, so ``segqueue-v0.3.0`` and ``0.3.0``
    both parse -- callers should not have to remember which form they hold.
    """
    if not text:
        return None
    candidate = str(text).strip()
    if candidate.startswith(TAG_PREFIX):
        candidate = candidate[len(TAG_PREFIX):]
    elif candidate[:1] in ("v", "V"):
        candidate = candidate[1:]
    match = _VERSION_PATTERN.match(candidate)
    if match is None:
        return None
    numbers = tuple(int(part) for part in match.group("numbers").split("."))
    return numbers, match.group("rest")


def _comparable(parsed: Tuple[Tuple[int, ...], str], width: int) -> Tuple[Any, ...]:
    """Pad to a common length so ``0.3`` and ``0.3.0`` compare equal.

    The suffix sorts *after* the bare version, which makes ``0.3.0+build7``
    newer than ``0.3.0`` -- the right answer for a rebuild of the same version,
    and harmless for the tagged releases this normally sees.
    """
    numbers, rest = parsed
    padded = numbers + (0,) * (width - len(numbers))
    return padded + (rest,)


def is_newer(candidate: Optional[str], current: Optional[str]) -> bool:
    """Whether ``candidate`` is a strictly newer version than ``current``.

    False whenever either side fails to parse. A client that cannot read its own
    version has no business rewriting itself.
    """
    left, right = parse_version(candidate), parse_version(current)
    if left is None or right is None:
        return False
    width = max(len(left[0]), len(right[0]))
    return _comparable(left, width) > _comparable(right, width)


def asset_for(release: Dict[str, Any],
              slicer_version: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """The extension archive attached to a release, or ``None``.

    ``slicer_version`` filters to a matching build when given: extensions are
    per Slicer minor version, and handing a 5.8 archive to 5.9 produces a module
    that loads and then fails in ways nobody enjoys diagnosing.
    """
    for asset in release.get("assets") or []:
        match = ASSET_PATTERN.match(str(asset.get("name") or ""))
        if match is None:
            continue
        if slicer_version and match.group("slicer") != str(slicer_version):
            continue
        if not asset.get("browser_download_url"):
            continue
        return asset
    return None


def select_latest(releases: Iterable[Dict[str, Any]],
                  slicer_version: Optional[str] = None,
                  allow_prerelease: bool = False) -> Optional[Dict[str, Any]]:
    """The newest usable release in a GitHub ``/releases`` listing.

    Usable means: not a draft, tagged for this extension, carrying an archive
    this Slicer can install, and with a version that actually parses. Drafts are
    excluded because their assets are not publicly downloadable; prereleases are
    excluded by default so a release candidate is not pushed at thirty
    annotators mid-project.

    Ordering is by version, not by publication date -- a hotfix to 0.2 published
    after 0.3 must not present itself as the newest thing available.
    """
    best: Optional[Dict[str, Any]] = None
    best_key: Optional[Tuple[Any, ...]] = None

    for release in releases or []:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        if release.get("prerelease") and not allow_prerelease:
            continue
        tag = str(release.get("tag_name") or "")
        if not tag.startswith(TAG_PREFIX):
            continue
        parsed = parse_version(tag)
        if parsed is None:
            continue
        if asset_for(release, slicer_version) is None:
            continue
        key = _comparable(parsed, 4)
        if best_key is None or key > best_key:
            best, best_key = release, key

    return best


def update_available(releases: Iterable[Dict[str, Any]], current: str,
                     slicer_version: Optional[str] = None,
                     allow_prerelease: bool = False) -> Optional[Dict[str, Any]]:
    """The release to offer, or ``None`` when the client is already current.

    One call is the whole decision, so the extension has no room to get half of
    it right.
    """
    latest = select_latest(releases, slicer_version, allow_prerelease)
    if latest is None:
        return None
    return latest if is_newer(latest.get("tag_name"), current) else None


def describe(release: Dict[str, Any]) -> str:
    """A short human label for a release, for logs and dialogue boxes."""
    tag = str(release.get("tag_name") or "?")
    parsed = parse_version(tag)
    version = ".".join(str(n) for n in parsed[0]) + parsed[1] if parsed else tag
    name = str(release.get("name") or "").strip()
    return "{} -- {}".format(version, name) if name and name != tag else version


def archive_members(names: Sequence[str], slicer_version: str) -> List[str]:
    """The paths inside the archive that belong in ``qt-scripted-modules``.

    Used to sanity-check a download before anything on disk is touched: an
    archive that does not contain the module at the expected path is not a
    SegQueue package, whatever its filename says.
    """
    prefix = "SegQueue/lib/Slicer-{}/qt-scripted-modules/".format(slicer_version)
    return [name for name in names
            if name.startswith(prefix) and not name.endswith("/")]
