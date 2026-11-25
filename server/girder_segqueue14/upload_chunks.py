"""Girder's minimum upload chunk size on janus, set to 0 (``core.upload_minimum_chunk_size``).

Run on the server by ``deploy/segqueue14-deploy.sh upload-chunks [--apply]``.

Why. Since 0.23.1 the SegQueue14 module uploads in 768 KiB chunks, halved down to
64 KiB on HTTP 413, to fit under janus's nginx ``client_max_body_size`` of 1 MiB.
Girder 5 refuses every chunk but the last that is smaller than
``core.upload_minimum_chunk_size`` (default 5 MiB; ``checkUploadSize`` in
``girder/utility/abstract_assetstore_adapter.py``) with HTTP 400 "Chunk is smaller
than the minimum size.". With nginx at 1 MiB and Girder at 5 MiB no chunk size works
for a file over 1 MiB, so every extended read failed. Girder's minimum exists for S3
multipart uploads (S3 refuses parts under 5 MiB); a filesystem assetstore, which
janus uses, appends each chunk to a temporary file and needs no minimum. So this
step sets it to 0, and refuses if any assetstore is not a filesystem one.

Without ``--apply`` it changes nothing and prints the value Girder answers now and
the new one. With ``--apply`` it checks the value with Girder's own validator, writes
it only if it differs, and prints the old stored value and the command that puts it
back. Applying again is a no-op. Nothing else is touched.
"""

import argparse
import json
import sys
from importlib import metadata

#: The setting this step owns, by the name Girder 5 gives it
#: (girder.settings.SettingKey.UPLOAD_MINIMUM_CHUNK_SIZE).
KEY = 'core.upload_minimum_chunk_size'
#: No minimum: any chunk size the client (and the proxy in front) settles on.
WANTED = 0

#: Girder majors whose SettingKey holds the key and whose adapters check it.
SUPPORTED_MAJORS = ('5',)
#: girder.constants.AssetstoreType.FILESYSTEM in every Girder 5.
FILESYSTEM = 0


def log(*parts):
    print('[upload-chunks]', *parts, flush=True)


class Refused(Exception):
    """A precondition failed; nothing was written."""


def girderVersion() -> str:
    return metadata.version('girder')


def checkGirder() -> str:
    """The installed Girder's version, once it is one this step was written for."""
    version = girderVersion()
    if version.split('.')[0] not in SUPPORTED_MAJORS:
        raise Refused(f'Girder {version} is not Girder 5; this setting was checked '
                      'against Girder 5 only. Nothing changed.')
    from girder.settings import SettingKey

    if getattr(SettingKey, 'UPLOAD_MINIMUM_CHUNK_SIZE', None) != KEY:
        raise Refused(f'Girder {version} has no setting {KEY}. Nothing changed.')
    return version


def assetstores():
    """``[(name, type)]`` of every assetstore Girder has."""
    from girder.models.assetstore import Assetstore

    return [(a.get('name', '?'), a.get('type'))
            for a in Assetstore().find({}, fields=['name', 'type'], sort=[('name', 1)])]


def checkAssetstores():
    """Refuse unless every assetstore is a filesystem one: on S3 the minimum is S3's
    own floor for multipart parts, and 0 would break uploads there instead."""
    stores = assetstores()
    if not stores:
        raise Refused('Girder has no assetstore; nothing to upload into. Nothing changed.')
    others = [f'{name!r} (type {kind})' for name, kind in stores if kind != FILESYSTEM]
    if others:
        raise Refused('not every assetstore is a filesystem assetstore: '
                      + ', '.join(others) + f'. {KEY} is the S3 multipart floor there and '
                      'must stay. Nothing changed.')
    return stores


def readState():
    """``(stored, effective)``; ``stored`` is None when the database holds no value
    and Girder answers its default."""
    from girder.models.setting import Setting

    doc = Setting().findOne({'key': KEY})
    return (doc['value'] if doc is not None else None), Setting().get(KEY)


def restoreCommand(old) -> str:
    return "python -m girder_segqueue14.upload_chunks --restore='" + json.dumps(old) + "'"


def configure(apply: bool = False) -> dict:
    """Show (and with ``apply`` write) ``KEY = 0``. Returns ``{KEY: old stored value
    or None}`` when it differs, else ``{}``."""
    version = checkGirder()
    stores = checkAssetstores()
    log(f'girder {version}; setting {KEY}; assetstores: '
        + ', '.join(f'{name!r} (filesystem)' for name, _ in stores))
    stored, effective = readState()
    where = 'stored' if stored is not None else "not stored: Girder's default"
    if stored == WANTED:
        log(f'{KEY}: current {effective!r} ({where}) -> unchanged')
        log('already 0; nothing to change')
        return {}
    log(f'{KEY}: current {effective!r} ({where}) -> new {WANTED!r}')
    old = {KEY: stored}
    log('old value (null = not stored, Girder default): ' + json.dumps(old))
    if not apply:
        log('dry run: nothing changed')
        return old
    from girder.models.setting import Setting

    Setting().validate({'key': KEY, 'value': WANTED})
    Setting().set(KEY, WANTED)
    log(f'{KEY} set to {Setting().get(KEY)!r}')
    log('to put the old value back: ' + restoreCommand(old))
    return old


def restore(raw: str) -> dict:
    """Put back the value ``configure(apply=True)`` printed; null unsets the key."""
    try:
        old = json.loads(raw)
    except ValueError as exc:
        raise Refused(f'--restore takes the JSON the apply printed: {exc}') from None
    if not isinstance(old, dict) or set(old) != {KEY}:
        raise Refused(f'--restore takes a JSON object with exactly the key {KEY}')
    value = old[KEY]
    if value is not None and (isinstance(value, bool) or not isinstance(value, int)
                              or value < 0):
        raise Refused(f'--restore: {KEY} takes a non-negative integer or null')
    checkGirder()
    from girder.models.setting import Setting

    if value is None:
        Setting().unset(KEY)
        log(f"{KEY} unset (Girder's default: {Setting().get(KEY)!r})")
    else:
        Setting().set(KEY, value)
        log(f'{KEY} set to {value!r}')
    return old


def buildParser():
    parser = argparse.ArgumentParser(
        prog='python -m girder_segqueue14.upload_chunks',
        description=f'Set {KEY} to 0 (filesystem assetstores only). Dry run unless --apply.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true', help='write the setting')
    group.add_argument('--restore', metavar='JSON',
                       help='put back the old value an --apply printed')
    return parser


def main(argv=None):
    args = buildParser().parse_args(argv)
    try:
        if args.restore is not None:
            restore(args.restore)
        else:
            configure(apply=args.apply)
    except Refused as exc:
        log(f'REFUSED: {exc}')
        return 2
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
