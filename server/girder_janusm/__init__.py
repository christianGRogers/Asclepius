"""The Janus-M border read queue (JA7), as a Girder 5 plugin beside SegQueue14.

It shares nothing writable with SegQueue14, and reads nothing of it:

=====================  ==========================  ==============================
                       SegQueue14                  this plugin
=====================  ==========================  ==============================
plugin name            ``segqueue14``              ``janusm``
REST prefix            ``/segqueue14``             ``/janusm``
Girder collection      ``SegQueue``                ``JanusM``
Mongo collections      ``segqueue14_*``            ``janusm_case``, ``janusm_read``
settings               ``segqueue14.*``            ``janusm.*``
groups                 ``segqueue14-annotators``   ``janusm-readers``,
                       ``segqueue14-reviewers``    ``janusm-admins``
wire protocol          SegQueue14 (16)             ``janusm-read`` 1
=====================  ==========================  ==============================

The CTs it serves are the ImageCAS-X train cases in the ``ImageCAS-X`` collection,
referenced by file id and never copied, moved or changed. Uninstalling the plugin
leaves SegQueue14 exactly as it was. See DEPLOY.md.
"""

import logging
import os

from girder.plugin import GirderPlugin

logger = logging.getLogger(__name__)

__version__ = '0.2.0'

#: Set to keep the plugin installed but not mounted.
DISABLE_ENV = 'JANUSM_DISABLE'
#: Set to re-raise a load failure instead of logging it.
STRICT_ENV = 'JANUSM_STRICT'


class JanusMPlugin(GirderPlugin):
    """Mounts ``/janusm``. A failure to load is logged, never raised, so a broken
    Janus-M install cannot stop Girder or SegQueue14."""

    DISPLAY_NAME = 'Janus-M reads'

    def load(self, info):
        if os.environ.get(DISABLE_ENV):
            logger.warning('Janus-M reads are installed but disabled (%s is set).',
                           DISABLE_ENV)
            return
        try:
            mount(info)
        except Exception:
            logger.exception('Janus-M reads failed to load; /janusm is not mounted. '
                             'The rest of Girder, including SegQueue14, is unaffected.')
            if os.environ.get(STRICT_ENV):
                raise


def mount(info):
    try:
        import janusm  # noqa: F401  (the JA12 guard and the JA6 freeze)
        import janusm_reads  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            'girder-janusm needs the `janusm` and `janusm_reads` packages from the '
            'Asclepius repository (src/). Install the repository root first.') from exc

    from . import utils  # noqa: F401  (registers the janusm.* settings)
    from .rest import JanusMResource

    info['apiRoot'].janusm = JanusMResource()
    utils.ensureGroups()
