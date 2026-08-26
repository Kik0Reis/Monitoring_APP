from django.db import models

from core.models import TimeStampedModel
from customers.models import Customer


# Model representing a location.
# A location belongs to a customer and can contain multiple devices.
class Location(TimeStampedModel):
    # Customer that owns the location.
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    # Location name.
    name = models.CharField(
        max_length=150,
    )

    # Optional description.
    description = models.TextField(
        blank=True,
    )

    # Indicates whether the location is active.
    active = models.BooleanField(
        default=True,
    )

    # Stable key used to match this location against the "{installation}"
    # segment of an MQTT topic. See Customer.mqtt_key for why this is kept
    # separate from the human-editable `name`. Manually-created locations
    # leave this blank.
    mqtt_key = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    # True for locations auto-created from an MQTT topic that didn't match
    # any existing location. Fully functional either way — this is just a
    # UI flag so a human can confirm/rename it.
    pending_review = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["customer", "name"],
                name="unique_location_name_per_customer",
            ),
            models.UniqueConstraint(
                fields=["customer", "mqtt_key"],
                condition=models.Q(mqtt_key__isnull=False),
                name="unique_location_mqtt_key_per_customer",
            ),
        ]

    def __str__(self):
        return self.name
