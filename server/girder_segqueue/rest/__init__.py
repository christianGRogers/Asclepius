"""REST resources. All three mount under one ``/segqueue`` prefix.

Split by audience rather than by data model -- annotator, reviewer, admin --
because that is how the permission checks fall, and a file whose every handler
starts with the same role check is a file you can read quickly.
"""

from .admin import AdminResource
from .queue import QueueResource
from .review import ReviewResource

__all__ = ["AdminResource", "QueueResource", "ReviewResource"]
