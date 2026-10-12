"""SegQueue14 REST resources, all under one ``/segqueue14`` prefix."""

from .admin import AdminResource14
from .queue import QueueResource14
from .review import ReviewResource14

__all__ = ["AdminResource14", "QueueResource14", "ReviewResource14"]
