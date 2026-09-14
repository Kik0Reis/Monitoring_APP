"""Deletes old heartbeats and resolved alerts so the DB doesn't grow forever.

DeviceHeartbeat grows fast (devices can heartbeat every few seconds), but
current health always lives on the Device row itself, so old heartbeats
only matter for a short historical window. Called periodically by
heartbeat_worker, or on demand via manage.py cleanup_heartbeats.
"""

import logging

from django.conf import settings
from django.utils import timezone

from monitoring.models import CameraAlert, DeviceAlert, DeviceHeartbeat

logger = logging.getLogger(__name__)

# Deleting millions of rows in one query can lock up SQLite/Postgres for a
# noticeable amount of time, so we delete in small batches instead.
DEFAULT_BATCH_SIZE = 5000


def delete_old_heartbeats(
    retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    """Delete DeviceHeartbeat rows older than retention_days. Returns rows deleted."""

    if retention_days is None:
        retention_days = settings.HEARTBEAT_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)

    total_deleted = 0

    while True:
        # delete in id batches so we're not holding one big table lock
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


def delete_old_resolved_alerts(
    retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    """Delete resolved alerts (active=False) older than retention_days.

    Active alerts are never touched -- they always have resolved_at=None,
    so the resolved_at__lt=cutoff filter can't match them.
    """

    if retention_days is None:
        retention_days = settings.ALERT_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)

    total_deleted = 0

    for model in (DeviceAlert, CameraAlert):
        while True:
            stale_ids = list(
                model.objects.filter(active=False, resolved_at__lt=cutoff)
                .order_by("id")
                .values_list("id", flat=True)[:batch_size]
            )

            if not stale_ids:
                break

            deleted_count, _ = model.objects.filter(id__in=stale_ids).delete()
            total_deleted += deleted_count

            if len(stale_ids) < batch_size:
                break

    if total_deleted:
        logger.info(
            "Alert cleanup: deleted %s resolved alert(s) older than %s days.",
            total_deleted,
            retention_days,
        )

    return total_deleted
