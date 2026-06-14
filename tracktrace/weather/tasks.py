from celery import shared_task

from tracktrace.weather.services import get_weather


@shared_task
def weather_update():
    """Refresh weather for all undelivered shipments. Scheduled every 2 hours."""
    get_weather()
