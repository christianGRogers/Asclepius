"""SegQueue: case assignment, submission and QA workflow, as a Girder 5 plugin.

Girder supplies the parts of this system that are not interesting -- accounts,
tokens, groups, a REST framework, chunked resumable uploads, file storage across
pluggable assetstores, and an admin UI. This plugin adds only what is specific to
running a segmentation workforce: a case pool with atomic assignment, a lease
that expires, a review queue, and the sampling that decides who gets looked at.

Loaded through the ``girder.plugin`` entry point declared in ``pyproject.toml``.
"""

from girder.constants import AccessType
from girder.models.user import User
from girder.plugin import GirderPlugin

try:
    import segqueue  # noqa: F401
except ImportError as exc:  # pragma: no cover - a deployment error, not a code path
    raise ImportError(
        'girder-segqueue needs the `segqueue` package, which ships in the '
        'Asclepius repository under src/. Install the repository root before '
        'this plugin:\n'
        '    pip install /path/to/Asclepius\n'
        'It is deliberately not a declared dependency: the distribution that '
        'provides it is named `segtrain`, and an unrelated project already owns '
        'that name on PyPI.'
    ) from exc

from . import settings  # noqa: F401  (imported for its setting validators)
from .rest import AdminResource, QueueResource, ReviewResource
from .utils import ensureGroups

__version__ = '0.1.0'


class SegQueuePlugin(GirderPlugin):
    DISPLAY_NAME = 'SegQueue'

    def load(self, info):
        # One mount point. The reviewer and admin resources hang their routes
        # off the queue resource so that every path reads /segqueue/... and the
        # generated API docs show one section instead of three.
        queue = QueueResource()
        ReviewResource().attachTo(queue)
        AdminResource().attachTo(queue)
        info['apiRoot'].segqueue = queue

        # The per-user case cap lives on the Girder user document. Exposed to
        # admins only: an annotator seeing their own quota is fine, but it is
        # served to them through /segqueue/project with the remaining count
        # already worked out, which is the number they actually want.
        User().exposeFields(level=AccessType.ADMIN, fields={'segqueueQuota'})

        # Idempotent, and worth doing on every load: a fresh deployment whose
        # first annotator cannot log in because nobody created a group is a
        # miserable first ten minutes.
        ensureGroups()
