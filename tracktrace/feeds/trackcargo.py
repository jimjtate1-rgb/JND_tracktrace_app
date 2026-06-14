"""
TrackCargo aggregator feed — ocean (BL / booking / container) + air (AWB) in one API.

TrackCargo is asynchronous: you POST to *create a tracking order* (returns an
orderId), then GET that order's tracking data. Ocean data refreshes ~daily, air
~2-hourly, and TrackCargo can also push updates to a webhook.

  Auth:     x-api-key header
  Base URL: https://api.trackcargo.com
  Create:   POST /api/v1/client-orders/create/tracking/{sea|air}
  Tracking: GET  /api/v1/client-orders/{orderId}/tracking

IMPORTANT: TrackCargo's exact request/response field names are not published (their
API reference is rendered client-side) and can't be verified without a live key, so
the request body and the response mapping below are written tolerantly and kept in
one place. The raw response is logged at INFO so we can lock the mapping to a real
payload — run `manage.py trackcargo_probe ...` once you have a key and send the output.
"""
from __future__ import annotations

import logging
import re
from datetime import datetime

import requests
from django.conf import settings

from tracktrace.feeds.base import (
    CarrierFeed,
    FeedAuthError,
    FeedConfigError,
    FeedError,
    FeedNotFound,
    NormalizedCargo,
    NormalizedContainer,
    NormalizedEvent,
    NormalizedShipment,
)

log = logging.getLogger("tracktrace.feeds.trackcargo")

# Map free-text TrackCargo statuses/events to our ShipmentStatus vocabulary by keyword.
_STATUS_KEYWORDS = [
    ("delivered", "delivered"), ("pod", "delivered"),
    ("out for delivery", "out-for-delivery"),
    ("available", "available"), ("notified", "available"), ("ready for pickup", "available"),
    ("discharg", "discharged"), ("unload", "discharged"), ("received from flight", "discharged"),
    ("arriv", "arrived"),
    ("transship", "transshipment"), ("transfer", "transshipment"),
    ("depart", "departed"), ("uplift", "departed"), ("vessel departure", "departed"),
    ("load", "loaded"), ("manifest", "loaded"),
    ("gate in", "gate-in"), ("received from shipper", "gate-in"), ("origin received", "gate-in"),
    ("book", "booked"), ("order created", "booked"),
    ("delay", "delayed"), ("hold", "delayed"), ("rolled", "delayed"),
]


def _first(d: dict, *keys, default=None):
    for k in keys:
        if isinstance(d, dict) and d.get(k) not in (None, ""):
            return d[k]
    return default


def _dt(value):
    if not value:
        return None
    if isinstance(value, (int, float)):
        try:
            return datetime.fromtimestamp(value if value < 1e12 else value / 1000)
        except (ValueError, OSError):
            return None
    s = str(value).strip().replace("Z", "+00:00")
    for fmt in (None,):  # ISO first
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d", "%d-%m-%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(value).strip(), fmt)
        except ValueError:
            continue
    return None


def _status_from_text(*texts) -> str:
    blob = " ".join(t for t in texts if t).lower()
    for needle, status in _STATUS_KEYWORDS:
        if needle in blob:
            return status
    return ""


class TrackCargoFeed(CarrierFeed):
    name = "trackcargo"
    supported_reference_types = ("bol", "booking", "container", "awb")

    def __init__(self):
        self.base_url = (settings.TRACKCARGO_BASE_URL or "https://api.trackcargo.com").rstrip("/")
        self.api_key = settings.TRACKCARGO_API_KEY
        self.timeout = 30

    def _headers(self):
        return {"x-api-key": self.api_key, "Content-Type": "application/json", "Accept": "application/json"}

    # --- public API -------------------------------------------------------
    def fetch(self, *, reference, reference_type) -> NormalizedShipment:
        if not self.api_key:
            raise FeedConfigError("Set TRACKCARGO_API_KEY (in Render → Environment) to use TrackCargo.")
        mode = "air" if reference_type == "awb" else "ocean"
        order_id = self.create_order(reference, reference_type, mode)
        payload = self.get_tracking(order_id)
        log.info("TrackCargo tracking payload (order %s): %s", order_id, payload)
        return self.parse_payload(payload, reference=reference, reference_type=reference_type)

    def create_order(self, reference, reference_type, mode) -> str:
        ref = re.sub(r"\s", "", str(reference))
        if mode == "air":
            url = f"{self.base_url}/api/v1/client-orders/create/tracking/air"
            body = {"awbNumber": re.sub(r"[-\s]", "", ref), "trackingNumber": ref}
        else:
            url = f"{self.base_url}/api/v1/client-orders/create/tracking/sea"
            # TrackCargo separates BL / booking / container; send the value plus a type hint.
            body = {"trackingNumber": ref, "referenceType": reference_type,
                    "blNumber" if reference_type == "bol" else
                    "bookingNumber" if reference_type == "booking" else
                    "containerNumber": ref}
        r = self._post(url, body)
        order_id = (_first(r, "orderId", "id", "order_id")
                    or _first(r.get("data", {}) if isinstance(r.get("data"), dict) else {}, "orderId", "id"))
        if not order_id:
            raise FeedError(f"TrackCargo did not return an order id (check field mapping): {str(r)[:300]}")
        return str(order_id)

    def get_tracking(self, order_id) -> dict:
        url = f"{self.base_url}/api/v1/client-orders/{order_id}/tracking"
        try:
            resp = requests.get(url, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as ex:
            raise FeedError(f"TrackCargo tracking request failed: {ex}") from ex
        if resp.status_code in (401, 403):
            raise FeedAuthError("TrackCargo rejected the API key.")
        if resp.status_code == 404:
            raise FeedNotFound(f"TrackCargo has no tracking yet for order {order_id}.")
        if resp.status_code >= 400:
            raise FeedError(f"TrackCargo tracking HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    def _post(self, url, body) -> dict:
        try:
            resp = requests.post(url, json=body, headers=self._headers(), timeout=self.timeout)
        except requests.RequestException as ex:
            raise FeedError(f"TrackCargo request failed: {ex}") from ex
        if resp.status_code in (401, 403):
            raise FeedAuthError("TrackCargo rejected the API key (check TRACKCARGO_API_KEY).")
        if resp.status_code >= 400:
            raise FeedError(f"TrackCargo HTTP {resp.status_code}: {resp.text[:300]}")
        return resp.json()

    # --- mapping (verify against a real payload) --------------------------
    @classmethod
    def extract_reference(cls, payload):
        """Derive (reference_type, reference) from a webhook payload."""
        d = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
        if not isinstance(d, dict):
            return None, None
        awb = _first(d, "awbNumber", "awb")
        if awb:
            return "awb", str(awb)
        bol = _first(d, "blNumber", "mblNumber", "billOfLading")
        if bol:
            return "bol", str(bol)
        bkg = _first(d, "bookingNumber", "carrierBookingReference")
        if bkg:
            return "booking", str(bkg)
        cnt = _first(d, "containerNumber")
        if cnt:
            return "container", str(cnt)
        conts = d.get("containers") or []
        if conts:
            c0 = conts[0]
            num = c0 if isinstance(c0, str) else _first(c0, "containerNumber", "number")
            if num:
                return "container", str(num)
        return None, None

    @classmethod
    def parse_payload(cls, payload, *, reference, reference_type, carrier_name="", carrier_code=""):
        d = payload.get("data") if isinstance(payload, dict) and isinstance(payload.get("data"), dict) else payload
        if not isinstance(d, dict):
            raise FeedNotFound("Unexpected TrackCargo payload (not an object).")
        mode = "air" if reference_type == "awb" else "ocean"

        carrier = d.get("carrier") if isinstance(d.get("carrier"), dict) else {}
        shp = NormalizedShipment(
            mode=mode, reference=reference, reference_type=reference_type,
            carrier_name=carrier_name or _first(d, "carrierName", "shippingLine", "airline") or _first(carrier, "name", default=""),
            carrier_code=carrier_code or _first(d, "scac", "carrierCode", "carrierScac") or _first(carrier, "scac", "code", default=""),
            bill_of_lading=_first(d, "blNumber", "mblNumber", "billOfLading") or (reference if reference_type == "bol" else ""),
            booking_number=_first(d, "bookingNumber", "carrierBookingReference") or (reference if reference_type == "booking" else ""),
            awb_number=re.sub(r"[-\s]", "", str(_first(d, "awbNumber", "awb") or (reference if reference_type == "awb" else ""))),
        )

        origin = d.get("origin") if isinstance(d.get("origin"), dict) else {}
        dest = d.get("destination") if isinstance(d.get("destination"), dict) else {}
        shp.origin_port = _first(d, "portOfLoading", "pol", "originPort") or _first(origin, "port", "name", "city", default="")
        shp.origin_code = _first(d, "polUnlocode", "originCode") or _first(origin, "unlocode", "code", default="")
        shp.origin_country = _first(origin, "country", default="")
        shp.destination_port = _first(d, "portOfDischarge", "pod", "destinationPort") or _first(dest, "port", "name", "city", default="")
        shp.destination_code = _first(d, "podUnlocode", "destinationCode") or _first(dest, "unlocode", "code", default="")
        shp.destination_country = _first(dest, "country", default="")
        shp.destination_city = _first(dest, "city", default="") or shp.destination_port
        shp.vessel_name = _first(d, "vesselName", "vessel", default="")
        shp.voyage_number = _first(d, "voyageNumber", "voyage", default="")
        shp.flight_number = _first(d, "flightNumber", "flight", default="")
        _etd = _dt(_first(d, "etd", "estimatedDeparture"))
        _eta = _dt(_first(d, "eta", "estimatedArrival"))
        shp.etd = _etd.date() if _etd else None
        shp.eta = _eta.date() if _eta else None

        # Containers (ocean)
        for c in (d.get("containers") or []):
            if isinstance(c, str):
                shp.containers.append(NormalizedContainer(container_number=c))
            elif isinstance(c, dict):
                num = _first(c, "containerNumber", "number", "equipmentReference")
                if num:
                    shp.containers.append(NormalizedContainer(
                        container_number=num,
                        container_type=_first(c, "containerType", "type", "isoCode", default=""),
                        seal_number=_first(c, "sealNumber", "seal", default=""),
                    ))

        # Events / milestones
        events_raw = d.get("events") or d.get("milestones") or d.get("trackingEvents") or d.get("movements") or []
        norm, best, best_rank = [], "", -1
        _RANK = {"booked": 0, "gate-in": 1, "loaded": 2, "departed": 3, "in-transit": 4, "transshipment": 4,
                 "arrived": 5, "discharged": 6, "available": 7, "out-for-delivery": 8, "delivered": 9, "delayed": 4}
        for ev in events_raw:
            if not isinstance(ev, dict):
                continue
            when = _dt(_first(ev, "timestamp", "eventDateTime", "date", "eventDate", "actualTime", "estimatedTime"))
            if when is None:
                continue
            desc = _first(ev, "description", "event", "eventName", "status", "statusName", default="Status update")
            loc = _first(ev, "location", "port", "locationName", "city", default="")
            loc_code = _first(ev, "unlocode", "locationCode", "portCode", default="")
            vf = _first(ev, "vessel", "flight", "vesselName", "flightNumber", "conveyance", default="")
            estimated = bool(_first(ev, "estimated", "isEstimated", default=False)) or \
                str(_first(ev, "eventType", "classifier", default="")).upper() in ("EST", "ESTIMATED", "PLN", "PLANNED")
            norm.append((when, NormalizedEvent(
                code=str(_first(ev, "code", "eventCode", "statusCode", default="") or "")[:24],
                description=desc, event_datetime=when, location=loc, location_code=loc_code,
                vessel_or_flight=vf, is_estimated=estimated)))
            st = _status_from_text(desc, _first(ev, "status", "statusName", default=""))
            if st and not estimated and _RANK.get(st, -1) > best_rank:
                best, best_rank = st, _RANK[st]

        norm.sort(key=lambda t: t[0])
        shp.events = [e for _, e in norm]
        shp.status = (best
                      or _status_from_text(_first(d, "status", "currentStatus", "statusName", default=""))
                      or "in-transit")

        # Air cargo line from piece/weight totals, if present.
        pieces = _first(d, "pieces", "totalPieces")
        weight = _first(d, "weightKg", "totalWeight", "weight")
        if mode == "air" and (pieces or weight):
            shp.cargo = [NormalizedCargo(description=_first(d, "commodity", default="Air cargo") or "Air cargo",
                                         pieces=int(pieces or 1), weight_kg=float(weight or 0))]
        return shp
