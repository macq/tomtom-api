from __future__ import annotations

from enum import Enum


class QueueItemStatus(Enum):
    # I've added a IS_ and a HAS_ in order
    IS_WAITING = 'waiting'
    SUBMITTED = 'submitted'
    COMPLETED = 'completed'
    CANCELED = 'canceled'
    HAS_ERROR = 'error'
