"""Support code for the SegQueue14 Slicer module. Free of Slicer, Qt and VTK, so
the network client and the cache are tested by ordinary pytest.

Named ``SegQueue14Lib`` -- not ``SegQueueLib`` -- because Slicer puts every
scripted module's directory on one ``sys.path``: two packages of the same name
would shadow each other, and whichever module loaded second would run the other's
client against the wrong server routes.
"""

from .cache import CacheError, CaseCache, defaultRoot
from .client import SegQueue14Client, SegQueue14Error

__all__ = [
    "CaseCache",
    "CacheError",
    "SegQueue14Client",
    "SegQueue14Error",
    "defaultRoot",
]
