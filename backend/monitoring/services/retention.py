import logging

from django.conf import settings
from django.utils import timezone

from core.alert_rules import CAMERA_ERROR_ALERT_TYPES, DEVICE_ERROR_ALERT_TYPES
from monitoring.models import CameraAlert, CameraAlertType, DeviceAlert, DeviceHeartbeat

logger = logging.getLogger(__name__)

# rows deleted per query, so big cleanups don't lock the database for long
DEFAULT_BATCH_SIZE = 5000


# deletes every row of a queryset in small batches and returns how many were deleted
def _delete_in_batches(queryset, batch_size):
    model = queryset.model
    total_deleted = 0

    while True:
        stale_ids = list(queryset.order_by("id").values_list("id", flat=True)[:batch_size])

        if not stale_ids:
            break

        deleted_count, _ = model.objects.filter(id__in=stale_ids).delete()
        total_deleted += deleted_count

        if len(stale_ids) < batch_size:
            break

    return total_deleted


# deletes heartbeats older than the retention days and returns how many were deleted
def delete_old_heartbeats(retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    if retention_days is None:
        retention_days = settings.HEARTBEAT_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    total_deleted = _delete_in_batches(DeviceHeartbeat.objects.filter(received_at__lt=cutoff), batch_size)

    if total_deleted:
        logger.info("Heartbeat cleanup: deleted %s heartbeat(s) older than %s days.", total_deleted, retention_days)

    return total_deleted


# deletes resolved alerts older than the retention days and returns how many were deleted
# active alerts are never touched because they have no resolved_at
def delete_old_resolved_alerts(retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    if retention_days is None:
        retention_days = settings.ALERT_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    total_deleted = 0

    for model in (DeviceAlert, CameraAlert):
        stale = model.objects.filter(active=False, resolved_at__lt=cutoff)
        total_deleted += _delete_in_batches(stale, batch_size)

    if total_deleted:
        logger.info("Alert cleanup: deleted %s resolved alert(s) older than %s days.", total_deleted, retention_days)

    return total_deleted


# resolves error alerts that were not reported again in the stale hours and returns how many
# offline and health alerts are skipped because an explicit status message already resolves them
def resolve_stale_alerts(stale_after_hours: int | None = None) -> int:
    if stale_after_hours is None:
        stale_after_hours = settings.ALERT_STALE_HOURS

    now = timezone.now()
    cutoff = now - timezone.timedelta(hours=stale_after_hours)

    resolved = DeviceAlert.objects.filter(
        active=True, alert_type__in=DEVICE_ERROR_ALERT_TYPES, last_seen_at__lt=cutoff
    ).update(active=False, resolved_at=now)

    resolved += CameraAlert.objects.filter(
        active=True, alert_type__in=CAMERA_ERROR_ALERT_TYPES, last_seen_at__lt=cutoff
    ).update(active=False, resolved_at=now)

    if resolved:
        logger.info(
            "Stale alert cleanup: auto-resolved %s alert(s) not re-reported on MQTT in over %s hour(s).",
            resolved,
            stale_after_hours,
        )

    return resolved


# deletes detections older than the retention days and returns how many were deleted
# detections never become inactive, so they have their own time based cleanup
def delete_old_detections(retention_days: int | None = None, batch_size: int = DEFAULT_BATCH_SIZE) -> int:
    if retention_days is None:
        retention_days = settings.DETECTION_RETENTION_DAYS

    cutoff = timezone.now() - timezone.timedelta(days=retention_days)
    stale = CameraAlert.objects.filter(alert_type=CameraAlertType.CAMERA_ALERT, created_at__lt=cutoff)
    total_deleted = _delete_in_batches(stale, batch_size)

    if total_deleted:
        logger.info("Detection cleanup: deleted %s detection(s) older than %s days.", total_deleted, retention_days)

    return total_deleted
