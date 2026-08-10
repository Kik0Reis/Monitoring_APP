"""
Heartbeat timeout monitoring.

This module checks devices that have stopped communicating.

The MQTT client receives messages and updates Device.last_seen.

This service periodically checks last_seen and determines whether
a device should now be considered OFFLINE.

The flow is:

    Device.last_seen
          ↓
    Calculate elapsed time
          ↓
    Compare with timeout
          ↓
    ONLINE → OFFLINE
          ↓
    Create DEVICE_OFFLINE alert
"""


from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from devices.models import Device, DeviceStatus

from monitoring.services.device_health import (
    create_offline_alert,
    update_device_status,
)


# ============================================================================
# Heartbeat timeout
# ============================================================================


DEFAULT_HEARTBEAT_TIMEOUT_SECONDS = 60


# ============================================================================
# Check a single device
# ============================================================================


@transaction.atomic
def check_device_timeout(
    device: Device,
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> Device:
    """
    Check whether a device has stopped communicating.

    A device is considered offline when:

        last_seen + timeout < current time

    If the device has never communicated:

        last_seen = None

    we do not automatically mark it offline here.

    This allows newly-created devices to remain UNKNOWN until the
    monitoring system has enough information to determine their state.
    """

    if now is None:
        now = timezone.now()

    # ------------------------------------------------------------------
    # A device that has never communicated remains UNKNOWN.
    # ------------------------------------------------------------------

    if device.last_seen is None:
        return device

    # ------------------------------------------------------------------
    # Calculate the time after which the heartbeat is considered expired.
    # ------------------------------------------------------------------

    timeout_delta = timedelta(
        seconds=timeout_seconds
    )

    expires_at = device.last_seen + timeout_delta

    # ------------------------------------------------------------------
    # The device is still within its heartbeat window.
    # ------------------------------------------------------------------

    if now <= expires_at:

        # If the device was previously ONLINE, keep it ONLINE.
        return device

    # ------------------------------------------------------------------
    # Heartbeat has expired.
    # ------------------------------------------------------------------

    if device.status != DeviceStatus.OFFLINE:

        update_device_status(
            device=device,
            new_status=DeviceStatus.OFFLINE,
        )

    # ------------------------------------------------------------------
    # Make sure there is an active offline alert.
    #
    # create_offline_alert() prevents duplicate active alerts.
    # ------------------------------------------------------------------

    create_offline_alert(device)

    return device


# ============================================================================
# Check all active devices
# ============================================================================


def check_all_device_timeouts(
    timeout_seconds: int = DEFAULT_HEARTBEAT_TIMEOUT_SECONDS,
    now=None,
) -> int:
    """
    Check all active devices for heartbeat expiration.

    Returns the number of devices currently considered OFFLINE.
    """

    if now is None:
        now = timezone.now()

    offline_count = 0

    devices = Device.objects.filter(
        active=True,
    )

    for device in devices:

        check_device_timeout(
            device=device,
            timeout_seconds=timeout_seconds,
            now=now,
        )

        # Refresh because check_device_timeout() may have changed
        # the status.
        device.refresh_from_db(
            fields=["status"],
        )

        if device.status == DeviceStatus.OFFLINE:
            offline_count += 1

    return offline_count

