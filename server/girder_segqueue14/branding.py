"""The Bradensbay branding of the Girder web UI on janus, through Girder's own settings.

Run on the server by ``deploy/segqueue14-deploy.sh branding [--apply]``. Girder's web
client is not forked or patched: Girder 5 already shows ``core.brand_name`` in its
header, page title and e-mails, and paints its header in ``core.banner_color`` (the
web client picks a readable text colour for it). This sets those two settings and
nothing else.

Girder 5.0 has no logo, favicon or header-image setting (its favicon and mark are
static files of the web client), so the Bradensbay mark and wordmark are not used
here. ``core.contact_email_address`` and ``core.privacy_notice`` are left alone: the
repository names no contact address or privacy page for Bradensbay.

Without ``--apply`` it changes nothing and prints, for each setting, what the database
holds now and what it would become. With ``--apply`` it writes only the settings
that differ, through Girder's ``Setting`` model (which runs Girder's own validators),
and prints the command that puts the old values back. Applying again is a no-op.

Values come from the repository: the name as the logo files spell it
(``aria-label="Bradensbay"``) and the navy of
``slicer/SegQueue/Resources/Logo/bradensbay-*.svg``. Girder's banner validator takes
``#RRGGBB`` only.
"""

import argparse
import json
import sys
from importlib import metadata

#: The name exactly as the repository writes it (the logo SVGs' aria-label).
BRAND_NAME = 'Bradensbay'
#: The Bradensbay navy, the dark fill of every bradensbay-*.svg mark and wordmark.
#: The teal (#16BFB2) is the accent; the banner is the dark one, as Girder's own
#: default (#3F3B3B) is, so the header's text stays white.
BANNER_COLOR = '#0A2540'

#: The settings this step owns, by the names Girder 5 gives them (girder.settings.SettingKey).
BRAND_NAME_KEY = 'core.brand_name'
BANNER_COLOR_KEY = 'core.banner_color'
WANTED = {BRAND_NAME_KEY: BRAND_NAME, BANNER_COLOR_KEY: BANNER_COLOR}

#: Girder majors whose SettingKey holds both keys and whose web client reads them.
SUPPORTED_MAJORS = ('5',)


def log(*parts):
    print('[branding]', *parts, flush=True)


class Refused(Exception):
    """A precondition failed; nothing was written."""


def girderVersion() -> str:
    return metadata.version('girder')


def checkGirder() -> str:
    """The installed Girder's version, once it is one this step was written for."""
    version = girderVersion()
    if version.split('.')[0] not in SUPPORTED_MAJORS:
        raise Refused(f'Girder {version} is not Girder 5; these settings were checked '
                      'against Girder 5 only. Nothing changed.')
    from girder.settings import SettingKey

    known = {getattr(SettingKey, 'BRAND_NAME', None), getattr(SettingKey, 'BANNER_COLOR', None)}
    missing = sorted(set(WANTED) - known)
    if missing:
        raise Refused(f'Girder {version} has no setting {", ".join(missing)}. Nothing changed.')
    return version


def readState():
    """``{key: (stored, effective)}``; ``stored`` is None when the database holds no
    value and Girder answers its default."""
    from girder.models.setting import Setting

    state = {}
    for key in WANTED:
        doc = Setting().findOne({'key': key})
        stored = doc['value'] if doc is not None else None
        state[key] = (stored, Setting().get(key))
    return state


def restoreCommand(old: dict) -> str:
    """The command line that puts ``old`` ({key: stored value or None}) back."""
    return ("python -m girder_segqueue14.branding --restore='"
            + json.dumps(old, sort_keys=True) + "'")


def brand(apply: bool = False) -> dict:
    """Show (and with ``apply`` write) the Bradensbay values. Returns the old stored
    values of the settings it changed, ``{key: value or None}``; empty if none."""
    version = checkGirder()
    log(f'girder {version}; settings {", ".join(WANTED)}')
    state = readState()
    changes = {}
    for key, new in WANTED.items():
        stored, effective = state[key]
        where = 'stored' if stored is not None else "not stored: Girder's default"
        if stored == new:
            log(f'{key}: current {effective!r} ({where}) -> unchanged')
        else:
            log(f'{key}: current {effective!r} ({where}) -> new {new!r}')
            changes[key] = stored
    if not changes:
        log('already Bradensbay-branded; nothing to change')
        return {}
    old = dict(sorted(changes.items()))
    log('old values (null = not stored, Girder default): ' + json.dumps(old, sort_keys=True))
    if not apply:
        log('dry run: nothing changed')
        return old
    from girder.models.setting import Setting

    # Girder's own validators, on every value before the first write: all or nothing.
    for key in changes:
        Setting().validate({'key': key, 'value': WANTED[key]})
    for key in changes:
        Setting().set(key, WANTED[key])
        log(f'{key} set to {WANTED[key]!r}')
    log('to put the old values back: ' + restoreCommand(old))
    return old


def restore(raw: str) -> dict:
    """Put back the values ``brand(apply=True)`` printed. Only this step's keys; a
    null value unsets the key (Girder's default again)."""
    try:
        old = json.loads(raw)
    except ValueError as exc:
        raise Refused(f'--restore takes the JSON the apply printed: {exc}') from None
    if not isinstance(old, dict) or not old:
        raise Refused('--restore takes a JSON object of settings')
    unknown = sorted(set(old) - set(WANTED))
    if unknown:
        raise Refused(f'--restore touches only {", ".join(WANTED)}, not {", ".join(unknown)}')
    for key, value in old.items():
        if value is not None and not isinstance(value, str):
            raise Refused(f'--restore: {key} takes a string or null')
    checkGirder()
    from girder.models.setting import Setting

    for key, value in sorted(old.items()):
        if value is None:
            Setting().unset(key)
            log(f"{key} unset (Girder's default: {Setting().get(key)!r})")
        else:
            Setting().set(key, value)
            log(f'{key} set to {value!r}')
    return old


def buildParser():
    parser = argparse.ArgumentParser(
        prog='python -m girder_segqueue14.branding',
        description="Bradensbay branding of Girder's web UI through core.brand_name "
                    'and core.banner_color. Dry run unless --apply.')
    group = parser.add_mutually_exclusive_group()
    group.add_argument('--apply', action='store_true', help='write the settings')
    group.add_argument('--restore', metavar='JSON',
                       help='put back the old values an --apply printed')
    return parser


def main(argv=None):
    args = buildParser().parse_args(argv)
    try:
        if args.restore is not None:
            restore(args.restore)
        else:
            brand(apply=args.apply)
    except Refused as exc:
        log(f'REFUSED: {exc}')
        return 2
    return 0


if __name__ == '__main__':  # pragma: no cover
    sys.exit(main())
