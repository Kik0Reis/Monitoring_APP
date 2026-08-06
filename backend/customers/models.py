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

    class Meta:
        ordering = ["name"]

        constraints = [
            models.UniqueConstraint(
                fields=["country", "name"],
                name="unique_customer_name_per_country",
            ),
        ]

    def __str__(self):
        return self.name