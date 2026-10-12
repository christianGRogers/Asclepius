"""SegQueue14: the 14-class, prelabel-correction SegQueue, as a Girder 5 plugin.

Loads **beside** the live ``segqueue`` plugin in the same Girder and shares
nothing writable with it:

=====================  ==========================  ==============================
                       live (girder_segqueue)       this plugin
=====================  ==========================  ==============================
plugin name            ``segqueue``                 ``segqueue14``
REST prefix            ``/segqueue``                ``/segqueue14``
Girder collection      ``SegQueue``                 ``SegQueue14``
Mongo collections      ``segqueue_*``               ``segqueue14_*``
settings               ``segqueue.*``               ``segqueue14.*``
groups                 ``segqueue-annotators`` ...  ``segqueue14-annotators`` ...
user quota field       ``segqueueQuota``            ``segqueue14Quota``
wire protocol          1                            14
=====================  ==========================  ==============================

The one thing it reads from the live project is the CT volumes (and heart masks
and ImageCAS-X references) already stored in the ``SegQueue`` collection, which
SegQueue14 cases reference by file id. Nothing here writes to, moves or deletes
any of those files. Uninstalling this plugin leaves the live project exactly as
it was; see DEPLOY.md.
"""

from girder.constants import AccessType
from girder.models.user import User
from girder.plugin import GirderPlugin

try:
    import segqueue  # noqa: F401
    import segqueue14  # noqa: F401
except ImportError as exc:  # pragma: no cover - a deployment error
    raise ImportError(
        'girder-segqueue14 needs the `segqueue` and `segqueue14` packages, which '
        'ship in the Asclepius repository under src/. Install the repository root '
        '(from a checkout that contains src/segqueue14) before this plugin:\n'
        '    pip install /path/to/Asclepius\n'
        '    pip install "/path/to/Asclepius/server/girder_segqueue14[scoring]"'
    ) from exc

from . import settings  # noqa: F401  (registers the segqueue14.* settings)
from .constants import QUOTA_FIELD
from .rest import AdminResource14, QueueResource14, ReviewResource14
from .utils import ensureGroups

__version__ = '0.1.0'


class SegQueue14Plugin(GirderPlugin):
    DISPLAY_NAME = 'SegQueue14'

    def load(self, info):
        queue = QueueResource14()
        ReviewResource14().attachTo(queue)
        AdminResource14().attachTo(queue)
        info['apiRoot'].segqueue14 = queue
        User().exposeFields(level=AccessType.ADMIN, fields={QUOTA_FIELD})
        ensureGroups()
