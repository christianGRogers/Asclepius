"""Shared helpers: roles, storage layout, refusals, and server-side hashing."""

import hashlib

from girder.constants import AccessType
from girder.exceptions import RestException
from girder.models.collection import Collection
from girder.models.file import File
from girder.models.folder import Folder
from girder.models.group import Group
from girder.models.user import User
from segqueue import protocol
from segqueue.checksum import CHUNK_BYTES

from .constants import (
    ANNOTATOR_GROUP,
    CASES_FOLDER,
    COLLECTION_NAME,
    GOLD_FOLDER,
    INCOMING_FOLDER,
    REVIEWER_GROUP,
    SUBMISSIONS_FOLDER,
)


def refuse(code, message, status=400, **detail):
    """Raise a refusal the Slicer client can act on rather than merely display.

    Girder puts the structured payload in ``extra`` and the text in ``message``;
    ``segqueue.protocol.parse_error`` knows how to unwrap both, so the extension
    can distinguish "the queue is empty, try later" from "you already hold a
    case" without matching on English.
    """
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
    """Site admins review by right; nobody has to remember to add them."""
    return bool(user and (user.get('admin') or isInGroup(user, REVIEWER_GROUP)))


def isAnnotator(user):
    return bool(user and (user.get('admin') or isInGroup(user, ANNOTATOR_GROUP)))


def requireAnnotator(user):
    if not isAnnotator(user):
        refuse('not_an_annotator',
               'Your account is not in the annotator group. Ask the project '
               'admin to add you.', status=403)
    return user


def requireReviewer(user):
    if not isReviewer(user):
        refuse('not_a_reviewer', 'You do not have reviewer access.', status=403)
    return user


# --------------------------------------------------------- storage layout


def rootCollection(creator=None):
    """The ``SegQueue`` collection, created on first use.

    Public is False: the data is de-identified, but "de-identified" is not
    "publish it", and an accidentally world-readable CT archive is not a mistake
    worth risking for the sake of one boolean.
    """
    collection = Collection().findOne({'name': COLLECTION_NAME})
    if collection is None:
        collection = Collection().createCollection(
            COLLECTION_NAME,
            creator=creator,
            description='Case pool, submissions and gold standards for the '
                        'SegQueue annotation platform.',
            public=False,
            reuseExisting=True,
        )
    return collection


def _folder(name, creator=None):
    collection = rootCollection(creator)
    return Folder().createFolder(
        collection, name, parentType='collection', public=False,
        creator=creator, reuseExisting=True,
    )


def casesFolder(creator=None):
    return _folder(CASES_FOLDER, creator)


def goldFolder(creator=None):
    return _folder(GOLD_FOLDER, creator)


def submissionsFolder(creator=None):
    return _folder(SUBMISSIONS_FOLDER, creator)


def incomingFolder(creator=None):
    """Where clients upload before calling /submit.

    Separate from ``submissions`` so that an abandoned or rejected upload never
    sits among accepted work looking like part of the dataset. Nothing downstream
    ever reads from it, and ``maintenance.sweepIncoming`` discards whatever is
    left here for longer than ``INCOMING_MAX_AGE_SECONDS``.

    The annotator group gets WRITE here and nowhere else. That is the whole
    reason this folder exists as a distinct object: Girder's chunked uploader
    needs write access on a parent folder, and the only safe place to grant that
    to thirty undergraduates is a drop box whose contents no downstream step
    trusts.
    """
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
    """Create the two role groups if they do not exist.

    Idempotent, and called on every plugin load, because the alternative is a
    fresh deployment where the first annotator's login fails with a message
    about a group nobody was told to create.

    Returns [] and creates nothing when there is no admin to own the groups yet.
    That case is not hypothetical: on a brand-new deployment the plugin loads
    before anyone has registered, and Girder needs a creator for a group. Raising
    here would deadlock the install -- the server would refuse to start, so
    nobody could create the first account, so the server would keep refusing to
    start. The groups get made on the next load instead, or by the first call
    that needs them.
    """
    owner = creator or _anyAdmin()
    if owner is None:
        return []

    made = []
    for name, description in (
        (ANNOTATOR_GROUP, 'May be assigned SegQueue cases to segment.'),
        (REVIEWER_GROUP, 'May review and approve or reject SegQueue submissions.'),
    ):
        if Group().findOne({'name': name}) is None:
            Group().createGroup(name, creator=owner,
                                description=description, public=False)
            made.append(name)
    return made


def _anyAdmin():
    """Some admin to own the bootstrap objects. Girder requires a creator."""
    return User().findOne({'admin': True})


# ------------------------------------------------------- server-side hashing


def hashStoredFile(file, chunkBytes=CHUNK_BYTES):
    """SHA-256 over a file already in an assetstore, without buffering it.

    The client sends the digest it computed; this recomputes it from the bytes
    that actually arrived. Trusting the client's number would verify only that
    the client can repeat itself.
    """
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
               'Tell the project admin -- this case needs re-ingesting.',
               status=500)
    return file


def loadOwnAssignment(assignmentModel, assignmentId, user):
    """Load an assignment and refuse unless it belongs to the caller."""
    assignment = assignmentModel.load(assignmentId, force=True)
    if assignment is None:
        refuse('no_such_assignment', 'No such assignment.', status=404)
    if assignment['userId'] != user['_id'] and not user.get('admin'):
        refuse('not_your_assignment',
               'That case is assigned to someone else.', status=403)
    return assignment


def checkClientProtocol(clientProtocol):
    """Translate the shared version check into a Girder refusal."""
    try:
        protocol.check_client_protocol(clientProtocol)
    except protocol.ProtocolError as exc:
        refuse(exc.code, str(exc), status=426, **exc.detail)


def grantRead(model, doc, user):
    """Let a user read a document they legitimately own a stake in."""
    model.setUserAccess(doc, user, level=AccessType.READ, save=True)
    return doc
