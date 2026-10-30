"""Roles, storage, refusals and settings for the Janus-M read queue."""

import hashlib
from typing import NoReturn, Optional

from girder.constants import AccessType
from girder.exceptions import RestException, ValidationException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.setting import Setting
from girder.models.user import User
from girder.utility import setting_utilities
from janusm_reads import protocol

from .constants import (
    ADMIN_GROUP,
    CHECK_SEEDS_FOLDER,
    COLLECTION_NAME,
    DEFAULT_MAX_OPEN,
    INCOMING_FOLDER,
    READER_GROUP,
    READS_FOLDER,
    SEEDS_FOLDER,
    SETTING_MAX_OPEN,
    SETTING_SEAL_OPEN,
)


def refuse(code: str, message: str, status: int = 400, **detail) -> NoReturn:
    raise RestException(message, code=status, extra=protocol.error_body(code, message, **detail))


# ----------------------------------------------------------------- settings


@setting_utilities.validator(SETTING_SEAL_OPEN)
def _validateSealOpen(doc):
    if not isinstance(doc['value'], bool):
        raise ValidationException('janusm.sealOpen must be true or false.', 'value')


@setting_utilities.default(SETTING_SEAL_OPEN)
def _defaultSealOpen():
    # JA6: no seal case is read before the seal is re-powered on 20 decision cases.
    return False


@setting_utilities.validator(SETTING_MAX_OPEN)
def _validateMaxOpen(doc):
    if not isinstance(doc['value'], int) or doc['value'] < 1:
        raise ValidationException('janusm.maxOpen must be a positive integer.', 'value')


@setting_utilities.default(SETTING_MAX_OPEN)
def _defaultMaxOpen():
    return DEFAULT_MAX_OPEN


def sealOpen() -> bool:
    return bool(Setting().get(SETTING_SEAL_OPEN))


def maxOpen() -> int:
    return int(Setting().get(SETTING_MAX_OPEN))


# -------------------------------------------------------------------- roles


def _inGroup(user, name) -> bool:
    if not user:
        return False
    group = Group().findOne({'name': name})
    return group is not None and group['_id'] in (user.get('groups') or [])


def isAdmin(user) -> bool:
    return bool(user and (user.get('admin') or _inGroup(user, ADMIN_GROUP)))


def isReader(user) -> bool:
    return bool(user and (user.get('admin') or _inGroup(user, READER_GROUP)))


def requireReader(user):
    if not isReader(user):
        refuse(protocol.ERR_NOT_A_READER,
               f'Your account is not a Janus-M reader ({READER_GROUP}). Ask the project '
               'admin to add you.', status=403)
    return user


def requireAdmin(user):
    if not isAdmin(user):
        refuse('not_a_janusm_admin', 'You do not have Janus-M admin access.', status=403)
    return user


def _anyAdmin():
    return User().findOne({'admin': True})


def ensureGroups(creator: Optional[dict] = None) -> list:
    owner = creator or _anyAdmin()
    if owner is None:
        return []
    made = []
    for name, description in (
        (READER_GROUP, 'May read Janus-M borders (JA7).'),
        (ADMIN_GROUP, 'May manage the Janus-M read queue.'),
    ):
        if Group().findOne({'name': name}) is None:
            Group().createGroup(name, creator=owner, description=description, public=False)
            made.append(name)
    return made


# ------------------------------------------------------------------ storage


def rootCollection(creator: Optional[dict] = None) -> dict:
    found = Collection().findOne({'name': COLLECTION_NAME})
    if found is None:
        found = Collection().createCollection(
            COLLECTION_NAME, creator=creator or _anyAdmin(), public=False,
            description='Janus-M border reads (JA7): seeds, uploads and accepted reads. '
                        'Separate from SegQueue.', reuseExisting=True)
    return found


def _folder(name, creator=None):
    return Folder().createFolder(rootCollection(creator), name, parentType='collection',
                                 public=False, creator=creator or _anyAdmin(),
                                 reuseExisting=True)


def seedsFolder(creator=None):
    return _folder(SEEDS_FOLDER, creator)


def readsFolder(creator=None):
    return _folder(READS_FOLDER, creator)


def checkSeedsFolder(creator=None):
    """Blank cases' check seeds (JA66). Private: no group is ever given access."""
    return _folder(CHECK_SEEDS_FOLDER, creator)


def incomingFolder(creator=None):
    """The one place readers may write: their uploads, before /submit."""
    folder = _folder(INCOMING_FOLDER, creator)
    group = Group().findOne({'name': READER_GROUP})
    if group is not None:
        has = any(e.get('id') == group['_id'] and e.get('level', -1) >= AccessType.WRITE
                  for e in (folder.get('access') or {}).get('groups', []))
        if not has:
            folder = Folder().setGroupAccess(folder, group, level=AccessType.WRITE, save=True)
    return folder


def hashStoredFile(file: dict) -> str:
    digest = hashlib.sha256()
    for chunk in File().download(file, headers=False)():
        digest.update(chunk)
    return digest.hexdigest()


def clientProtocolFrom(clientProtocol):
    if clientProtocol not in (None, ''):
        return clientProtocol
    try:
        import cherrypy

        return cherrypy.request.headers.get(protocol.PROTOCOL_HEADER)
    except Exception:  # pragma: no cover - outside a request
        return None


def checkClientProtocol(clientProtocol) -> None:
    try:
        protocol.check_client_protocol(clientProtocolFrom(clientProtocol))
    except protocol.ProtocolError as exc:
        refuse(exc.code, exc.message, status=426, **exc.detail)


# --------------------------------------------------------------- CT geometry


def ctWorldBounds(case):
    """``(lo, hi)``: the world (RAS, mm) bounding box of a case's CT, voxel edges
    included, from its header alone; cached on the case. None when the CT is not a
    NIfTI file (JA67's lesion-point check then cannot run)."""
    if case.get('ctWorldBounds'):
        return case['ctWorldBounds']
    from janusm_reads import niftihead

    from .models import JanusMCase

    file = File().load(case['ctFileId'], force=True)
    if file is None:
        return None
    raw = b''.join(File().download(file, headers=False,
                                   endByte=niftihead.HEADER_READ_BYTES)())
    bounds = niftihead.world_bounds(raw)
    if bounds is None:
        return None
    bounds = [list(bounds[0]), list(bounds[1])]
    JanusMCase().collection.update_one({'_id': case['_id']},
                                       {'$set': {'ctWorldBounds': bounds}})
    return bounds
