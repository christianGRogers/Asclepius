"""Which published JanusMRead release is newer than the one a reader runs.

The same decisions as ``segqueue.release``, on a separate line:

* only tags ``janusm-read-v<version>`` count, so no SegQueue or SegQueue14
  release (``segqueue-v*``, ``segqueue14-v*``) is ever offered to a reader, and
  this release is never offered to a SegQueue14 annotator (their updater matches
  ``segqueue-v*`` and ``SegQueue-<v>-Slicer-<x.y>.zip`` only);
* the archive is ``JanusMRead-<version>-Slicer-<x.y>.zip``, rooted at
  ``JanusMRead/``;
* an unparseable version is never newer.

Stdlib only.
"""

from __future__ import annotations

import re
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple

EXTENSION_NAME = "JanusMRead"
TAG_PREFIX = "janusm-read-v"
ASSET_PATTERN = re.compile(
    r"^JanusMRead-(?P<version>[0-9][0-9A-Za-z.\-+]*)-Slicer-(?P<slicer>[0-9]+\.[0-9]+)\.zip$")
_VERSION_PATTERN = re.compile(r"^(?P<numbers>[0-9]+(?:\.[0-9]+)*)(?P<rest>.*)$")


def parse_version(text: Optional[str]) -> Optional[Tuple[Tuple[int, ...], str]]:
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
    return tuple(int(p) for p in match.group("numbers").split(".")), match.group("rest")


def _key(parsed, width=4):
    numbers, rest = parsed
    return numbers + (0,) * (width - len(numbers)) + (rest,)


def is_newer(candidate: Optional[str], current: Optional[str]) -> bool:
    left, right = parse_version(candidate), parse_version(current)
    if left is None or right is None:
        return False
    width = max(len(left[0]), len(right[0]))
    return _key(left, width) > _key(right, width)


def asset_for(release: Dict[str, Any], slicer_version: Optional[str] = None):
    for asset in release.get("assets") or []:
        match = ASSET_PATTERN.match(str(asset.get("name") or ""))
        if match is None or not asset.get("browser_download_url"):
            continue
        if slicer_version and match.group("slicer") != str(slicer_version):
            continue
        return asset
    return None


def select_latest(releases: Iterable[Dict[str, Any]], slicer_version: Optional[str] = None,
                  allow_prerelease: bool = False) -> Optional[Dict[str, Any]]:
    best, best_key = None, None
    for release in releases or []:
        if not isinstance(release, dict) or release.get("draft"):
            continue
        if release.get("prerelease") and not allow_prerelease:
            continue
        tag = str(release.get("tag_name") or "")
        if not tag.startswith(TAG_PREFIX):
            continue
        parsed = parse_version(tag)
        if parsed is None or asset_for(release, slicer_version) is None:
            continue
        key = _key(parsed)
        if best_key is None or key > best_key:
            best, best_key = release, key
    return best


def update_available(releases, current: str, slicer_version: Optional[str] = None,
                     allow_prerelease: bool = False) -> Optional[Dict[str, Any]]:
    latest = select_latest(releases, slicer_version, allow_prerelease)
    if latest is None:
        return None
    return latest if is_newer(latest.get("tag_name"), current) else None


def describe(release: Dict[str, Any]) -> str:
    tag = str(release.get("tag_name") or "?")
    parsed = parse_version(tag)
    return ".".join(str(n) for n in parsed[0]) + parsed[1] if parsed else tag


def scripted_prefix(slicer_version: str) -> str:
    return f"{EXTENSION_NAME}/lib/Slicer-{slicer_version}/qt-scripted-modules/"


def archive_members(names: Sequence[str], slicer_version: str) -> List[str]:
    prefix = scripted_prefix(slicer_version)
    return [n for n in names if n.startswith(prefix) and not n.endswith("/")]
