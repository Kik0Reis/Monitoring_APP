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

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["customer", "name"],
                name="unique_location_name_per_customer",
            ),
        ]

    def __str__(self):
        return self.name