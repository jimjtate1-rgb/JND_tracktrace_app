"""
Pull a shipment from a carrier feed and ingest it.

Ocean (DCSA Track & Trace v2) — needs DCSA_BASE_URL + DCSA_API_KEY:
    python manage.py pull_shipment --bol COSU6229185001 --scac COSU --carrier "COSCO Shipping"
    python manage.py pull_shipment --container CSNU6229185

Air (IATA Cargo-IMP FSU) — needs AIR_FEED_BASE_URL + AIR_FEED_API_KEY:
    python manage.py pull_shipment --awb 160-22334454 --carrier "Cathay Cargo"

Offline (parse a local payload, no network/key); provider auto-selected by reference:
    python manage.py pull_shipment --sample tracktrace/feeds/samples/dcsa_events_sample.json --bol COSU6229185001 --scac COSU --carrier "COSCO Shipping"
    python manage.py pull_shipment --sample tracktrace/feeds/samples/aircargo_fsu_sample.json --awb 160-22334454 --carrier "Cathay Cargo"
"""
import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError

from tracktrace.feeds.base import FeedError
from tracktrace.feeds.ingest import ingest_shipment
from tracktrace.feeds.registry import DEFAULT_PROVIDER_BY_REF, FEEDS, get_feed


class Command(BaseCommand):
    help = "Pull a shipment from a carrier feed (ocean DCSA or air FSU) and store it."

    def add_arguments(self, parser):
        parser.add_argument("--provider", default=None, help="dcsa | aircargo (auto by reference if omitted)")
        parser.add_argument("--bol", help="Bill of lading / transport document reference")
        parser.add_argument("--booking", help="Carrier booking reference")
        parser.add_argument("--container", help="Container (equipment) number")
        parser.add_argument("--awb", help="Air waybill number")
        parser.add_argument("--sample", help="Parse a local JSON payload instead of calling the API")
        parser.add_argument("--carrier", default="", help="Carrier display name to stamp on the shipment")
        parser.add_argument("--scac", default="", help="Carrier SCAC / IATA prefix to stamp")

    def handle(self, *args, **o):
        ref_type, reference = self._reference(o)
        provider = o["provider"] or DEFAULT_PROVIDER_BY_REF[ref_type]
        if provider not in FEEDS:
            raise CommandError(f"Unknown provider '{provider}'. Available: {', '.join(sorted(FEEDS))}.")

        try:
            if o["sample"]:
                normalized = self._from_sample(provider, o["sample"], ref_type, reference,
                                               o["carrier"], o["scac"])
            else:
                normalized = get_feed(provider).fetch(reference=reference, reference_type=ref_type)
                if o["carrier"]:
                    normalized.carrier_name = o["carrier"]
                if o["scac"]:
                    normalized.carrier_code = o["scac"]
        except FeedError as ex:
            raise CommandError(str(ex))

        shipment, created = ingest_shipment(normalized)
        verb = "Created" if created else "Updated"
        self.stdout.write(self.style.SUCCESS(
            f"{verb} {shipment} [{provider}] — {shipment.carrier_name or 'carrier ?'} · "
            f"{shipment.origin_code or '?'} → {shipment.destination_code or '?'} · "
            f"status '{shipment.get_status_display()}' · "
            f"{shipment.containers.count()} container(s) · {shipment.cargo.count()} cargo line(s) · "
            f"{shipment.events.count()} event(s)."
        ))

    def _reference(self, o):
        given = [(t, o[t]) for t in ("bol", "booking", "container", "awb") if o.get(t)]
        if len(given) != 1:
            raise CommandError("Provide exactly one of --bol, --booking, --container, or --awb.")
        return given[0]

    def _from_sample(self, provider, path, ref_type, reference, carrier, scac):
        p = Path(path)
        if not p.exists():
            raise CommandError(f"Sample file not found: {path}")
        payload = json.loads(p.read_text())
        return FEEDS[provider].parse_payload(
            payload, reference=reference, reference_type=ref_type,
            carrier_name=carrier, carrier_code=scac,
        )
