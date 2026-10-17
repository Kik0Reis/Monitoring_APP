# database model of a location

from django.db import models

from core.models import TimeStampedModel
from customers.models import Customer


# a physical site of a customer, with one or more devices
class Location(TimeStampedModel):
    customer = models.ForeignKey(Customer, on_delete=models.CASCADE, related_name="locations")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    # matches the installation part of an mqtt topic, empty when the location was created by hand
    mqtt_key = models.CharField(max_length=150, blank=True, null=True)

    # True for locations created automatically from mqtt
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

    # returns the location name
    def __str__(self):
        return self.name
