from django.db import models

from tracktrace.common.models import BaseModel
from tracktrace.traceapi.validators import (
    validate_awb_number,
    validate_container_number,
)
from tracktrace.weather.models import Weather


class TransportMode(models.TextChoices):
    OCEAN = "ocean", "Ocean"
    AIR = "air", "Air"


class ShipmentStatus(models.TextChoices):
    BOOKED = "booked", "Booked"
    GATE_IN = "gate-in", "Gate in at origin"
    LOADED = "loaded", "Loaded on board"
    DEPARTED = "departed", "Departed origin"
    IN_TRANSIT = "in-transit", "In transit"
    TRANSSHIPMENT = "transshipment", "Transshipment"
    ARRIVED = "arrived", "Arrived at destination"
    DISCHARGED = "discharged", "Discharged"
    AVAILABLE = "available", "Available for pickup"
    OUT_FOR_DELIVERY = "out-for-delivery", "Out for delivery"
    DELIVERED = "delivered", "Delivered"
    DELAYED = "delayed", "Delayed"


# Statuses that mean the shipment is finished -> no more weather refreshes.
TERMINAL_STATUSES = {ShipmentStatus.DELIVERED}


class Shipment(BaseModel):
    mode = models.CharField(max_length=10, choices=TransportMode.choices, db_index=True)
    status = models.CharField(
        max_length=20, choices=ShipmentStatus.choices, default=ShipmentStatus.BOOKED, db_index=True
    )

    # Carrier (SCAC for ocean, IATA airline prefix for air).
    carrier_name = models.CharField(max_length=100)
    carrier_code = models.CharField(max_length=10, db_index=True, blank=True)

    # Reference numbers (mode-specific; blank where not applicable).
    bill_of_lading = models.CharField(max_length=40, blank=True, db_index=True)
    booking_number = models.CharField(max_length=40, blank=True, db_index=True)
    awb_number = models.CharField(
        max_length=20, blank=True, db_index=True, validators=[validate_awb_number]
    )

    # Parties.
    shipper_name = models.CharField(max_length=150)
    shipper_address = models.CharField(max_length=255, blank=True)
    consignee_name = models.CharField(max_length=150)
    consignee_address = models.CharField(max_length=255, blank=True)

    # Origin port/airport.
    origin_port = models.CharField(max_length=100)
    origin_code = models.CharField(max_length=10, blank=True)  # UN/LOCODE or IATA
    origin_country = models.CharField(max_length=60, blank=True)

    # Destination port/airport (+ city used for weather).
    destination_port = models.CharField(max_length=100)
    destination_code = models.CharField(max_length=10, blank=True)
    destination_country = models.CharField(max_length=60, blank=True)
    destination_city = models.CharField(max_length=80, blank=True)

    # Conveyance.
    vessel_name = models.CharField(max_length=100, blank=True)  # ocean
    voyage_number = models.CharField(max_length=20, blank=True)  # ocean
    flight_number = models.CharField(max_length=20, blank=True)  # air

    etd = models.DateField(null=True, blank=True)  # estimated departure
    eta = models.DateField(null=True, blank=True)  # estimated arrival

    weather = models.ForeignKey(Weather, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        ref = self.bill_of_lading or self.awb_number or self.booking_number or str(self.pk)
        return f"[{self.mode}] {ref}"

    @property
    def primary_reference(self) -> str:
        return self.bill_of_lading or self.awb_number or self.booking_number or ""


class Container(models.Model):
    """Ocean only: a BOL/booking can carry many containers."""

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="containers")
    container_number = models.CharField(
        max_length=11, db_index=True, validators=[validate_container_number]
    )
    container_type = models.CharField(max_length=10, blank=True)  # e.g. 40HC, 20GP, 40RF
    seal_number = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.container_number


class CargoItem(models.Model):
    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="cargo")
    description = models.CharField(max_length=200)
    hs_code = models.CharField(max_length=12, blank=True)  # HTS classification
    pieces = models.PositiveIntegerField(default=1)
    weight_kg = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"{self.description} ({self.pieces} pcs)"


class TrackingEvent(BaseModel):
    """
    A single milestone in the shipment timeline.

    Ocean codes (DCSA-style): GTIN, LOAD, DEPA, ARRI, DISC, GTOT, DLVD, AVPU.
    Air codes (IATA Cargo-IMP):  BKD, RCS, MAN, DEP, ARR, RCF, NFD, DLV.
    """

    shipment = models.ForeignKey(Shipment, on_delete=models.CASCADE, related_name="events")
    container = models.ForeignKey(
        Container, on_delete=models.CASCADE, null=True, blank=True, related_name="events"
    )
    code = models.CharField(max_length=12)
    description = models.CharField(max_length=200)
    location = models.CharField(max_length=100, blank=True)
    location_code = models.CharField(max_length=10, blank=True)
    vessel_or_flight = models.CharField(max_length=100, blank=True)
    event_datetime = models.DateTimeField(db_index=True)
    is_estimated = models.BooleanField(default=False)  # planned vs actual

    class Meta:
        ordering = ["event_datetime"]

    def __str__(self):
        return f"{self.code} @ {self.location} ({self.event_datetime:%Y-%m-%d})"
