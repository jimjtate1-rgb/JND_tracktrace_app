from django.db import models

from tracktrace.common.models import BaseModel


class Weather(BaseModel):
    """Current weather at a destination port/airport city."""

    city = models.CharField(max_length=120)
    country = models.CharField(max_length=80)
    temperature = models.FloatField()  # OpenWeatherMap default units (Kelvin)
    wind_speed = models.FloatField()
    description = models.CharField(max_length=120, blank=True)

    class Meta:
        unique_together = ("city", "country")

    def __str__(self):
        return f"{self.city}, {self.country}"
