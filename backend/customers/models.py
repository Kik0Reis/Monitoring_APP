from django.db import models
from core.models import TimeStampedModel
from countries.models import Country


# Model for the customer 
# it has a name, a description, an active status and a foreign key to the country model
class Customer(TimeStampedModel):
    country = models.ForeignKey(
        Country,
        on_delete=models.CASCADE,
        related_name="customers",
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