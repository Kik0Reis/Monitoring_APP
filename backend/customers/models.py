from django.db import models

from core.models import TimeStampedModel
from countries.models import Country


class Customer(TimeStampedModel):
    """A customer (a company we monitor sites for), scoped to one country."""

    country = models.ForeignKey(Country, on_delete=models.CASCADE, related_name="customers")
    name = models.CharField(max_length=150)
    description = models.TextField(blank=True)
    active = models.BooleanField(default=True)

    # matches the "{client}" segment of an MQTT topic, set once on
    # auto-create and never touched again so renaming in the UI can't
    # break matching or spawn a duplicate. blank if made by hand
    mqtt_key = models.CharField(max_length=150, blank=True, null=True)

    # set for customers auto-created from MQTT traffic, just a UI flag
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

    def __str__(self):
        return self.name
