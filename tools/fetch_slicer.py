"""Download a 3D Slicer package for CI: an exact version, or a channel.

    python tools/fetch_slicer.py --os macosx --version 5.8.1 --out slicer.dmg
    python tools/fetch_slicer.py --os linux  --version release --out slicer.tar.gz

``release`` and ``preview`` follow download.slicer.org (the newest build, which
drifts on purpose). An exact version is looked up on Slicer's package server
(slicer-packages.kitware.com) by its release name, so a job can test the Slicer
that annotators are told to install rather than whatever is newest. Prints the
revision it fetched, which is what an extension archive for macOS is keyed by.

Stdlib only.
"""

import argparse
import json
import shutil
import sys
import urllib.parse
import urllib.request

PACKAGES = "https://slicer-packages.kitware.com/api/v1"
#: The Slicer application's id on the package server.
APP_ID = "5f4474d0e1d8c75dfc705482"
CHANNEL_URL = "https://download.slicer.org/download?os={os}&stability={channel}"
#: download.slicer.org names macOS ``macos``; the package server ``macosx``.
CHANNEL_OS = {"macosx": "macos", "linux": "linux", "win": "win"}


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


def package_url(os_name, arch, revision):
    query = urllib.parse.urlencode(
        {"os": os_name, "arch": arch, "revision": revision, "limit": 5})
    packages = _get_json(f"{PACKAGES}/app/{APP_ID}/package?{query}")
    if not packages:
        raise SystemExit(f"no {os_name}/{arch} package for revision {revision}")
    return "{}/item/{}/download".format(PACKAGES, packages[0]["_id"])


def download(url, out):
    with urllib.request.urlopen(url, timeout=600) as response, open(out, "wb") as handle:
        shutil.copyfileobj(response, handle, 1024 * 1024)


def main(argv=None):
    parser = argparse.ArgumentParser(prog="fetch_slicer.py")
    parser.add_argument("--os", required=True, choices=sorted(CHANNEL_OS))
    parser.add_argument("--arch", default="amd64")
    parser.add_argument("--version", default="release",
                        help="release, preview, or an exact version such as 5.8.1")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    if args.version in ("release", "preview"):
        url = CHANNEL_URL.format(os=CHANNEL_OS[args.os], channel=args.version)
        print(f"Slicer {args.version} channel for {args.os}")
    else:
        revision = revision_for(args.version)
        url = package_url(args.os, args.arch, revision)
        print(f"Slicer {args.version} (revision {revision}) for {args.os}/{args.arch}")
    download(url, args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
