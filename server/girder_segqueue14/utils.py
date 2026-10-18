"""Roles, storage layout, refusals and hashing -- adapted from the live plugin's
``utils`` with SegQueue14's own groups, collection and protocol."""

import hashlib

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


def refuse(code, message, status=400, **detail):
    """Raise a structured refusal the SegQueue14 client can act on."""
    raise RestException(message, code=status,
                        extra=protocol.error_body(code, message, **detail))


# ------------------------------------------------------------------- roles


def isInGroup(user, groupName):
    if not user:
        return False
    group = Group().findOne({'name': groupName})
    if group is None:
        return False
    return group['_id'] in (user.get('groups') or [])


def isReviewer(user):
    return bool(user and (user.get('admin') or isInGroup(user, REVIEWER_GROUP)))


def isAnnotator(user):
    return bool(user and (user.get('admin') or isInGroup(user, ANNOTATOR_GROUP)))


def fullName(user):
    """``First Last`` from a Girder user, '' when it has neither."""
    return f"{user.get('firstName', '')} {user.get('lastName', '')}".strip()


def requireAnnotator(user):
    if not isAnnotator(user):
        refuse('not_an_annotator',
               'Your account is not in the SegQueue14 annotator group '
               f'({ANNOTATOR_GROUP}). Ask the project admin to add you.', status=403)
    return user


def requireReviewer(user):
    if not isReviewer(user):
        refuse('not_a_reviewer', 'You do not have SegQueue14 reviewer access.', status=403)
    return user


# --------------------------------------------------------- storage layout


def rootCollection(creator=None):
    """The ``SegQueue14`` collection, created on first use. Private."""
    collection = Collection().findOne({'name': COLLECTION_NAME})
    if collection is None:
        collection = Collection().createCollection(
            COLLECTION_NAME,
            creator=creator or _anyAdmin(),
            description='Prelabels, submissions and scratch uploads for the '
                        'SegQueue14 (4-class coronary) project. The CT '
                        'volumes are not here: cases reference the SegQueue '
                        "collection's files by id.",
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


def submissionsFolder(creator=None):
    return _folder(SUBMISSIONS_FOLDER, creator)


def prelabelsFolder(version, creator=None):
    """``SegQueue14/prelabels/<model_version>/``."""
    version = sqplan.validate_model_version(version)
    top = _folder(PRELABELS_FOLDER, creator)
    return _folder(version, creator, parent=top, parentType='folder')


def incomingFolder(creator=None):
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


def ensureGroups(creator=None):
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


def hashStoredFile(file):
    digest = hashlib.sha256()
    stream = File().download(file, headers=False)
    for chunk in stream():
        digest.update(chunk)
    return digest.hexdigest()


def fileForCase(case):
    file = File().load(case['fileId'], force=True)
    if file is None:
        refuse('case_file_missing',
               f"The volume for case {case['name']!r} is missing from storage. "
               'Tell the project admin.', status=500)
    return file


def loadOwnAssignment(assignmentModel, assignmentId, user):
    assignment = assignmentModel.load(assignmentId, force=True)
    if assignment is None:
        refuse('no_such_assignment', 'No such assignment.', status=404)
    if assignment['userId'] != user['_id'] and not user.get('admin'):
        refuse('not_your_assignment', 'That case is assigned to someone else.', status=403)
    return assignment


def requireCaseInvolvement(assignmentModel, caseId, user):
    if isReviewer(user):
        return True
    held = assignmentModel.collection.count_documents(
        {'caseId': caseId, 'userId': user['_id']}, limit=1)
    if not held:
        refuse(protocol.ERR_NOT_YOUR_CASE,
               'You can only read or add notes on cases you have worked on.', status=403)
    return True


def clientProtocolFrom(clientProtocol):
    """The version from the request parameter, else from the request header."""
    if clientProtocol not in (None, ''):
        return clientProtocol
    try:
        import cherrypy

        return cherrypy.request.headers.get(protocol.PROTOCOL_HEADER)
    except Exception:  # pragma: no cover - outside a request
        return None


def checkClientProtocol(clientProtocol):
    """Refuse (426) a client that is not a current SegQueue14 module."""
    try:
        protocol.check_client_protocol(clientProtocolFrom(clientProtocol))
    except protocol.ProtocolError as exc:
        refuse(exc.code, str(exc), status=426, **exc.detail)
