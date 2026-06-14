"""
Persist a NormalizedShipment into the Django models.

Two modes:
  * replace_events=True  (polling: GET returns the full history) -> replace timeline.
  * replace_events=False (webhook deltas) -> merge new events, never regress status.

Idempotent either way: re-pulling/re-pushing the same data does not duplicate rows.
"""
from __future__ import annotations

from django.db import transaction

from tracktrace.feeds.base import NormalizedShipment
from tracktrace.traceapi.models import CargoItem, Container, Shipment, TrackingEvent

# Higher = further along the journey. Used so webhook deltas only advance status.
STATUS_RANK = {
    "booked": 0, "gate-in": 1, "loaded": 2, "departed": 3, "in-transit": 4,
    "transshipment": 4, "arrived": 5, "discharged": 6, "available": 7,
    "out-for-delivery": 8, "delivered": 9, "delayed": 4,
}


def _match_shipment(n: NormalizedShipment) -> Shipment | None:
    if n.bill_of_lading:
        return Shipment.objects.filter(mode=n.mode, bill_of_lading=n.bill_of_lading).first()
    if n.booking_number:
        return Shipment.objects.filter(mode=n.mode, booking_number=n.booking_number).first()
    if n.awb_number:
        return Shipment.objects.filter(mode=n.mode, awb_number=n.awb_number).first()
    if n.containers:
        return Shipment.objects.filter(
            mode=n.mode, containers__container_number=n.containers[0].container_number
        ).first()
    return None


@transaction.atomic
def ingest_shipment(n: NormalizedShipment, *, replace_events: bool = True) -> tuple[Shipment, bool]:
    """Create or update a Shipment from normalized feed data. Returns (shipment, created)."""
    shipment = _match_shipment(n)
    created = shipment is None
    if shipment is None:
        shipment = Shipment(mode=n.mode)

    # Status: full snapshot adopts the feed status; a delta only advances it.
    if replace_events:
        status = n.status or shipment.status or "booked"
    else:
        cur = STATUS_RANK.get(shipment.status, -1)
        new = STATUS_RANK.get(n.status, -1)
        status = n.status if new > cur else (shipment.status or "booked")

    fields = {
        "mode": n.mode,
        "status": status,
        "carrier_name": n.carrier_name or shipment.carrier_name,
        "carrier_code": n.carrier_code or shipment.carrier_code,
        "bill_of_lading": n.bill_of_lading or shipment.bill_of_lading,
        "booking_number": n.booking_number or shipment.booking_number,
        "awb_number": n.awb_number or shipment.awb_number,
        "origin_port": n.origin_port or shipment.origin_port,
        "origin_code": n.origin_code or shipment.origin_code,
        "origin_country": n.origin_country or shipment.origin_country,
        "destination_port": n.destination_port or shipment.destination_port,
        "destination_code": n.destination_code or shipment.destination_code,
        "destination_country": n.destination_country or shipment.destination_country,
        "destination_city": n.destination_city or shipment.destination_city,
        "vessel_name": n.vessel_name or shipment.vessel_name,
        "voyage_number": n.voyage_number or shipment.voyage_number,
        "flight_number": n.flight_number or shipment.flight_number,
        "etd": n.etd or shipment.etd,
        "eta": n.eta or shipment.eta,
    }
    for k, v in fields.items():
        setattr(shipment, k, v)
    if created:
        shipment.shipper_name = shipment.shipper_name or "—"
        shipment.consignee_name = shipment.consignee_name or "—"
    shipment.save()

    # Containers (upsert by number).
    for c in n.containers:
        Container.objects.update_or_create(
            shipment=shipment, container_number=c.container_number,
            defaults={"container_type": c.container_type, "seal_number": c.seal_number},
        )

    # Cargo (only when the feed supplied it; ocean T&T feeds don't).
    if n.cargo:
        shipment.cargo.all().delete()
        CargoItem.objects.bulk_create([
            CargoItem(shipment=shipment, description=c.description, hs_code=c.hs_code,
                      pieces=c.pieces, weight_kg=c.weight_kg)
            for c in n.cargo
        ])

    # Events.
    if replace_events:
        shipment.events.all().delete()
        new_events = n.events
    else:
        def _key(e):
            return (e.code, e.location_code, int(e.event_datetime.timestamp()))
        existing = {_key(e) for e in shipment.events.all()}
        new_events = [e for e in n.events if _key(e) not in existing]
    TrackingEvent.objects.bulk_create([
        TrackingEvent(
            shipment=shipment, code=e.code, description=e.description, location=e.location,
            location_code=e.location_code, vessel_or_flight=e.vessel_or_flight,
            event_datetime=e.event_datetime, is_estimated=e.is_estimated,
        )
        for e in new_events
    ])
    return shipment, created
