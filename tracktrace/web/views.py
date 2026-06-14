from datetime import datetime

from django.shortcuts import render

from tracktrace.traceapi.carriers import carriers as list_carriers, detect_carrier
from tracktrace.traceapi.selectors import (
    get_traces,
    serialize_cargo,
    serialize_containers,
    serialize_events,
)

# How far along the origin -> destination rail each status sits (percent).
PROGRESS = {
    "booked": 4, "gate-in": 12, "loaded": 22, "departed": 30,
    "in-transit": 58, "transshipment": 62, "arrived": 86, "discharged": 91,
    "available": 95, "out-for-delivery": 98, "delivered": 100, "delayed": 55,
}
STATUS_CLASS = {
    "booked": "s-neutral", "gate-in": "s-neutral",
    "loaded": "s-move", "departed": "s-move", "in-transit": "s-move",
    "transshipment": "s-move", "out-for-delivery": "s-move", "delayed": "s-late",
    "arrived": "s-arr", "discharged": "s-arr", "available": "s-arr",
    "delivered": "s-done",
}


def _fmt_awb(digits: str) -> str:
    return f"{digits[:3]}-{digits[3:]}" if len(digits) == 11 else digits


def _fmt_dt(iso: str) -> str:
    dt = datetime.fromisoformat(iso)
    return dt.strftime("%d %b %Y, %H:%M UTC")


def _weather(raw):
    if not raw:
        return None
    c = raw["temperature"] - 273.15
    return {"c": round(c), "f": round(c * 9 / 5 + 32), "wind": raw["wind_speed"]}


def _via(shipment, events):
    """First milestone location that isn't the origin or destination port."""
    skip = {shipment.origin_port, shipment.destination_port}
    for e in events:
        if e["location"] and e["location"] not in skip:
            return {"port": e["location"], "code": e["location_code"]}
    return None


def _shipment_context(shipment):
    events = serialize_events(shipment)
    for e in events:
        e["display"] = _fmt_dt(e["datetime"])

    if shipment.mode == "ocean":
        ref = shipment.bill_of_lading or shipment.booking_number
        ref_kind = "Bill of Lading"
        conveyance = ("Vessel / Voyage",
                      f"{shipment.vessel_name} · {shipment.voyage_number}".strip(" ·"))
    else:
        ref = _fmt_awb(shipment.awb_number)
        ref_kind = "Air Waybill"
        conveyance = ("Flight", shipment.flight_number)

    return {
        "ref": ref,
        "ref_kind": ref_kind,
        "mode": shipment.mode,
        "status": shipment.status,
        "status_label": shipment.get_status_display(),
        "status_class": STATUS_CLASS.get(shipment.status, "s-neutral"),
        "progress": PROGRESS.get(shipment.status, 50),
        "origin": {"port": shipment.origin_port, "code": shipment.origin_code},
        "destination": {
            "port": shipment.destination_port,
            "code": shipment.destination_code,
            "country": shipment.destination_country,
            "city": shipment.destination_city or shipment.destination_port,
        },
        "via": _via(shipment, events),
        "carrier": {"name": shipment.carrier_name, "code": shipment.carrier_code},
        "conveyance_label": conveyance[0],
        "conveyance_value": conveyance[1],
        "etd": shipment.etd.strftime("%d %b %Y") if shipment.etd else "—",
        "eta": shipment.eta.strftime("%d %b %Y") if shipment.eta else "—",
        "shipper": {"name": shipment.shipper_name, "address": shipment.shipper_address},
        "consignee": {"name": shipment.consignee_name, "address": shipment.consignee_address},
        "containers": serialize_containers(shipment),
        "cargo": serialize_cargo(shipment),
        "weather": _weather(shipment.weather and {
            "temperature": shipment.weather.temperature,
            "wind_speed": shipment.weather.wind_speed,
        }),
        "events": events,
    }


def track_view(request):
    q = (request.GET.get("q") or "").strip()
    mode = request.GET.get("mode") or ""
    carrier = request.GET.get("carrier") or ""
    searched = "q" in request.GET or bool(mode) or bool(carrier)

    shipments, detected = [], None
    if searched:
        filters = {}
        if q:
            filters["search"] = q
            detected = detect_carrier(q)
        if mode:
            filters["mode"] = mode
        if carrier:
            filters["carrier"] = carrier
        qs = (
            get_traces(filters=filters)
            .select_related("weather")
            .prefetch_related("containers", "cargo", "events")
        )
        shipments = [_shipment_context(s) for s in qs]

    return render(request, "web/index.html", {
        "q": q,
        "mode": mode,
        "carrier": carrier,
        "searched": searched,
        "detected": detected,
        "shipments": shipments,
        "count": len(shipments),
        "carriers": list_carriers(with_scac_only=True),
        "modes": [("ocean", "Ocean"), ("air", "Air")],
    })
