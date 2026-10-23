"""Download a 3D Slicer package for CI: an exact version, or a channel.

    python tools/fetch_slicer.py --os macosx --version 5.8.1 --out slicer.dmg
    python tools/fetch_slicer.py --os linux  --version release --out slicer.tar.gz
    python tools/fetch_slicer.py --os macosx --version r35403  --out slicer.dmg

``release`` and ``preview`` follow download.slicer.org (the newest build, which
drifts on purpose). download.slicer.org calls the preview channel ``nightly``:
``stability=preview`` is not an error there, it quietly serves the *stable*
build, so a job asking for "preview" that way was testing stable (#97). An exact
version is looked up on Slicer's package server (slicer-packages.kitware.com) by
its release name, so a job can test the Slicer that annotators are told to
install rather than whatever is newest; ``r<revision>`` fetches one exact build,
preview builds included. Prints the version and revision it fetched, and with
``--github-env`` also writes them as ``SLICER_FETCHED_VERSION`` and
``SLICER_FETCHED_REVISION``.

Stdlib only.
"""

import argparse
import json
import os
import platform
import shutil
import sys
import urllib.parse
import urllib.request

PACKAGES = "https://slicer-packages.kitware.com/api/v1"
#: The Slicer application's id on the package server.
APP_ID = "5f4474d0e1d8c75dfc705482"
FIND_URL = "https://download.slicer.org/find?os={os}&stability={channel}&arch={arch}"
DOWNLOAD_BASE = "https://download.slicer.org"
#: Our channel names -> download.slicer.org's. ``preview`` must be ``nightly``.
CHANNELS = {"release": "release", "preview": "nightly"}
#: Both download.slicer.org and the package server name macOS ``macosx``
#: (``os=macos`` is a 400).
CHANNEL_OS = {"macosx": "macosx", "linux": "linux", "win": "win"}


def _get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def revision_for(version):
    """The build revision of a released Slicer version, e.g. 5.8.1 -> 33241."""
    releases = _get_json(f"{PACKAGES}/app/{APP_ID}/release?limit=0")
    for release in releases:
        if release.get("name") == version:
            return str(release["meta"]["revision"])
    raise SystemExit(f"no Slicer release named {version!r} on the package server")


def package_for(os_name, arch, revision):
    """``(url, version)`` of the package built at ``revision``."""
    query = urllib.parse.urlencode(
        {"os": os_name, "arch": arch, "revision": revision, "limit": 5})
    packages = _get_json(f"{PACKAGES}/app/{APP_ID}/package?{query}")
    if not packages:
        raise SystemExit(f"no {os_name}/{arch} package for revision {revision}")
    package = packages[0]
    url = "{}/item/{}/download".format(PACKAGES, package["_id"])
    return url, str((package.get("meta") or {}).get("version") or "?")


def channel_package(os_name, channel, arch="amd64"):
    """``(url, version, revision)`` of the newest build on a channel."""
    found = _get_json(FIND_URL.format(os=CHANNEL_OS[os_name], channel=CHANNELS[channel],
                                      arch=arch))
    if found.get("stability") != CHANNELS[channel] or found.get("arch") != arch:
        raise SystemExit(f"asked for {channel}/{arch}, download.slicer.org answered "
                         f"{found.get('stability')!r}/{found.get('arch')!r}")
    return (DOWNLOAD_BASE + found["download_url"], str(found.get("version") or "?"),
            str(found["revision"]))


def _resolve(os_name, arch, version):
    """``(url, version, revision)`` for a channel, ``r<revision>`` or a release name."""
    if version in CHANNELS:
        return channel_package(os_name, version, arch)
    if version.startswith("r") and version[1:].isdigit():
        revision = version[1:]
        url, found = package_for(os_name, arch, revision)
        return url, found, revision
    revision = revision_for(version)
    url, _ = package_for(os_name, arch, revision)
    return url, version, revision


def download(url, out):
    with urllib.request.urlopen(url, timeout=600) as response, open(out, "wb") as handle:
        shutil.copyfileobj(response, handle, 1024 * 1024)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fetch_slicer.py")
    parser.add_argument("--os", required=True, choices=sorted(CHANNEL_OS))
    parser.add_argument("--arch", default="auto",
                        help="amd64, arm64, or auto: arm64 on an Apple Silicon Mac when "
                             "that build exists (previews have one; 5.8-5.12 do not), "
                             "else amd64, as an annotator's download would be")
    parser.add_argument("--version", default="release",
                        help="release, preview, an exact version such as 5.8.1, "
                             "or an exact build such as r35403")
    parser.add_argument("--out", required=True)
    parser.add_argument("--github-env", action="store_true",
                        help="append SLICER_FETCHED_VERSION/REVISION to $GITHUB_ENV")
    args = parser.parse_args(argv)

    if args.arch == "auto":
        native = args.os == "macosx" and platform.machine() == "arm64"
        arches = ["arm64", "amd64"] if native else ["amd64"]
    else:
        arches = [args.arch]
    for position, arch in enumerate(arches):
        try:
            url, version, revision = _resolve(args.os, arch, args.version)
            args.arch = arch
            break
        except SystemExit:
            if position == len(arches) - 1:
                raise
    asked = args.version
    print(f"Slicer {version} (revision {revision}) for {args.os}/{args.arch}"
          f" [asked for {asked}]")
    download(url, args.out)
    if args.github_env:
        with open(os.environ["GITHUB_ENV"], "a", encoding="utf-8") as handle:
            handle.write(f"SLICER_FETCHED_VERSION={version}\n"
                         f"SLICER_FETCHED_REVISION={revision}\n"
                         f"SLICER_FETCHED_ARCH={args.arch}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
