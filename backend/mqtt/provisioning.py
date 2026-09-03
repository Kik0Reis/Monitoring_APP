"""
Auto-provisioning of the Country -> Customer -> Location -> Device tree
from MQTT topics.

Devices are resolved using the FULL path extracted from the topic
(country / client / installation / device_id), never a bare device_id
lookup. This matters because mqtt_identifier is only guaranteed unique
*within a location* — two different customers can legitimately both
have a device whose installer called it "01".

Anything created here is a guess based on untrusted network input
(anyone who can publish to the MQTT broker can trigger this), so every
newly created record is marked pending_review=True. It behaves exactly
like a normal record everywhere else in the app — pending_review is
purely a UI flag so a human can confirm it, rename it to something
meaningful, and (for devices) fill in its real serial number.
"""

import logging

from django.db import IntegrityError, transaction

from cameras.models import Camera
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceType
from locations.models import Location

logger = logging.getLogger(__name__)


def _resolve_by_mqtt_key(model, mqtt_key, lookup, name_field, defaults):
    """
    Shared get-or-create logic for models with both a unique `name` and a
    separately-unique `mqtt_key` (Customer, Location).

    A record with this name may already exist without an mqtt_key (e.g.
    created by hand through the UI before any MQTT traffic arrived for
    it). If we only searched by mqtt_key, get_or_create would try to
    insert a second row with the same name and crash on the unique
    (scope, name) constraint. So we check by name first and adopt that
    record instead of creating a duplicate.

    `lookup` is the queryset filter identifying the parent scope, e.g.
    {"country": country} for Customer or {"customer": customer} for
    Location.
    """

    existing = model.objects.filter(mqtt_key=mqtt_key, **lookup).first()
    if existing:
        return existing, False

    existing = model.objects.filter(
        **{name_field: mqtt_key, "mqtt_key__isnull": True}, **lookup
    ).first()
    if existing:
        existing.mqtt_key = mqtt_key
        existing.save(update_fields=["mqtt_key", "updated_at"])
        return existing, False

    try:
        with transaction.atomic():
            return (model.objects.create(mqtt_key=mqtt_key, **lookup, **defaults), True)
    except IntegrityError:
        # Lost a race with another request that created the same record
        # in between our checks above and our insert — just use theirs.
        return model.objects.get(mqtt_key=mqtt_key, **lookup), False


def resolve_device(
    *, country_code: str, client_key: str, installation_key: str, device_id: str
) -> Device | None:
    """
    Resolve the Device for an incoming MQTT message, auto-creating any
    missing Country/Customer/Location/Device along the way.

    Returns None (and logs a warning, mirroring the old "unknown device"
    behavior) if the device already exists but has been deliberately
    deactivated — a disabled device should not have messages processed
    for it, and should not be silently "resurrected" by MQTT traffic.
    """

    country = _resolve_country(country_code)
    customer = _resolve_customer(country, client_key)
    location = _resolve_location(customer, installation_key)
    device = _resolve_device(location, device_id)

    if not device.active:
        logger.warning(
            "Ignoring MQTT message for deactivated device: "
            "country=%s client=%s installation=%s device_id=%s",
            country_code,
            client_key,
            installation_key,
            device_id,
        )
        return None

    return device


def _resolve_country(country_code: str) -> Country:
    code = country_code.strip().upper()[:2]

    country, created = Country.objects.get_or_create(
        code=code, defaults={"name": f"Unverified ({code})", "pending_review": True}
    )

    if created:
        logger.warning("Auto-created Country from MQTT: code=%s (pending review)", code)

    return country


def _resolve_customer(country: Country, client_key: str) -> Customer:
    key = client_key.strip()

    customer, created = _resolve_by_mqtt_key(
        Customer,
        mqtt_key=key,
        lookup={"country": country},
        name_field="name",
        defaults={"name": key, "pending_review": True},
    )

    if created:
        logger.warning(
            "Auto-created Customer from MQTT: country=%s key=%s (pending review)",
            country.code,
            key,
        )

    return customer


def _resolve_location(customer: Customer, installation_key: str) -> Location:
    key = installation_key.strip()

    location, created = _resolve_by_mqtt_key(
        Location,
        mqtt_key=key,
        lookup={"customer": customer},
        name_field="name",
        defaults={"name": key, "pending_review": True},
    )

    if created:
        logger.warning(
            "Auto-created Location from MQTT: customer=%s key=%s (pending review)",
            customer.name,
            key,
        )

    return location


def _resolve_device(location: Location, device_id: str) -> Device:
    identifier = device_id.strip()

    try:
        device, created = Device.objects.get_or_create(
            location=location,
            mqtt_identifier=identifier,
            defaults={
                "name": identifier,
                # No serial number is available from MQTT. This placeholder
                # is guaranteed unique (location.id is globally unique) and
                # obviously a placeholder, so it's easy to spot in the UI
                # and replace with the device's real serial number later.
                "serial_number": f"AUTO-{location.id}-{identifier}",
                "device_type": DeviceType.EDGE,
                "pending_review": True,
            },
        )
    except IntegrityError:
        # A manually-created device at this location already has the
        # name we'd want to use (unique_device_name_per_location), even
        # though its mqtt_identifier doesn't match. Fall back to it
        # rather than crashing MQTT processing.
        device = Device.objects.get(location=location, name=identifier)
        created = False

    if created:
        logger.warning(
            "Auto-created Device from MQTT: location=%s identifier=%s (pending review)",
            location.name,
            identifier,
        )

    return device


def resolve_camera(
    device: Device, camera_identifier: str, name: str | None = None, channel: int = 1
) -> Camera:
    """
    Resolve the Camera for an entry in a device's ".../cameras" status
    list, auto-creating it if this device hasn't reported this camera
    before.

    Scoped to `device` (Camera.camera_identifier is already only unique
    per-device in the schema, so no collision risk here the way there was
    with Device.mqtt_identifier).
    """

    identifier = camera_identifier.strip()

    camera, created = Camera.objects.get_or_create(
        device=device,
        camera_identifier=identifier,
        channel=channel,
        defaults={
            "name": (name or identifier).strip() or identifier,
            "pending_review": True,
        },
    )

    if created:
        logger.warning(
            "Auto-created Camera from MQTT: device=%s identifier=%s (pending review)",
            device.name,
            identifier,
        )

    return camera
