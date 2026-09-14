from django.db import models

from core.models import TimeStampedModel
from customers.models import Customer


class Location(TimeStampedModel):
    """A physical site belonging to a customer, containing one or more devices."""

    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    # matches the "{installation}" segment of an MQTT topic, separate from
    # the human-editable name (see Customer.mqtt_key). blank if made by hand
    mqtt_key = models.CharField(max_length=150, blank=True, null=True)

    # set for locations auto-created from MQTT traffic, just a UI flag
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["customer", "name"], name="unique_location_name_per_customer"
            ),
            models.UniqueConstraint(
                fields=["customer", "mqtt_key"],
                condition=models.Q(mqtt_key__isnull=False),
                name="unique_location_mqtt_key_per_customer",
            ),
        ]

    def __str__(self):
        return self.name
