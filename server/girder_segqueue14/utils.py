"""Roles, storage layout, refusals and hashing -- adapted from the live plugin's
``utils`` with SegQueue14's own groups, collection and protocol."""

import hashlib
from typing import NoReturn, Optional

from girder.constants import AccessType
from girder.exceptions import RestException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.user import User
from segqueue14 import plan as sqplan
from segqueue14 import protocol

from .constants import (
    ANNOTATOR_GROUP,
    COLLECTION_NAME,
    INCOMING_FOLDER,
    PRELABELS_FOLDER,
    REVIEWER_GROUP,
    SUBMISSIONS_FOLDER,
)


def refuse(code: str, message: str, status: int = 400, **detail) -> NoReturn:
    """Raise a structured refusal the SegQueue14 client can act on."""
    raise RestException(message, code=status,
                        extra=protocol.error_body(code, message, **detail))


# ------------------------------------------------------------------- roles


def isInGroup(user: Optional[dict], groupName: str) -> bool:
    """Membership by group name. False for no user, and for a group that does
    not exist yet (before ``ensureGroups`` has had an admin to own it)."""
    if not user:
        return False
    group = Group().findOne({'name': groupName})
    if group is None:
        return False
    return group['_id'] in (user.get('groups') or [])


def isReviewer(user: Optional[dict]) -> bool:
    return bool(user and (user.get('admin') or isInGroup(user, REVIEWER_GROUP)))


def isAnnotator(user: Optional[dict]) -> bool:
    return bool(user and (user.get('admin') or isInGroup(user, ANNOTATOR_GROUP)))


def fullName(user: dict) -> str:
    """``First Last`` from a Girder user, '' when it has neither."""
    return f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()


def requireAnnotator(user: Optional[dict]) -> dict:
    """The user, or a 403 ``not_an_annotator`` refusal."""
    if not isAnnotator(user):
        refuse('not_an_annotator',
               'Your account is not in the SegQueue14 annotator group '
               f'({ANNOTATOR_GROUP}). Ask the project admin to add you.', status=403)
    return user


def requireReviewer(user: Optional[dict]) -> dict:
    """The user, or a 403 ``not_a_reviewer`` refusal."""
    if not isReviewer(user):
        refuse('not_a_reviewer', 'You do not have SegQueue14 reviewer access.', status=403)
    return user


# --------------------------------------------------------- storage layout


def rootCollection(creator: Optional[dict] = None) -> dict:
    """The ``SegQueue`` collection (D36), created on first use. Private."""
    collection = Collection().findOne({'name': COLLECTION_NAME})
    if collection is None:
        collection = Collection().createCollection(
            COLLECTION_NAME,
            creator=creator or _anyAdmin(),
            description='The SegQueue annotation project: CT volumes (cases/), '
                        'seeds, and SegQueue14 prelabels, submissions and '
                        'scratch uploads.',
            public=False,
            reuseExisting=True,
        )
    return collection


def _folder(name, creator=None, parent=None, parentType='collection'):
    parent = parent if parent is not None else rootCollection(creator)
    return Folder().createFolder(
        parent, name, parentType=parentType, public=False,
        creator=creator or _anyAdmin(), reuseExisting=True,
    )


def submissionsFolder(creator: Optional[dict] = None) -> dict:
    return _folder(SUBMISSIONS_FOLDER, creator)


def prelabelsFolder(version: str, creator: Optional[dict] = None) -> dict:
    """``SegQueue/prelabels/<model_version>/``."""
    version = sqplan.validate_model_version(version)
    top = _folder(PRELABELS_FOLDER, creator)
    return _folder(version, creator, parent=top, parentType='folder')


def incomingFolder(creator: Optional[dict] = None) -> dict:
    """The drop box clients upload into before /submit. The SegQueue14 annotator
    group gets WRITE here and nowhere else (see the live plugin for why)."""
    folder = _folder(INCOMING_FOLDER, creator)
    group = Group().findOne({'name': ANNOTATOR_GROUP})
    if group is not None and not _hasGroupWrite(folder, group):
        folder = Folder().setGroupAccess(
            folder, group, level=AccessType.WRITE, save=True)
    return folder


def _hasGroupWrite(folder, group):
    for entry in (folder.get('access') or {}).get('groups', []):
        if entry.get('id') == group['_id'] and entry.get('level', -1) >= AccessType.WRITE:
            return True
    return False


def ensureGroups(creator: Optional[dict] = None) -> list[str]:
    """Create the two SegQueue14 groups if they do not exist. Idempotent; a no-op
    until an admin exists to own them."""
    owner = creator or _anyAdmin()
    if owner is None:
        return []
    made = []
    for name, description in (
        (ANNOTATOR_GROUP, 'May be assigned SegQueue14 cases to annotate.'),
        (REVIEWER_GROUP, 'May review SegQueue14 submissions.'),
    ):
        if Group().findOne({'name': name}) is None:
            Group().createGroup(name, creator=owner, description=description,
                                public=False)
            made.append(name)
    return made


def _anyAdmin():
    return User().findOne({'admin': True})


# ------------------------------------------------------- server-side hashing


def hashStoredFile(file: dict) -> str:
    digest = hashlib.sha256()
    stream = File().download(file, headers=False)
    for chunk in stream():
        digest.update(chunk)
    return digest.hexdigest()


def fileForCase(case: dict) -> dict:
    """The case's CT file document, or a 500 ``case_file_missing`` refusal: a
    case whose volume has gone is a storage fault, not a client error."""
    file = File().load(case['fileId'], force=True)
    if file is None:
        refuse('case_file_missing',
               f"The volume for case {case['name']!r} is missing from storage. "
               'Tell the project admin.', status=500)
    return file


def loadOwnAssignment(assignmentModel, assignmentId, user: dict) -> dict:
    assignment = assignmentModel.load(assignmentId, force=True)
    if assignment is None:
        refuse('no_such_assignment', 'No such assignment.', status=404)
    if assignment['userId'] != user['_id'] and not user.get('admin'):
        refuse('not_your_assignment', 'That case is assigned to someone else.', status=403)
    return assignment


def requireCaseInvolvement(assignmentModel, caseId, user: dict) -> bool:
    if isReviewer(user):
        return True
    held = assignmentModel.collection.count_documents(
        {'caseId': caseId, 'userId': user['_id']}, limit=1)
    if not held:
        refuse(protocol.ERR_NOT_YOUR_CASE,
               'You can only read or add notes on cases you have worked on.', status=403)
    return True


def clientProtocolFrom(clientProtocol) -> Optional[str]:
    """The version from the request parameter, else from the request header."""
    if clientProtocol not in (None, ''):
        return clientProtocol
    try:
        import cherrypy

        return cherrypy.request.headers.get(protocol.PROTOCOL_HEADER)
    except Exception:  # pragma: no cover - outside a request
        return None


def checkClientProtocol(clientProtocol) -> None:
    """Refuse (426) a client that is not a current SegQueue14 module."""
    try:
        protocol.check_client_protocol(clientProtocolFrom(clientProtocol))
    except protocol.ProtocolError as exc:
        refuse(exc.code, str(exc), status=426, **exc.detail)
