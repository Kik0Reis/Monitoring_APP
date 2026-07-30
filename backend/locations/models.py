from django.db import models
from core.models import TimeStampedModel
from customers.models import Customer


# Model for the location
# it has a name, a description, an active status and a foreign key to the customer model

class Location(TimeStampedModel):
    customer = models.ForeignKey(
        Customer,
        on_delete=models.CASCADE,
        related_name="locations",
    )

    name = models.CharField(max_length=150)

    description = models.TextField(
        blank=True,
    )

    active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name