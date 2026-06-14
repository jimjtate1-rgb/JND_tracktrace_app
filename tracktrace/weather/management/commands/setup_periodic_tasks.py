"""
Register the Celery-beat schedule that refreshes shipment weather every 2 hours.

    python manage.py setup_periodic_tasks
"""
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils.timezone import get_default_timezone_name

from django_celery_beat.models import CrontabSchedule, IntervalSchedule, PeriodicTask

from tracktrace.weather.tasks import weather_update


class Command(BaseCommand):
    help = "Set up Celery beat periodic tasks (weather refresh every 2 hours)."

    @transaction.atomic
    def handle(self, *args, **options):
        self.stdout.write("Resetting periodic tasks and schedules...")
        PeriodicTask.objects.all().delete()
        IntervalSchedule.objects.all().delete()
        CrontabSchedule.objects.all().delete()

        # Every 2 hours, on the hour: https://crontab.guru/#0_*/2_*_*_*
        cron, _ = CrontabSchedule.objects.get_or_create(
            minute="0",
            hour="*/2",
            day_of_week="*",
            day_of_month="*",
            month_of_year="*",
            timezone=get_default_timezone_name(),
        )
        PeriodicTask.objects.create(
            name="Refresh shipment weather (every 2h)",
            task=weather_update.name,
            crontab=cron,
            enabled=True,
        )
        self.stdout.write(self.style.SUCCESS(f"Registered '{weather_update.name}' every 2 hours."))
