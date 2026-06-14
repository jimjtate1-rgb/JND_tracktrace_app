"""
Probe TrackCargo and print the RAW JSON it returns, so the field mapping in
trackcargo.py can be locked to a real response.

    python manage.py trackcargo_probe --bol MEDUXXXXXXX
    python manage.py trackcargo_probe --awb 160-12345678

Needs TRACKCARGO_API_KEY set. Copy the printed JSON and send it over.
"""
import json

from django.core.management.base import BaseCommand, CommandError

from tracktrace.feeds.base import FeedError
from tracktrace.feeds.trackcargo import TrackCargoFeed


class Command(BaseCommand):
    help = "Create a TrackCargo order and dump the raw create + tracking JSON."

    def add_arguments(self, parser):
        parser.add_argument("--bol")
        parser.add_argument("--booking")
        parser.add_argument("--container")
        parser.add_argument("--awb")

    def handle(self, *args, **o):
        given = [(t, o[t]) for t in ("bol", "booking", "container", "awb") if o.get(t)]
        if len(given) != 1:
            raise CommandError("Provide exactly one of --bol, --booking, --container, --awb.")
        ref_type, reference = given[0]
        mode = "air" if ref_type == "awb" else "ocean"
        feed = TrackCargoFeed()
        if not feed.api_key:
            raise CommandError("Set TRACKCARGO_API_KEY first.")
        try:
            self.stdout.write(self.style.WARNING("Creating order..."))
            order_id = feed.create_order(reference, ref_type, mode)
            self.stdout.write(self.style.SUCCESS(f"order id: {order_id}"))
            self.stdout.write(self.style.WARNING("Fetching tracking (may be 'pending' on first call)..."))
            tracking = feed.get_tracking(order_id)
        except FeedError as ex:
            raise CommandError(str(ex))
        self.stdout.write("\n===== RAW TRACKING JSON (copy everything below) =====")
        self.stdout.write(json.dumps(tracking, indent=2, default=str))
        self.stdout.write("===== END =====")
