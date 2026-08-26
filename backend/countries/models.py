from django.db import models

from core.models import TimeStampedModel


# Model representing a country.
# Each country has a unique name and a unique ISO-like code (e.g. PT, US).
# The model inherits from TimeStampedModel to automatically include
# created_at and updated_at fields.
class Country(TimeStampedModel):
    # Country name.
    name = models.CharField(
        max_length=100,
        unique=True,
    )

    # Two-letter country code.
    code = models.CharField(
        max_length=2,
        unique=True,
    )

    # True for countries auto-created from an MQTT topic that didn't match
    # any existing country. The record is fully functional either way —
    # this is just a UI flag so a human can confirm/rename it, since it
    # was created from untrusted network input rather than deliberately.
    pending_review = models.BooleanField(
        default=False,
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Country"
        verbose_name_plural = "Countries"

    def __str__(self):
        return self.name