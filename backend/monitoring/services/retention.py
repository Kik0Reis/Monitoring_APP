"""Deletes old heartbeats and resolved alerts so the DB doesn't grow forever.

DeviceHeartbeat grows fast (devices can heartbeat every few seconds), but
current health always lives on the Device row itself, so old heartbeats
only matter for a short historical window. Called periodically by
heartbeat_worker, or on demand via manage.py cleanup_heartbeats.
"""

import logging

from django.conf import settings
from django.utils import timezone

from monitoring.models import (
    AlertType,
    CameraAlert,
    CameraAlertType,
    DeviceAlert,
    DeviceHeartbeat,
)

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


# Alert types with no explicit "back to normal" MQTT message -- they're
# raised from a free-form issue/error report and only ever stop being
# re-reported once fixed, rather than sending a clear "resolved" signal.
# DEVICE_OFFLINE/DEVICE_HEALTH/CAMERA_OFFLINE are deliberately excluded:
# those already resolve immediately from an explicit status signal (see
# device_health.py / camera_monitor.py), so time-based staleness would
# only risk auto-resolving one that's still genuinely broken.
_STALE_ELIGIBLE_DEVICE_ALERT_TYPES = [AlertType.DEVICE_ERROR, AlertType.MQTT_ERROR, AlertType.SYSTEM_ERROR]
_STALE_ELIGIBLE_CAMERA_ALERT_TYPES = [CameraAlertType.CAMERA_ERROR]


def resolve_stale_alerts(stale_after_hours: int | None = None) -> int:
    """Auto-resolve active issue-style alerts no longer being re-reported on MQTT.

    create_device_issue_alert (and the equivalent for cameras) bumps
    last_seen_at every time the same issue is re-seen; if it hasn't been
    re-seen in `stale_after_hours`, it's treated as resolved. Returns how
    many were resolved.
    """

    if stale_after_hours is None:
        stale_after_hours = settings.ALERT_STALE_HOURS

    cutoff = timezone.now() - timezone.timedelta(hours=stale_after_hours)
    now = timezone.now()

    resolved = DeviceAlert.objects.filter(
        active=True,
        alert_type__in=_STALE_ELIGIBLE_DEVICE_ALERT_TYPES,
        last_seen_at__lt=cutoff,
    ).update(active=False, resolved_at=now)

    resolved += CameraAlert.objects.filter(
        active=True,
        alert_type__in=_STALE_ELIGIBLE_CAMERA_ALERT_TYPES,
        last_seen_at__lt=cutoff,
    ).update(active=False, resolved_at=now)

    if resolved:
        logger.info(
            "Stale alert cleanup: auto-resolved %s alert(s) not re-reported "
            "on MQTT in over %s hour(s).",
            resolved,
            stale_after_hours,
        )

    return resolved


def delete_old_detections(
    retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE
) -> int:
    """Delete CAMERA_ALERT (detection) rows older than retention_days.

    Detections never go active=False (see
    camera_monitor.process_camera_detection's docstring), so they'd never
    be touched by delete_old_resolved_alerts above -- this is their own,
    simpler, purely time-based retention window instead.
    """

    if retention_days is None:
        retention_days = settings.DETECTION_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)

    total_deleted = 0

    while True:
        stale_ids = list(
            CameraAlert.objects.filter(
                alert_type=CameraAlertType.CAMERA_ALERT, created_at__lt=cutoff
            )
            .order_by("id")
            .values_list("id", flat=True)[:batch_size]
        )

        if not stale_ids:
            break

        deleted_count, _ = CameraAlert.objects.filter(id__in=stale_ids).delete()
        total_deleted += deleted_count

        if len(stale_ids) < batch_size:
            break

    if total_deleted:
        logger.info(
            "Detection cleanup: deleted %s detection(s) older than %s days.",
            total_deleted,
            retention_days,
        )

    return total_deleted
