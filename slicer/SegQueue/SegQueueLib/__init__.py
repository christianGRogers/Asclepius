"""Support code for the SegQueue Slicer module.

Everything in here is free of Slicer, Qt and VTK imports on purpose. The module
file next door is the only place that touches Slicer's API, which means the
network client, the local cache and the self-updater -- the three parts most
likely to be wrong -- can be exercised by ordinary pytest on a laptop with no
Slicer installed.
"""

from .cache import CacheError, CaseCache, defaultRoot
from .client import SegQueueClient, SegQueueError
from .updater import UpdateError

__all__ = [
    "CaseCache",
    "CacheError",
    "SegQueueClient",
    "SegQueueError",
    "UpdateError",
    "defaultRoot",
]
