from django.db import models

from core.models import TimeStampedModel
from countries.models import Country


# Model representing a customer.
# Each customer belongs to a country and can own multiple locations.
class Customer(TimeStampedModel):
    # Country that owns the customer.
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="customers",
    )

    # Customer name.
    name = models.CharField(
        max_length=150,
    )

    # Optional description.
    description = models.TextField(
        blank=True,
    )

    # Indicates whether the customer is active.
    active = models.BooleanField(
        default=True,
    )

    # Stable key used to match this customer against the "{client}"
    # segment of an MQTT topic (aiaction/{country}/{client}/...).
    #
    # This is deliberately separate from `name`: `name` is meant to be
    # human-edited freely (e.g. renamed to a nicer display name), while
    # `mqtt_key` is set once when the customer is first auto-created from
    # MQTT and never changes — so renaming a customer in the UI can't
    # break MQTT matching or cause a duplicate to be auto-created later.
    # Manually-created customers leave this blank.
    mqtt_key = models.CharField(
        max_length=150,
        blank=True,
        null=True,
    )

    # True for customers auto-created from an MQTT topic that didn't match
    # any existing customer. Fully functional either way — this is just a
    # UI flag so a human can confirm/rename it.
    pending_review = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"],
                name="unique_customer_name_per_country",
            ),
            models.UniqueConstraint(
                fields=["country", "mqtt_key"],
                condition=models.Q(mqtt_key__isnull=False),
                name="unique_customer_mqtt_key_per_country",
            ),
        ]

    def __str__(self):
        return self.name
