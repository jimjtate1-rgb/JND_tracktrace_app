"""
Register a DCSA event subscription so the carrier pushes updates to our webhook.

    python manage.py dcsa_subscribe --callback-url https://your-host/api/feeds/dcsa/webhook/ \\
        --bol COSU6229185001

The carrier returns a subscriptionID (and, depending on the carrier, a shared
secret) — put the secret in DCSA_WEBHOOK_SECRET so inbound callbacks verify.
Exact request body varies by carrier/version; adjust as needed.
"""
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create a DCSA Track & Trace event subscription (carrier -> our webhook)."

    def add_arguments(self, parser):
        parser.add_argument("--callback-url", required=True)
        parser.add_argument("--bol")
        parser.add_argument("--booking")
        parser.add_argument("--container")
        parser.add_argument("--secret", default=settings.DCSA_WEBHOOK_SECRET,
                            help="Shared secret for HMAC-signing callbacks.")

    def handle(self, *args, **o):
        if not settings.DCSA_BASE_URL or not settings.DCSA_API_KEY:
            raise CommandError("Set DCSA_BASE_URL and DCSA_API_KEY in .env first.")

        body = {"callbackUrl": o["callback_url"]}
        if o["bol"]:
            body["transportDocumentReference"] = o["bol"]
        if o["booking"]:
            body["carrierBookingReference"] = o["booking"]
        if o["container"]:
            body["equipmentReference"] = o["container"]
        if o["secret"]:
            body["secret"] = o["secret"]

        headers = {
            settings.DCSA_API_KEY_HEADER or "API-Key": settings.DCSA_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            resp = requests.post(
                f"{settings.DCSA_BASE_URL.rstrip('/')}/event-subscriptions",
                json=body, headers=headers, timeout=20,
            )
        except requests.RequestException as ex:
            raise CommandError(f"Subscription request failed: {ex}")

        if resp.status_code >= 400:
            raise CommandError(f"Carrier returned HTTP {resp.status_code}: {resp.text[:300]}")

        self.stdout.write(self.style.SUCCESS("Subscription created:"))
        self.stdout.write(resp.text[:1000])
        self.stdout.write(self.style.WARNING(
            "\nStore any returned secret in DCSA_WEBHOOK_SECRET so callbacks verify."
        ))
