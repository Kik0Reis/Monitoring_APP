from django.db import models
from core.models import TimeStampedModel

#Model for the country
# it has a name and a code (PT, US, etc) and it inherits from TimeStampedModel to have created_at and updated_at fields
class Country(TimeStampedModel):
    name = models.CharField(max_length=100)
    code = models.CharField(max_length=2, unique=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name