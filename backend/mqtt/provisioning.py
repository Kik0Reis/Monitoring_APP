"""Auto-creates Country/Customer/Location/Device records from MQTT topics.

Devices are looked up by the full topic path, not a bare device_id --
mqtt_identifier is only unique within a location, so two customers can
both have a device named "01" by their installer.

Anything auto-created here comes from untrusted network input (anyone who
can publish to the broker triggers this), so it's saved as pending_review=True.
It works exactly like any other record, that flag just tells the UI a human
should confirm/rename it.
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
    """Get-or-create for models with both a unique name and a unique mqtt_key.

    A record with this name might already exist without an mqtt_key (created
    by hand in the UI before any MQTT traffic showed up for it). Checking by
    mqtt_key alone would insert a duplicate and crash on the name constraint,
    so we check by name first and adopt that row instead.

    `lookup` scopes the search to the parent, e.g. {"country": country}.
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
        # someone else created it between our check and our insert, use theirs
        return model.objects.get(mqtt_key=mqtt_key, **lookup), False


def resolve_device(
    *, country_code: str, client_key: str, installation_key: str, device_id: str
) -> Device | None:
    """Find/auto-create the Device an MQTT message belongs to.

    Returns None if the device exists but was deliberately deactivated --
    a disabled device shouldn't get resurrected just because MQTT traffic
    still shows up for it.
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
                # MQTT has no serial number -- this placeholder is unique
                # (location.id is global) and obviously fake, easy to spot
                # and replace with the real one later
                "serial_number": f"AUTO-{location.id}-{identifier}",
                "device_type": DeviceType.EDGE,
                "pending_review": True,
            },
        )
    except IntegrityError:
        # a manually-created device at this location already has this name,
        # even though its mqtt_identifier differs -- fall back to it instead
        # of crashing MQTT processing
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
    """Find/auto-create the Camera for an entry in a device's cameras list.

    Scoped to `device` -- camera_identifier is only unique per-device, so
    there's no cross-customer collision risk like there was for devices.
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
