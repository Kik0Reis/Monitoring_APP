# creates the country, customer, location, device and camera of an mqtt topic when they do not exist

import logging

from django.db import IntegrityError, transaction

from cameras.models import Camera
from countries.models import Country
from customers.models import Customer
from devices.models import Device, DeviceType
from locations.models import Location

logger = logging.getLogger(__name__)


# gets or creates a record that has a unique name and a unique mqtt_key
def _resolve_by_mqtt_key(model, mqtt_key, lookup, name_field, defaults):
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
        # another process created it first, use that one
        return model.objects.get(mqtt_key=mqtt_key, **lookup), False


# finds the device of an mqtt message, creating it when it does not exist
def resolve_device(
    *, country_code: str, client_key: str, installation_key: str, device_id: str
) -> Device | None:
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


# gets or creates the country of the topic
def _resolve_country(country_code: str) -> Country:
    code = country_code.strip().upper()[:2]

    country, created = Country.objects.get_or_create(
        code=code, defaults={"name": f"Unverified ({code})", "pending_review": True}
    )

    if created:
        logger.warning("Auto-created Country from MQTT: code=%s (pending review)", code)

    return country


# gets or creates the customer of the topic
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


# gets or creates the location of the topic
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


# gets or creates the device of the topic
def _resolve_device(location: Location, device_id: str) -> Device:
    identifier = device_id.strip()

    try:
        device, created = Device.objects.get_or_create(
            location=location,
            mqtt_identifier=identifier,
            defaults={
                "name": identifier,
                # mqtt has no serial number, so use a unique placeholder that is easy to find and replace
                "serial_number": f"AUTO-{location.id}-{identifier}",
                "device_type": DeviceType.EDGE,
                "pending_review": True,
            },
        )
    except IntegrityError:
        # a manually created device with this name already exists here, use it instead of failing
        device = Device.objects.get(location=location, name=identifier)
        created = False

    if created:
        logger.warning(
            "Auto-created Device from MQTT: location=%s identifier=%s (pending review)",
            location.name,
            identifier,
        )

    return device


# finds the camera of an entry in the device camera list, creating it when needed
def resolve_camera(
    device: Device, camera_identifier: str, name: str | None = None, channel: int = 1
) -> Camera:
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
