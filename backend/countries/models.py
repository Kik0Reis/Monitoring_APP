from django.db import models

from core.models import TimeStampedModel


class Country(TimeStampedModel):
    """A country a customer belongs to, keyed by a two-letter code (PT, US, ...)."""

    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=2, unique=True)

    # set for countries auto-created from MQTT traffic, just a UI flag
    pending_review = models.BooleanField(default=False)

    class Meta:
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name
