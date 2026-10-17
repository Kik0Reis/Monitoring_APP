# database model of a customer

from django.db import models

from core.models import TimeStampedModel
from countries.models import Country


# a company whose sites we monitor, it belongs to one country
class Customer(TimeStampedModel):
    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    # matches the client part of an mqtt topic, never changed after creation so renaming cannot break the match
    mqtt_key = models.CharField(max_length=150, blank=True, null=True)

    # True for customers created automatically from mqtt
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"], name="unique_customer_name_per_country"
            ),
            models.UniqueConstraint(
                fields=["country", "mqtt_key"],
                condition=models.Q(mqtt_key__isnull=False),
                name="unique_customer_mqtt_key_per_country",
            ),
        ]

    # returns the customer name
    def __str__(self):
        return self.name
