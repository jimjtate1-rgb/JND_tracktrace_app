"""
Register an air-cargo status subscription so the provider pushes FSU updates to
our webhook. Air has no single standard subscription endpoint, so the request
body is generic — adjust to your provider's API.

    python manage.py air_subscribe --callback-url https://<host>/api/feeds/air/webhook/ --awb 160-22334454
"""
import re

import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create an air-cargo status subscription (provider -> our webhook)."

    def add_arguments(self, parser):
        parser.add_argument("--callback-url", required=True)
        parser.add_argument("--awb", required=True)
        parser.add_argument("--secret", default=settings.AIR_WEBHOOK_SECRET)

    def handle(self, *args, **o):
        if not settings.AIR_FEED_BASE_URL or not settings.AIR_FEED_API_KEY:
            raise CommandError("Set AIR_FEED_BASE_URL and AIR_FEED_API_KEY in .env first.")
        body = {"callbackUrl": o["callback_url"], "awbNumber": re.sub(r"[\s-]", "", o["awb"])}
        if o["secret"]:
            body["secret"] = o["secret"]
        headers = {
            settings.AIR_FEED_API_KEY_HEADER or "API-Key": settings.AIR_FEED_API_KEY,
            "Content-Type": "application/json", "Accept": "application/json",
        }
        try:
            resp = requests.post(f"{settings.AIR_FEED_BASE_URL.rstrip('/')}/subscriptions",
                                 json=body, headers=headers, timeout=20)
        except requests.RequestException as ex:
            raise CommandError(f"Subscription request failed: {ex}")
        if resp.status_code >= 400:
            raise CommandError(f"Provider returned HTTP {resp.status_code}: {resp.text[:300]}")
        self.stdout.write(self.style.SUCCESS("Air subscription created:"))
        self.stdout.write(resp.text[:1000])
        self.stdout.write(self.style.WARNING("\nStore any returned secret in AIR_WEBHOOK_SECRET."))
