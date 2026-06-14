"""
Carrier-feed abstraction.

A feed turns a carrier/aggregator tracking response into a provider-neutral
`NormalizedShipment`, which the ingest service maps onto the Django models.
Adding a new provider = one subclass of `CarrierFeed`; nothing else changes.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime


class FeedError(Exception):
    """Base class for all feed problems."""


class FeedConfigError(FeedError):
    """Provider is missing required configuration (base URL, API key, ...)."""


class FeedAuthError(FeedError):
    """Provider rejected the credentials (401/403)."""


class FeedNotFound(FeedError):
    """The reference was not found by the provider (404 / empty)."""


@dataclass
class NormalizedEvent:
    code: str
    description: str
    event_datetime: datetime
    location: str = ""
    location_code: str = ""
    vessel_or_flight: str = ""
    is_estimated: bool = False


@dataclass
class NormalizedContainer:
    container_number: str
    container_type: str = ""
    seal_number: str = ""


@dataclass
class NormalizedCargo:
    description: str = "Cargo"
    hs_code: str = ""
    pieces: int = 1
    weight_kg: float = 0.0


@dataclass
class NormalizedShipment:
    mode: str = "ocean"
    reference_type: str = "bol"          # bol | booking | container | awb
    reference: str = ""
    carrier_name: str = ""
    carrier_code: str = ""
    bill_of_lading: str = ""
    booking_number: str = ""
    awb_number: str = ""
    origin_port: str = ""
    origin_code: str = ""
    origin_country: str = ""
    destination_port: str = ""
    destination_code: str = ""
    destination_country: str = ""
    destination_city: str = ""
    vessel_name: str = ""
    voyage_number: str = ""
    flight_number: str = ""
    etd: date | None = None
    eta: date | None = None
    status: str = "booked"
    containers: list[NormalizedContainer] = field(default_factory=list)
    cargo: list[NormalizedCargo] = field(default_factory=list)
    events: list[NormalizedEvent] = field(default_factory=list)


class CarrierFeed(ABC):
    """Interface every provider adapter implements."""

    name: str = "base"

    #: reference kinds this feed accepts
    supported_reference_types: tuple[str, ...] = ("bol", "booking", "container")

    @abstractmethod
    def fetch(self, *, reference: str, reference_type: str) -> NormalizedShipment:
        """Look up a shipment and return it in normalized form. Raises FeedError."""
        raise NotImplementedError

    @classmethod
    def parse_payload(cls, payload, *, reference: str, reference_type: str,
                      carrier_name: str = "", carrier_code: str = "") -> NormalizedShipment:
        """Turn a raw provider payload into a NormalizedShipment (used for offline samples)."""
        raise NotImplementedError
