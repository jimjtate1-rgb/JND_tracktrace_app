"""
Air cargo feed (IATA Cargo-IMP FSU status model).

Air freight visibility is carried by FSU (Flight Status Update) messages whose
status codes — RCS, MAN, DEP, ARR, RCF, NFD, AWD, DLV, ... — are the universal
air-cargo vocabulary (IATA Cargo-IMP; the modern REST successors are Cargo-XML
and IATA ONE Record). This adapter consumes a JSON representation of an air
waybill plus its FSU status events. Endpoint path / field names vary by provider
and ONE Record carrier, so they are centralised here and easy to adjust.

Configure with AIR_FEED_BASE_URL + AIR_FEED_API_KEY (+ header). Tracks by AWB.
"""
from __future__ import annotations

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
    NormalizedEvent,
    NormalizedShipment,
)

# IATA Cargo-IMP FSU status code -> (description, our shipment status)
_FSU = {
    "BKD": ("Booking confirmed", "booked"),
    "FOH": ("Freight on hand at origin", "booked"),
    "RCS": ("Received from shipper", "gate-in"),
    "MAN": ("Manifested on flight", "loaded"),
    "DEP": ("Departed on flight", "departed"),
    "ARR": ("Arrived at airport", "arrived"),
    "RCF": ("Received from flight", "discharged"),
    "NFD": ("Consignee notified (arrival notice)", "available"),
    "AWD": ("Arrival documents delivered", "available"),
    "DLV": ("Delivered to consignee", "delivered"),
    "TFD": ("Transferred to another flight", "transshipment"),
    "TRM": ("To be transferred", "transshipment"),
    "DIS": ("Discrepancy reported", "delayed"),
}
_RANK = {
    "booked": 0, "gate-in": 1, "loaded": 2, "departed": 3, "in-transit": 4,
    "arrived": 5, "discharged": 6, "available": 7, "delivered": 9, "transshipment": 4,
    "delayed": 4,
}

# Minimal IATA airport -> city lookup (extend as needed); falls back to the code.
_AIRPORTS = {
    "HKG": "Hong Kong", "PVG": "Shanghai", "PEK": "Beijing", "CAN": "Guangzhou",
    "SZX": "Shenzhen", "ICN": "Seoul", "TPE": "Taipei", "NRT": "Tokyo", "SIN": "Singapore",
    "FRA": "Frankfurt", "ANC": "Anchorage",
    "ORD": "Chicago", "LAX": "Los Angeles", "JFK": "New York", "SFO": "San Francisco",
    "DFW": "Dallas", "ATL": "Atlanta", "MIA": "Miami",
}


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _airport_name(code: str) -> str:
    return _AIRPORTS.get((code or "").upper(), code or "")


class AirCargoFeed(CarrierFeed):
    name = "aircargo"
    supported_reference_types = ("awb",)

    def __init__(self):
        self.base_url = (settings.AIR_FEED_BASE_URL or "").rstrip("/")
        self.api_key = settings.AIR_FEED_API_KEY
        self.api_key_header = settings.AIR_FEED_API_KEY_HEADER or "API-Key"

    def fetch(self, *, reference: str, reference_type: str) -> NormalizedShipment:
        if reference_type != "awb":
            raise FeedError("Air cargo feed only supports AWB lookups.")
        if not self.base_url or not self.api_key:
            raise FeedConfigError(
                "Air feed needs AIR_FEED_BASE_URL and AIR_FEED_API_KEY "
                "(or use --sample to parse a local payload)."
            )
        headers = {self.api_key_header: self.api_key, "Accept": "application/json"}
        params = {"awbNumber": re.sub(r"[\s-]", "", reference)}
        try:
            resp = requests.get(f"{self.base_url}/tracking", params=params, headers=headers, timeout=20)
        except requests.RequestException as ex:
            raise FeedError(f"Air feed request failed: {ex}") from ex
        if resp.status_code in (401, 403):
            raise FeedAuthError("Air feed rejected the API key (HTTP %s)." % resp.status_code)
        if resp.status_code == 404:
            raise FeedNotFound(f"No air cargo data for AWB {reference}.")
        if resp.status_code >= 400:
            raise FeedError(f"Air feed returned HTTP {resp.status_code}: {resp.text[:200]}")
        return self.parse_payload(resp.json(), reference=reference, reference_type="awb")

    @classmethod
    def parse_payload(cls, payload: dict, *, reference, reference_type="awb",
                      carrier_name="", carrier_code="") -> NormalizedShipment:
        awb_digits = re.sub(r"[\s-]", "", str(payload.get("awb") or payload.get("awbNumber") or reference))
        carrier = payload.get("carrier") or {}
        shp = NormalizedShipment(
            mode="air", reference=awb_digits, reference_type="awb", awb_number=awb_digits,
            carrier_name=carrier_name or carrier.get("name", ""),
            carrier_code=carrier_code or carrier.get("prefix", ""),
        )

        events_raw = payload.get("events") or payload.get("statusEvents") or []
        norm: list[tuple[datetime, NormalizedEvent]] = []
        best_status, best_rank = "booked", -1
        first_dep = last_arr = None
        latest_flight = ""

        for ev in events_raw:
            code = (ev.get("statusCode") or ev.get("status") or "").upper()
            when = _parse_dt(ev.get("timestamp") or ev.get("eventDateTime") or ev.get("date"))
            if when is None:
                continue
            desc, status = _FSU.get(code, (ev.get("description") or code or "Status update", ""))
            airport = (ev.get("airport") or ev.get("station") or "").upper()
            flight = ev.get("flight") or ev.get("flightNumber") or ""
            if flight:
                latest_flight = flight
            if code == "DEP" and (first_dep is None or when < first_dep[0]):
                first_dep = (when, airport)
            if code == "ARR" and (last_arr is None or when > last_arr[0]):
                last_arr = (when, airport)
            norm.append((when, NormalizedEvent(
                code=code or "FSU", description=desc,
                event_datetime=when, location=_airport_name(airport), location_code=airport,
                vessel_or_flight=flight, is_estimated=bool(ev.get("estimated", False)),
            )))
            if status and _RANK.get(status, -1) > best_rank and not ev.get("estimated", False):
                best_status, best_rank = status, _RANK[status]

        norm.sort(key=lambda t: t[0])
        shp.events = [e for _, e in norm]
        shp.status = best_status
        shp.flight_number = latest_flight

        # Route: explicit origin/destination, else derived from DEP/ARR (or first/last event).
        o_code = (payload.get("origin") or (first_dep[1] if first_dep else "")
                  or (norm[0][1].location_code if norm else "")).upper()
        d_code = (payload.get("destination") or (last_arr[1] if last_arr else "")
                  or (norm[-1][1].location_code if norm else "")).upper()
        shp.origin_code, shp.origin_port = o_code, _airport_name(o_code)
        shp.destination_code, shp.destination_port = d_code, _airport_name(d_code)
        shp.destination_city = _airport_name(d_code)
        if first_dep:
            shp.etd = first_dep[0].date()
        if last_arr:
            shp.eta = last_arr[0].date()

        # Cargo line from AWB-level pieces/weight (no commodity/HS in a status feed).
        pieces = payload.get("pieces")
        weight = payload.get("weightKg") or payload.get("weight")
        if pieces or weight:
            shp.cargo = [NormalizedCargo(
                description=payload.get("commodity") or "Consolidated air cargo",
                pieces=int(pieces or 1), weight_kg=float(weight or 0),
            )]
        return shp
