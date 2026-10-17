# database model of a country

from django.db import models

from core.models import TimeStampedModel


# a country with a two letter code (PT, US, ...)
class Country(TimeStampedModel):
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True)

    # True for countries created automatically from mqtt
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    # returns the country name
    def __str__(self):
        return self.name
