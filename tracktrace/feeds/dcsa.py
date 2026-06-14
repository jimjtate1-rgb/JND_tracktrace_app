"""
DCSA Track & Trace v2 adapter.

Targets the DCSA T&T Interface Standard v2.2 (the vendor-neutral spec implemented
by Maersk, Hapag-Lloyd, CMA CGM, COSCO, ONE, Evergreen, Yang Ming, HMM, ZIM and
others — see github.com/dcsaorg/DCSA-OpenAPI). The carrier's `GET /events`
endpoint returns a flat list of SHIPMENT / TRANSPORT / EQUIPMENT events; we derive
the route, vessel/voyage, ETD/ETA, containers and a status from that timeline.

Field access is deliberately tolerant: it accepts both v2.2 (`transportCall.location`,
`transportCall.vessel`) and v2.1-style flattened fields, since carriers vary. Verify
the exact request params / auth header against your carrier's published DCSA docs.

DCSA T&T does NOT expose commercial party data (shipper/consignee) or cargo line
items — those live in gated Booking / Shipping-Instruction APIs — so those fields
stay blank when populated from this feed.
"""
from __future__ import annotations

from datetime import datetime

import requests
from django.conf import settings

from tracktrace.feeds.base import (
    CarrierFeed,
    FeedAuthError,
    FeedConfigError,
    FeedError,
    FeedNotFound,
    NormalizedContainer,
    NormalizedEvent,
    NormalizedShipment,
)

# DCSA reference type -> GET /events query parameter.
_REF_PARAM = {
    "bol": "transportDocumentReference",
    "booking": "carrierBookingReference",
    "container": "equipmentReference",
}

# EQUIPMENT equipmentEventTypeCode -> (human description, our status)
_EQUIP = {
    "GTIN": ("Gated in at terminal", "gate-in"),
    "GTOT": ("Gated out for delivery", "out-for-delivery"),
    "LOAD": ("Loaded on vessel", "loaded"),
    "DISC": ("Discharged from vessel", "discharged"),
    "STUF": ("Container stuffed", ""),
    "STRP": ("Container stripped", ""),
    "PICK": ("Empty container picked up", ""),
    "DROP": ("Empty container returned", ""),
    "INSP": ("Container inspected", ""),
}
# TRANSPORT transportEventTypeCode -> (description, status)
_TRANSPORT = {
    "ARRI": ("Vessel arrived", "arrived"),
    "DEPA": ("Vessel departed", "departed"),
}
# SHIPMENT shipmentEventTypeCode -> (description, status)
_SHIPMENT = {
    "RECE": ("Booking received", "booked"),
    "CONF": ("Booking confirmed", "booked"),
    "ISSU": ("Transport document issued", "booked"),
    "RELS": ("Released", "available"),
    "SURR": ("Document surrendered", ""),
}
# How far each status sits along the route (used only to seed ordering/priority).
_RANK = {
    "booked": 0, "gate-in": 1, "loaded": 2, "departed": 3, "in-transit": 4,
    "arrived": 5, "discharged": 6, "available": 7, "out-for-delivery": 8, "delivered": 9,
}


def _parse_dt(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _transport_call(ev: dict) -> dict:
    return ev.get("transportCall") or {}


def _location(tc: dict) -> tuple[str, str]:
    """Return (location_name, UNLocationCode) tolerating v2.1/v2.2 shapes."""
    loc = tc.get("location") or {}
    name = loc.get("locationName") or loc.get("UNLocationCode") or tc.get("UNLocationCode") or ""
    code = loc.get("UNLocationCode") or tc.get("UNLocationCode") or ""
    return name, code


def _vessel_voyage(tc: dict) -> tuple[str, str]:
    vessel = (tc.get("vessel") or {}).get("vesselName") or tc.get("vesselName") or ""
    voyage = tc.get("carrierVoyageNumber") or tc.get("exportVoyageNumber") or ""
    return vessel, voyage


class DcsaFeed(CarrierFeed):
    name = "dcsa"

    def __init__(self):
        self.base_url = (settings.DCSA_BASE_URL or "").rstrip("/")
        self.api_key = settings.DCSA_API_KEY
        self.api_key_header = settings.DCSA_API_KEY_HEADER or "API-Key"
        self.carrier_name = settings.DCSA_CARRIER_NAME
        self.carrier_code = settings.DCSA_CARRIER_SCAC

    # ---- network ----
    def fetch(self, *, reference: str, reference_type: str) -> NormalizedShipment:
        if reference_type not in _REF_PARAM:
            raise FeedError(f"DCSA feed does not support reference type '{reference_type}'.")
        if not self.base_url or not self.api_key:
            raise FeedConfigError(
                "DCSA feed needs DCSA_BASE_URL and DCSA_API_KEY. "
                "Set them in .env (or use --sample to parse a local payload)."
            )

        params = {_REF_PARAM[reference_type]: reference}
        headers = {self.api_key_header: self.api_key, "Accept": "application/json"}
        try:
            resp = requests.get(f"{self.base_url}/events", params=params, headers=headers, timeout=20)
        except requests.RequestException as ex:
            raise FeedError(f"DCSA request failed: {ex}") from ex

        if resp.status_code in (401, 403):
            raise FeedAuthError("DCSA provider rejected the API key (HTTP %s)." % resp.status_code)
        if resp.status_code == 404:
            raise FeedNotFound(f"No DCSA events found for {reference_type} {reference}.")
        if resp.status_code >= 400:
            raise FeedError(f"DCSA provider returned HTTP {resp.status_code}: {resp.text[:200]}")

        return self.parse_payload(resp.json(), reference=reference, reference_type=reference_type,
                                  carrier_name=self.carrier_name, carrier_code=self.carrier_code)

    @classmethod
    def parse_payload(cls, payload, *, reference, reference_type,
                      carrier_name="", carrier_code=""):
        events = cls._extract_events(payload)
        if not events:
            raise FeedNotFound(f"No DCSA events found for {reference_type} {reference}.")
        return cls.parse(events, reference=reference, reference_type=reference_type,
                         carrier_name=carrier_name, carrier_code=carrier_code)

    @classmethod
    def extract_reference(cls, events: list[dict]) -> tuple[str | None, str | None]:
        """Derive (reference_type, reference) from pushed events (used by the webhook)."""
        bol = booking = container = None
        for ev in events:
            for ref in (ev.get("documentReferences") or ev.get("references") or []):
                if not isinstance(ref, dict):
                    continue
                rtype = (ref.get("documentTypeCode") or ref.get("documentReferenceType")
                         or ref.get("type") or "").upper()
                rval = (ref.get("documentReference") or ref.get("documentReferenceValue")
                        or ref.get("value") or "")
                if not rval:
                    continue
                if rtype in ("TRD", "TRANSPORTDOCUMENT", "BL", "BOL") and not bol:
                    bol = rval
                elif rtype in ("BKG", "CBR", "BOOKING") and not booking:
                    booking = rval
            if not container and ev.get("equipmentReference"):
                container = ev["equipmentReference"]
        if bol:
            return "bol", bol
        if booking:
            return "booking", booking
        if container:
            return "container", container
        return None, None

    @staticmethod
    def _extract_events(payload) -> list[dict]:
        if isinstance(payload, list):
            return payload
        if isinstance(payload, dict):
            for key in ("events", "data", "results"):
                if isinstance(payload.get(key), list):
                    return payload[key]
        return []

    # ---- mapping (also used directly for offline sample payloads) ----
    @classmethod
    def parse(cls, events: list[dict], *, reference: str, reference_type: str,
              carrier_name: str = "", carrier_code: str = "") -> NormalizedShipment:
        shp = NormalizedShipment(
            mode="ocean", reference=reference, reference_type=reference_type,
            carrier_name=carrier_name, carrier_code=carrier_code,
        )
        if reference_type == "bol":
            shp.bill_of_lading = reference
        elif reference_type == "booking":
            shp.booking_number = reference

        containers: dict[str, NormalizedContainer] = {}
        norm_events: list[tuple[datetime, NormalizedEvent]] = []
        best_status, best_rank = "booked", -1
        first_depa = last_arri = None

        for ev in events:
            etype = (ev.get("eventType") or "").upper()
            classifier = (ev.get("eventClassifierCode") or "").upper()  # PLN / EST / ACT
            estimated = classifier != "ACT"
            when = _parse_dt(ev.get("eventDateTime"))
            if when is None:
                continue
            tc = _transport_call(ev)
            loc_name, loc_code = _location(tc)
            vessel, voyage = _vessel_voyage(tc)
            vf = f"{vessel} {voyage}".strip()

            code = desc = ""
            status = ""

            if etype == "EQUIPMENT":
                code = (ev.get("equipmentEventTypeCode") or "").upper()
                desc, status = _EQUIP.get(code, (code or "Equipment event", ""))
                ref_no = ev.get("equipmentReference") or ""
                if ref_no:
                    iso = ev.get("ISOEquipmentCode") or ev.get("isoEquipmentCode") or ""
                    c = containers.setdefault(ref_no, NormalizedContainer(ref_no, iso))
                    if iso and not c.container_type:
                        c.container_type = iso
                empty = (ev.get("emptyIndicator") or "").upper()
                if empty == "LADEN":
                    desc += " (laden)"
                elif empty == "EMPTY":
                    desc += " (empty)"
            elif etype == "TRANSPORT":
                code = (ev.get("transportEventTypeCode") or "").upper()
                base_desc, status = _TRANSPORT.get(code, (code or "Transport event", ""))
                desc = f"{base_desc} {loc_name}".strip() if loc_name else base_desc
                if code == "DEPA" and (first_depa is None or when < first_depa[0]):
                    first_depa = (when, loc_name, loc_code, classifier)
                if code == "ARRI" and (last_arri is None or when > last_arri[0]):
                    last_arri = (when, loc_name, loc_code, classifier)
            elif etype == "SHIPMENT":
                code = (ev.get("shipmentEventTypeCode") or "").upper()
                desc, status = _SHIPMENT.get(code, (code or "Shipment event", ""))
            else:
                continue

            norm_events.append((when, NormalizedEvent(
                code=code or etype, description=desc or etype, event_datetime=when,
                location=loc_name, location_code=loc_code, vessel_or_flight=vf,
                is_estimated=estimated,
            )))

            if not estimated and status and _RANK.get(status, -1) > best_rank:
                best_status, best_rank = status, _RANK[status]

        norm_events.sort(key=lambda t: t[0])
        shp.events = [e for _, e in norm_events]
        shp.containers = list(containers.values())

        # Route + schedule from transport calls.
        if first_depa:
            shp.origin_port, shp.origin_code = first_depa[1], first_depa[2]
            shp.etd = first_depa[0].date()
        if last_arri:
            shp.destination_port, shp.destination_code = last_arri[1], last_arri[2]
            shp.destination_city = last_arri[1]
            shp.eta = last_arri[0].date()

        # Vessel/voyage from the most recent transport-bearing event.
        for _, e in reversed(norm_events):
            if e.vessel_or_flight:
                parts = e.vessel_or_flight.rsplit(" ", 1)
                shp.vessel_name = parts[0]
                shp.voyage_number = parts[1] if len(parts) > 1 else ""
                break

        # If an arrival is only estimated but a discharge already happened, treat as arrived.
        shp.status = best_status
        return shp
