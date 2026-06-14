"""
Seed realistic ocean + air freight shipments with event timelines.

    python manage.py seed_data
"""
from datetime import datetime, timedelta, timezone as dt_timezone

from django.core.management.base import BaseCommand
from django.db import transaction

from tracktrace.traceapi.models import (
    CargoItem,
    Container,
    Shipment,
    TrackingEvent,
)
from tracktrace.traceapi.validators import build_awb_number, build_container_number
from tracktrace.weather.models import Weather


def dt(base, days=0, hours=0):
    return base + timedelta(days=days, hours=hours)


class Command(BaseCommand):
    help = "Seed sample ocean and air shipments (China -> US lane)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty", action="store_true",
            help="Only seed when no shipments exist yet (safe to run on every deploy).",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options["if_empty"] and Shipment.objects.exists():
            self.stdout.write(
                f"seed_data --if-empty: {Shipment.objects.count()} shipment(s) already "
                "present, skipping."
            )
            return
        TrackingEvent.objects.all().delete()
        Container.objects.all().delete()
        CargoItem.objects.all().delete()
        Shipment.objects.all().delete()
        Weather.objects.all().delete()

        weather = {
            ("Los Angeles", "United States"): Weather.objects.create(
                city="Los Angeles", country="United States",
                temperature=295.4, wind_speed=3.1, description="clear sky"),
            ("Chicago", "United States"): Weather.objects.create(
                city="Chicago", country="United States",
                temperature=288.2, wind_speed=5.7, description="broken clouds"),
            ("Newark", "United States"): Weather.objects.create(
                city="Newark", country="United States",
                temperature=291.0, wind_speed=4.2, description="light rain"),
        }

        base = datetime(2026, 6, 1, 8, 0, tzinfo=dt_timezone.utc)

        # ---------- OCEAN 1: Maersk, Shanghai -> Los Angeles (in transit) ----------
        bol = "MAEU" + "562301487"
        s1 = Shipment.objects.create(
            mode="ocean", status="in-transit",
            carrier_name="Maersk", carrier_code="MAEU",
            bill_of_lading=bol, booking_number="562301487",
            shipper_name="Shenzhen Lumina Electronics Co., Ltd",
            shipper_address="Bao'an District, Shenzhen, China",
            consignee_name="Pacific Import Partners LLC",
            consignee_address="2200 E 7th St, Los Angeles, CA 90021, USA",
            origin_port="Shanghai", origin_code="CNSHA", origin_country="China",
            destination_port="Los Angeles", destination_code="USLAX",
            destination_country="United States", destination_city="Los Angeles",
            vessel_name="MAERSK EMDEN", voyage_number="512W",
            etd=dt(base, 0).date(), eta=dt(base, 19).date(),
            weather=weather[("Los Angeles", "United States")],
        )
        c1a = Container.objects.create(
            shipment=s1, container_number=build_container_number("MSKU", "076259"),
            container_type="40HC", seal_number="ML-AX88231")
        c1b = Container.objects.create(
            shipment=s1, container_number=build_container_number("MSKU", "184022"),
            container_type="40HC", seal_number="ML-AX88245")
        CargoItem.objects.create(
            shipment=s1, description="LED illuminated signage", hs_code="9405.61.6000",
            pieces=320, weight_kg=4180.00)
        CargoItem.objects.create(
            shipment=s1, description="Hand tool sets", hs_code="8206.00.0000",
            pieces=150, weight_kg=2960.00)
        ocean1_events = [
            (0, 0, "GTIN", "Empty container gated in / stuffed", "Shanghai", "CNSHA", "", False),
            (0, 6, "LOAD", "Loaded on vessel", "Shanghai", "CNSHA", "MAERSK EMDEN 512W", False),
            (0, 14, "DEPA", "Vessel departed origin", "Shanghai", "CNSHA", "MAERSK EMDEN 512W", False),
            (8, 0, "ARRI", "Vessel arrived transshipment", "Busan", "KRPUS", "MAERSK EMDEN 512W", False),
            (8, 10, "DEPA", "Vessel departed transshipment", "Busan", "KRPUS", "MAERSK HORSBURGH 514W", False),
            (19, 0, "ARRI", "Estimated vessel arrival", "Los Angeles", "USLAX", "MAERSK HORSBURGH 514W", True),
            (20, 0, "DISC", "Estimated discharge from vessel", "Los Angeles", "USLAX", "", True),
        ]
        for d, h, code, desc, loc, lc, vf, est in ocean1_events:
            TrackingEvent.objects.create(
                shipment=s1, code=code, description=desc, location=loc,
                location_code=lc, vessel_or_flight=vf, event_datetime=dt(base, d, h),
                is_estimated=est)

        # ---------- OCEAN 2: COSCO, Ningbo -> Newark (delivered) ----------
        s2 = Shipment.objects.create(
            mode="ocean", status="delivered",
            carrier_name="COSCO Shipping", carrier_code="COSU",
            bill_of_lading="COSU6789012345", booking_number="6789012345",
            shipper_name="Ningbo Homewares Mfg Co.",
            shipper_address="Beilun, Ningbo, China",
            consignee_name="Eastline Distribution Inc.",
            consignee_address="Port Newark, NJ 07114, USA",
            origin_port="Ningbo", origin_code="CNNGB", origin_country="China",
            destination_port="New York / Newark", destination_code="USNYC",
            destination_country="United States", destination_city="Newark",
            vessel_name="COSCO SHIPPING ARIES", voyage_number="047E",
            etd=dt(base, -35).date(), eta=dt(base, -7).date(),
            weather=weather[("Newark", "United States")],
        )
        Container.objects.create(
            shipment=s2, container_number=build_container_number("CSNU", "622918"),
            container_type="20GP", seal_number="CS-1182004")
        CargoItem.objects.create(
            shipment=s2, description="Upholstered seating", hs_code="9401.61.6011",
            pieces=88, weight_kg=5120.00)
        ocean2_events = [
            (-35, 0, "GTIN", "Empty container gated in / stuffed", "Ningbo", "CNNGB", "", False),
            (-34, 0, "DEPA", "Vessel departed origin", "Ningbo", "CNNGB", "COSCO SHIPPING ARIES 047E", False),
            (-8, 0, "ARRI", "Vessel arrived destination", "New York / Newark", "USNYC", "COSCO SHIPPING ARIES 047E", False),
            (-7, 4, "DISC", "Discharged from vessel", "New York / Newark", "USNYC", "", False),
            (-5, 0, "GTOT", "Full container gated out for delivery", "Newark", "USNYC", "", False),
            (-4, 0, "DLVD", "Delivered to consignee", "Newark", "USNYC", "", False),
        ]
        for d, h, code, desc, loc, lc, vf, est in ocean2_events:
            TrackingEvent.objects.create(
                shipment=s2, code=code, description=desc, location=loc,
                location_code=lc, vessel_or_flight=vf, event_datetime=dt(base, d, h),
                is_estimated=est)

        # ---------- AIR 1: Cathay Pacific, Hong Kong -> Chicago (arrived/notified) ----------
        awb1 = build_awb_number("160", "4421890")  # Cathay prefix 160
        a1 = Shipment.objects.create(
            mode="air", status="available",
            carrier_name="Cathay Pacific Cargo", carrier_code="160",
            awb_number=awb1,
            shipper_name="Guangzhou Precision Components Ltd",
            shipper_address="Huangpu District, Guangzhou, China",
            consignee_name="Midwest Tech Imports LLC",
            consignee_address="O'Hare Cargo City, Chicago, IL 60666, USA",
            origin_port="Hong Kong Intl", origin_code="HKG", origin_country="Hong Kong",
            destination_port="Chicago O'Hare Intl", destination_code="ORD",
            destination_country="United States", destination_city="Chicago",
            flight_number="CX880",
            etd=dt(base, 10).date(), eta=dt(base, 11).date(),
            weather=weather[("Chicago", "United States")],
        )
        CargoItem.objects.create(
            shipment=a1, description="Smartphones", hs_code="8517.13.0000",
            pieces=1200, weight_kg=860.00)
        air1_events = [
            (10, 0, "BKD", "Booking confirmed", "Hong Kong", "HKG", "", False),
            (10, 4, "RCS", "Cargo received from shipper", "Hong Kong", "HKG", "", False),
            (10, 8, "MAN", "Manifested on flight", "Hong Kong", "HKG", "CX880", False),
            (10, 11, "DEP", "Departed on flight (uplift)", "Hong Kong", "HKG", "CX880", False),
            (11, 6, "ARR", "Arrived at destination", "Chicago", "ORD", "CX880", False),
            (11, 9, "RCF", "Received from flight", "Chicago", "ORD", "", False),
            (11, 11, "NFD", "Consignee notified (arrival notice)", "Chicago", "ORD", "", False),
        ]
        for d, h, code, desc, loc, lc, vf, est in air1_events:
            TrackingEvent.objects.create(
                shipment=a1, code=code, description=desc, location=loc,
                location_code=lc, vessel_or_flight=vf, event_datetime=dt(base, d, h),
                is_estimated=est)

        # ---------- AIR 2: Lufthansa, Shanghai -> Chicago via Frankfurt (in transit) ----------
        awb2 = build_awb_number("020", "9087654")  # Lufthansa prefix 020
        a2 = Shipment.objects.create(
            mode="air", status="in-transit",
            carrier_name="Lufthansa Cargo", carrier_code="020",
            awb_number=awb2,
            shipper_name="Suzhou Medical Devices Co.",
            shipper_address="Suzhou Industrial Park, China",
            consignee_name="Great Lakes Medical Supply",
            consignee_address="1100 W Cermak Rd, Chicago, IL 60608, USA",
            origin_port="Shanghai Pudong Intl", origin_code="PVG", origin_country="China",
            destination_port="Chicago O'Hare Intl", destination_code="ORD",
            destination_country="United States", destination_city="Chicago",
            flight_number="LH729",
            etd=dt(base, 2).date(), eta=dt(base, 3).date(),
            weather=weather[("Chicago", "United States")],
        )
        CargoItem.objects.create(
            shipment=a2, description="Diagnostic test kits", hs_code="3822.00.0000",
            pieces=540, weight_kg=1320.00)
        air2_events = [
            (2, 0, "RCS", "Cargo received from shipper", "Shanghai", "PVG", "", False),
            (2, 6, "DEP", "Departed on flight (uplift)", "Shanghai", "PVG", "LH729", False),
            (2, 20, "ARR", "Arrived transit hub", "Frankfurt", "FRA", "LH729", False),
            (3, 2, "DEP", "Departed transit hub", "Frankfurt", "FRA", "LH8090", False),
            (3, 12, "ARR", "Estimated arrival", "Chicago", "ORD", "LH8090", True),
        ]
        for d, h, code, desc, loc, lc, vf, est in air2_events:
            TrackingEvent.objects.create(
                shipment=a2, code=code, description=desc, location=loc,
                location_code=lc, vessel_or_flight=vf, event_datetime=dt(base, d, h),
                is_estimated=est)

        self.stdout.write(self.style.SUCCESS(
            f"Seeded {Shipment.objects.count()} shipments "
            f"({Shipment.objects.filter(mode='ocean').count()} ocean, "
            f"{Shipment.objects.filter(mode='air').count()} air), "
            f"{Container.objects.count()} containers, "
            f"{TrackingEvent.objects.count()} events."))
