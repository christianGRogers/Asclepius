"""End-to-end check of a running SegQueue14 over real HTTP, with the module's client.

Not collected by pytest (no ``test_`` prefix): it needs a live server with
SegQueue14 installed, populated and given prelabels. It is step 4 of
``server/girder_segqueue14/VALIDATION.md``::

    python tests/segqueue14_e2e.py --url https://<server> --user <test annotator>

It uses the same ``SegQueue14Lib`` client the Slicer module uses, so a pass means
the module's network path works against that server. In order: an out-of-date
client is refused with "update the SegQueue14 module"; login fetches the 14-class
project; ``/next`` hands out a case with a prelabel; the CT downloads and matches
its checksum; the prelabel downloads and is a uint8 volume on the CT's grid; a
read with LCx empty is refused by name; the reference is not downloadable by an
annotator. Then the case is **given back** -- nothing is submitted -- unless
``--submit-prelabel`` is passed, which submits the prelabel unchanged (only on a
staging server: it consumes a case with an uncorrected read).

Exits non-zero if any check fails.
"""

import argparse
import getpass
import gzip
import json
import os
import sys
import tempfile

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO, "src"))
sys.path.insert(0, os.path.join(REPO, "slicer", "SegQueue14"))

from SegQueue14Lib import SegQueue14Client, SegQueue14Error  # noqa: E402

from segqueue.checksum import sha256_file  # noqa: E402
from segqueue14 import PROTOCOL_VERSION, labels, nifti, protocol  # noqa: E402

_results = []


def check(name, condition, detail=""):
    _results.append((name, bool(condition)))
    print(f"  [{'PASS' if condition else 'FAIL'}] {name}" + (f"  -- {detail}" if detail else ""))
    return bool(condition)


def refused(call, code=None, text=""):
    try:
        call()
    except SegQueue14Error as exc:
        ok = (code is None or getattr(exc, "code", None) == code) and text in str(exc)
        return ok, str(exc)
    return False, "was not refused"


def main(argv=None):
    parser = argparse.ArgumentParser(prog="segqueue14_e2e.py")
    parser.add_argument("--url", required=True)
    parser.add_argument("--user", required=True)
    parser.add_argument("--password", default=None)
    parser.add_argument("--submit-prelabel", action="store_true",
                        help="Submit the prelabel unchanged instead of giving the case "
                             "back. Staging servers only.")
    args = parser.parse_args(argv)
    password = args.password or os.environ.get("SEGQUEUE14_PASSWORD") or getpass.getpass()
    work = tempfile.mkdtemp(prefix="segqueue14-e2e-")

    print("Protocol")
    old = SegQueue14Client(args.url, extensionVersion="e2e-old")
    old.login(args.user, password)
    ok, why = refused(lambda: old._json("GET", protocol.path(protocol.PROJECT),
                                        params={"clientProtocol": PROTOCOL_VERSION - 1}),
                      protocol.ERR_CLIENT_TOO_OLD, "Update the SegQueue14 module")
    check("an out-of-date module is refused with an update message", ok, why[:90])
    ok, why = refused(lambda: old._json("POST", protocol.path(protocol.NEXT),
                                        params={"clientProtocol": 1}),
                      protocol.ERR_CLIENT_TOO_OLD)
    check("a live-protocol client is refused at /next", ok, why[:90])

    print("Login and project")
    client = SegQueue14Client(args.url, extensionVersion="e2e")
    client.login(args.user, password)
    project = client.project()
    names = [s.name for s in project.segments]
    check("14 segments with ImageCAS-X names and values",
          names == labels.NAMES and [s.label for s in project.segments] == list(range(1, 15)),
          ", ".join(names))
    check("LAD, LCx and RCA are the required ones",
          [s.name for s in project.segments if s.required] == labels.REQUIRED)
    check("instructions are the 14-class text",
          project.instructions.startswith("You are given a prediction"))

    print("A case")
    held = [a for a in client.myAssignments()]
    assignment = held[0] if held else client.nextCase()
    if not check("a case is available", assignment is not None):
        return _finish()
    check("it ships a prelabel and no seed",
          assignment.has_prelabel and not assignment.has_seed,
          f"{assignment.case_name}, prelabel {assignment.prelabel_version!r}")
    volume = os.path.join(work, assignment.volume_name or "volume.nii.gz")
    client.downloadCase(assignment.case_id, volume)
    check("the CT matches its checksum", sha256_file(volume) == assignment.checksum)
    prelabel = client.downloadAsset(assignment.case_id, protocol.ASSET_PRELABEL,
                                    os.path.join(work, "prelabel"))
    header = nifti.header_from_path(prelabel) if prelabel else None
    check("the prelabel is a uint8 3D volume",
          header is not None and nifti.check_prelabel_header(header) is None,
          header and f"{header.shape3} {header.dtype_name}")
    if header is not None and volume.endswith((".nii", ".nii.gz")):
        problem = nifti.same_grid(header, nifti.header_from_path(volume))
        check("the prelabel is on the CT grid", problem is None, problem or "")
    # The client reads a refused asset as "none" -- what matters is that no bytes
    # of the reference arrive.
    try:
        got = client.downloadAsset(assignment.case_id, protocol.ASSET_REFERENCE,
                                   os.path.join(work, "ref"))
    except SegQueue14Error:
        got = None
    check("an annotator cannot download the ImageCAS-X reference",
          got is None and not any(n.startswith("ref") for n in os.listdir(work)))

    print("Submit")
    counts = {name: 100 for name in labels.NAMES}
    counts["LCx"] = 0
    ok, why = refused(lambda: client.submit(
        assignment.assignment_id, protocol.SubmissionMeta(checksum="0" * 64,
                                                          voxel_counts=counts), "x"),
        protocol.ERR_MISSING_REQUIRED, "LCx")
    check("a read with LCx empty is refused by name", ok, why[:90])

    if args.submit_prelabel:
        uploaded = client.uploadFile(prelabel, project.upload_folder_id,
                                     name=f"{assignment.case_name}_e2e.nii.gz")
        counts = _counts(prelabel)
        meta = protocol.SubmissionMeta(checksum=sha256_file(prelabel),
                                       size_bytes=os.path.getsize(prelabel),
                                       annotation_seconds=1.0, voxel_counts=counts,
                                       extension_version="e2e")
        response = client.submit(assignment.assignment_id, meta, uploaded["_id"])
        check("the unchanged prelabel is accepted as a read",
              bool(response.get("submissionId")), json.dumps(response)[:120])
    else:
        client.releaseCase(assignment.assignment_id, reason="SegQueue14 e2e check")
        check("the case was given back (nothing submitted)", True, assignment.case_name)
    return _finish()


def _counts(path):
    """Voxels per class, from the NIfTI's raw bytes (uint8, so one byte a voxel)."""
    header = nifti.header_from_path(path)
    opener = gzip.open if path.endswith(".gz") else open
    with opener(path, "rb") as handle:
        handle.seek(int(header.vox_offset))
        data = handle.read()
    return {name: data.count(bytes([labels.LABEL_VALUES[name]])) for name in labels.NAMES}


def _finish():
    failed = [name for name, ok in _results if not ok]
    print(f"\n{len(_results) - len(failed)}/{len(_results)} checks passed.")
    for name in failed:
        print(f"  FAILED: {name}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
