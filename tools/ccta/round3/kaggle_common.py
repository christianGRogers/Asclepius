"""Shared helpers for round-3 agent Kaggle adapters (imports the round-2 library from ../)."""
import os, sys, zipfile, urllib.parse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import ingest_open as io_  # noqa: E402
from ingest_open import HTTPFile, KAGGLE, kaggle_files, copy_member, log, report, anatomy_check, dicom_extra  # noqa


def member(ref, path):
    """Like ingest_open.kaggle_member, but the path is fully URL-encoded (nested paths 404 otherwise)."""
    f = HTTPFile(f'{KAGGLE}/download/{ref}/{urllib.parse.quote(path, safe="")}')
    if f.read(4) == b'PK\x03\x04':
        f.seek(0)
        try:
            z = zipfile.ZipFile(f)
            names = z.namelist()
            if len(names) == 1 and names[0] == os.path.basename(path):
                return z.open(names[0])
        except zipfile.BadZipFile:
            pass
    f.seek(0)
    return f


def fetch(ref, path, dst):
    return copy_member(member(ref, path), dst)


def files_retry(ref, tries=8):
    import time, urllib.error
    for a in range(tries):
        try:
            return kaggle_files(ref)
        except urllib.error.HTTPError as e:
            if e.code != 429 or a == tries - 1:
                raise
            time.sleep(20)


def view(ref, tries=8):
    import time, json, urllib.error
    for a in range(tries):
        try:
            with io_._open(f'{KAGGLE}/view/{ref}') as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            if e.code != 429 or a == tries - 1:
                raise
            time.sleep(20)
