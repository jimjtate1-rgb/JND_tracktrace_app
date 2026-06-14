from django.db.models import QuerySet

from tracktrace.traceapi.filters import TraceFilter
from tracktrace.traceapi.models import Shipment


def get_traces(*, filters=None) -> QuerySet[Shipment]:
    filters = filters or {}
    qs = Shipment.objects.all()
    return TraceFilter(filters, qs).qs


def serialize_containers(shipment) -> list[dict]:
    return [
        {
            "number": c.container_number,
            "type": c.container_type,
            "seal": c.seal_number,
        }
        for c in shipment.containers.all()
    ]


def serialize_cargo(shipment) -> list[dict]:
    return [
        {
            "description": item.description,
            "hs_code": item.hs_code,
            "pieces": item.pieces,
            "weight_kg": float(item.weight_kg),
        }
        for item in shipment.cargo.all()
    ]


def serialize_events(shipment) -> list[dict]:
    return [
        {
            "datetime": e.event_datetime.isoformat(),
            "code": e.code,
            "description": e.description,
            "location": e.location,
            "location_code": e.location_code,
            "vessel_or_flight": e.vessel_or_flight,
            "estimated": e.is_estimated,
        }
        for e in shipment.events.all()
    ]
