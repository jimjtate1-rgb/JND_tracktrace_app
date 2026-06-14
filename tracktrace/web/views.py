import re
from datetime import datetime

from django.shortcuts import redirect, render

from tracktrace.traceapi.carriers import carriers as list_carriers, detect_carrier
from tracktrace.traceapi.validators import is_valid_awb, is_valid_container_number
from tracktrace.web.airlines import airlines_sorted, lookup
from tracktrace.web.shipping_lines import lines_sorted, lookup_line
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


def aircargo_view(request):
    """Air-cargo router: detect the airline from the AWB's 3-digit prefix and
    forward to that airline's cargo tracking (with a manual picker fallback)."""
    awb = (request.GET.get("awb") or "").strip()
    airline_iata = (request.GET.get("airline") or "").strip()
    airlines = airlines_sorted()

    if airline_iata:  # manual pick from the list
        for a in airlines:
            if a["iata"] == airline_iata:
                return redirect(a["url"])

    ctx = {"awb": awb, "airlines": airlines, "error": None, "warn": None,
           "prefix": "", "go_url": "", "go_name": ""}
    if awb:
        digits = re.sub(r"\D", "", awb)
        if len(digits) < 3:
            ctx["error"] = "Enter an AWB like 160-12345675 (3-digit airline prefix + 8 digits)."
        else:
            prefix = digits[:3]
            ctx["prefix"] = prefix
            hit = lookup(prefix)
            bad_check = len(digits) >= 11 and not is_valid_awb(digits[:11])
            if hit and not bad_check:
                return redirect(hit[2])
            if hit and bad_check:
                ctx["warn"] = (f"That AWB's check digit doesn't validate (possible typo), "
                               f"but prefix {prefix} is {hit[0]}.")
                ctx["go_url"], ctx["go_name"] = hit[2], hit[0]
            else:
                ctx["error"] = f"Airline for prefix {prefix} isn't in the list yet — pick it below."
    return render(request, "web/aircargo.html", ctx)


def ocean_view(request):
    """Ocean router: detect the shipping line from the first 4 letters of a
    container or B/L number and forward to that line's tracking (with a picker)."""
    num = (request.GET.get("num") or "").strip()
    scac = (request.GET.get("line") or "").strip().upper()
    lines = lines_sorted()

    if scac:  # manual pick from the list
        for l in lines:
            if l["scac"] == scac:
                return redirect(l["url"])

    ctx = {"num": num, "lines": lines, "error": None, "warn": None,
           "prefix": "", "go_url": "", "go_name": ""}
    if num:
        cleaned = re.sub(r"[^A-Za-z0-9]", "", num).upper()
        if len(cleaned) < 4 or not cleaned[:4].isalpha():
            ctx["error"] = "Enter a container (MSKU1234567) or B/L number starting with the line's 4-letter code."
        else:
            prefix = cleaned[:4]
            ctx["prefix"] = prefix
            hit = lookup_line(prefix)
            is_container = bool(re.fullmatch(r"[A-Z]{4}\d{7}", cleaned))
            bad_check = is_container and not is_valid_container_number(cleaned)
            if hit and not bad_check:
                return redirect(hit["url"])
            if hit and bad_check:
                ctx["warn"] = (f"That container's check digit doesn't validate (possible typo), "
                               f"but prefix {prefix} is {hit['name']}.")
                ctx["go_url"], ctx["go_name"] = hit["url"], hit["name"]
            else:
                ctx["error"] = f"Shipping line for code {prefix} isn't in the list yet — pick it below."
    return render(request, "web/ocean.html", ctx)
