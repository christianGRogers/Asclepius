"""SegQueue14: the pooled-volume, 4-class SegQueue (D23, D25), as a Girder 5 plugin.

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

import logging
import os

from girder.plugin import GirderPlugin

logger = logging.getLogger(__name__)

__version__ = '0.1.0'

#: Set to any non-empty value to keep the plugin installed but not mounted --
#: the fastest rollback there is: set it, restart Girder, and /segqueue14 is gone
#: while SegQueue carries on. See DEPLOY.md.
DISABLE_ENV = 'SEGQUEUE14_DISABLE'
#: Set to re-raise a load failure instead of logging it (for testing a deploy).
STRICT_ENV = 'SEGQUEUE14_STRICT'


class SegQueue14Plugin(GirderPlugin):
    """Mounts ``/segqueue14``.

    Everything is imported inside ``load`` and a failure there is logged rather
    than raised: Girder loads every installed plugin at startup and stops if one
    raises, so a broken SegQueue14 install must not be able to take the live
    SegQueue down with it. This module itself imports nothing but Girder's plugin
    base, for the same reason -- Girder imports it to read the entry point before
    any plugin loads.
    """

    DISPLAY_NAME = 'SegQueue14'

    def load(self, info):
        if os.environ.get(DISABLE_ENV):
            logger.warning('SegQueue14 is installed but disabled (%s is set); '
                           '/segqueue14 is not mounted.', DISABLE_ENV)
            return
        try:
            mount(info)
        except Exception:
            logger.exception('SegQueue14 failed to load; /segqueue14 is not mounted. '
                             'The rest of Girder, including SegQueue, is unaffected.')
            if os.environ.get(STRICT_ENV):
                raise


def mount(info):
    """Register the settings, the routes and the groups."""
    from girder.constants import AccessType
    from girder.models.user import User

    try:
        import segqueue  # noqa: F401
        import segqueue14  # noqa: F401
    except ImportError as exc:
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

    queue = QueueResource14()
    ReviewResource14().attachTo(queue)
    AdminResource14().attachTo(queue)
    info['apiRoot'].segqueue14 = queue
    User().exposeFields(level=AccessType.ADMIN, fields={QUOTA_FIELD})
    ensureGroups()
