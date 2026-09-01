"""
Database retention / cleanup.

Devices can send a heartbeat every few seconds, so DeviceHeartbeat is by
far the fastest-growing table in the app. A device's *current* health is
always available on the Device row itself (status, last_seen, health_data),
so old heartbeats are only useful for a short historical window — we don't
need to keep them forever.

This module deletes heartbeats older than a configurable cutoff. It's
called periodically by the heartbeat_worker management command, and can
also be run on demand via `manage.py cleanup_heartbeats`.
"""

import logging

from django.conf import settings
from django.utils import timezone

from monitoring.models import DeviceHeartbeat

logger = logging.getLogger(__name__)

# Deleting millions of rows in one query can lock up SQLite/Postgres for a
# noticeable amount of time, so we delete in small batches instead.
DEFAULT_BATCH_SIZE = 5000


def delete_old_heartbeats(
    retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    """
    Delete DeviceHeartbeat rows older than `retention_days`.

    Returns the total number of rows deleted.
    """

    if retention_days is None:
        retention_days = settings.HEARTBEAT_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)

    total_deleted = 0

    while True:
        # Grab a batch of old row ids and delete just those. This keeps
        # each individual DELETE small and fast instead of taking one big
        # lock on the whole table.
        stale_ids = list(
            DeviceHeartbeat.objects.filter(received_at__lt=cutoff)
            .order_by("id")
            .values_list("id", flat=True)[:batch_size]
        )

        if not stale_ids:
            break

        deleted_count, _ = DeviceHeartbeat.objects.filter(id__in=stale_ids).delete()
        total_deleted += deleted_count

        if len(stale_ids) < batch_size:
            break

    if total_deleted:
        logger.info(
            "Heartbeat cleanup: deleted %s heartbeat(s) older than %s days.",
            total_deleted,
            retention_days,
        )

    return total_deleted
