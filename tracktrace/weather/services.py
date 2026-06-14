"""
Weather integration (OpenWeatherMap).

Mirrors the original cost-control design: only destinations of shipments still
in transit are refreshed, and a given city is refreshed at most once every two
hours. If WEATHER_API_KEY is unset, fetching is skipped gracefully.
"""
from datetime import timedelta

import requests
from django.conf import settings
from django.utils import timezone

from tracktrace.weather.models import Weather

OWM_URL = "https://api.openweathermap.org/data/2.5/weather"


def update_weather_data(city: str, country: str):
    """Fetch current weather for a city and upsert a Weather row. Returns it (or None)."""
    api_key = settings.WEATHER_API_KEY
    if not api_key or not city:
        return None

    response = requests.get(
        OWM_URL, params={"q": f"{city},{country}", "appid": api_key}, timeout=10
    )
    if response.status_code != 200:
        return None

    data = response.json()
    weather, _ = Weather.objects.update_or_create(
        city=city,
        country=country,
        defaults={
            "temperature": data["main"]["temp"],
            "wind_speed": data["wind"]["speed"],
            "description": (data.get("weather") or [{}])[0].get("description", ""),
        },
    )
    return weather


def get_weather():
    """
    Periodic entrypoint (called by the Celery task).

    For every non-terminal shipment, refresh destination weather if it is stale
    (>2h) or missing, then link the Weather row back to the shipment.
    """
    from tracktrace.traceapi.models import TERMINAL_STATUSES, Shipment

    shipments = Shipment.objects.exclude(status__in=TERMINAL_STATUSES)
    refreshed = set()

    for shipment in shipments:
        city = shipment.destination_city or shipment.destination_port
        country = shipment.destination_country
        key = (city, country)

        existing = Weather.objects.filter(city=city, country=country).first()
        is_stale = existing is None or (timezone.now() - existing.updated_at) > timedelta(hours=2)

        if is_stale and key not in refreshed:
            update_weather_data(city, country)
            refreshed.add(key)

        weather = Weather.objects.filter(city=city, country=country).first()
        if weather is not None and shipment.weather_id != weather.id:
            Shipment.objects.filter(id=shipment.id).update(weather=weather)
