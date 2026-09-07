"""Case notes: a per-case message thread the whole project can read.

Keyed by case rather than by assignment, and append-only. Both choices are the
point of the feature.

**Per case** because the value is continuity across people. A case that comes
back for rework is handled by a different annotator from the one who first drew
it, judged by a reviewer who saw neither, and the fact worth carrying between
them -- "the RCA ostium is behind a stent, the seed mask is wrong from slice
180" -- belongs to the *case*. Attached to an assignment it would vanish the
moment the assignment did.

**Append-only** because a shared editable field loses one person's text the
instant two people have the case open, and loses attribution always. A remark
from a reviewer and the same words from a first-week annotator are not the same
claim, and the person deciding whether to trust a segmentation needs to know
which they are reading.

Nothing here is deleted. A note that turns out to be wrong is answered by
another note; an audit that finds a bad batch of segmentations needs the
conversation that surrounded them, not a tidied version of it.
"""

import datetime

from girder.constants import AccessType
from girder.exceptions import ValidationException
from girder.models.model_base import AccessControlledModel
from segqueue import protocol


class Note(AccessControlledModel):
    def initialize(self):
        self.name = 'segqueue_note'
        self.ensureIndices([
            # The only query that matters: this case, oldest first.
            ([('caseId', 1), ('created', 1)], {}),
            'authorId',
        ])
        self.exposeFields(level=AccessType.READ, fields={
            '_id', 'caseId', 'authorId', 'author', 'text', 'created', 'system',
        })

    def validate(self, doc):
        doc['text'] = protocol.clean_note(doc.get('text'))
        if not doc['text']:
            raise ValidationException('A note cannot be empty.', 'text')
        if not doc.get('caseId'):
            raise ValidationException('A note must belong to a case.', 'caseId')
        doc['author'] = (doc.get('author') or '').strip() or 'unknown'
        doc.setdefault('system', False)
        return doc

    # ------------------------------------------------------------- writing

    def createNote(self, caseId, user, text, system=False):
        """Append one note. ``user`` may be None only for system notes."""
        return self.save({
            'caseId': caseId,
            'authorId': user['_id'] if user else None,
            'author': displayName(user) if user else 'SegQueue',
            'text': text,
            'system': bool(system),
            'created': datetime.datetime.now(datetime.timezone.utc),
        })

    def systemNote(self, caseId, text):
        """A note the server wrote. Never fails a request that triggered it.

        Called from the middle of submit and review, where the note is a nicety
        and the transaction around it is not: a thread that lost one line is a
        far better outcome than a rejected submission that the annotator has to
        redo because the note insert raised.
        """
        try:
            return self.createNote(caseId, None, text, system=True)
        except Exception:
            return None

    # ------------------------------------------------------------- reading

    def forCase(self, caseId, limit=None):
        """The thread, oldest first, capped at the newest ``limit`` notes.

        Sorted newest-first in the query and reversed here, so the cap keeps the
        *recent* end of a long thread rather than its beginning.
        """
        limit = int(limit or protocol.NOTE_PAGE_SIZE)
        newest = list(self.find({'caseId': caseId}, sort=[('created', -1)], limit=limit))
        return list(reversed(newest))

    def countForCase(self, caseId):
        return self.collection.count_documents({'caseId': caseId})


def displayName(user):
    """What to show as the author. Login, because it is what people call it.

    Falls back through the names Girder might have. Never returns an empty
    string: an unattributed note in a thread people use to judge segmentations
    is worse than a slightly ugly one.
    """
    if not user:
        return 'SegQueue'
    login = (user.get('login') or '').strip()
    if login:
        return login
    full = ' '.join(p for p in (user.get('firstName'), user.get('lastName')) if p).strip()
    return full or str(user.get('_id') or 'unknown')
