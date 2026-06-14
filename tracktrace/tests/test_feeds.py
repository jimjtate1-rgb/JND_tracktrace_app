import json
from pathlib import Path

import pytest

from tracktrace.feeds.base import FeedAuthError, FeedConfigError, FeedError, FeedNotFound
from tracktrace.feeds.dcsa import DcsaFeed
from tracktrace.feeds.ingest import ingest_shipment
from tracktrace.feeds.registry import get_feed
from tracktrace.traceapi.models import Shipment, TrackingEvent

SAMPLE = Path("tracktrace/feeds/samples/dcsa_events_sample.json")


def _sample_events():
    return DcsaFeed._extract_events(json.loads(SAMPLE.read_text()))


def _parse():
    return DcsaFeed.parse(_sample_events(), reference="COSU6229185001", reference_type="bol",
                          carrier_name="COSCO Shipping", carrier_code="COSU")


# ---- parsing ----
def test_parse_maps_dcsa_events():
    n = _parse()
    assert n.mode == "ocean"
    assert n.bill_of_lading == "COSU6229185001"
    assert n.carrier_code == "COSU"
    assert n.origin_code == "CNSHA" and n.destination_code == "USLAX"
    assert n.vessel_name == "COSCO SHIPPING ARIES" and n.voyage_number == "047E"
    assert n.status == "departed"               # latest ACT event is DEPA
    assert n.etd.isoformat() == "2026-05-30"    # DEPA date at origin port (local)
    assert len(n.containers) == 1
    assert n.containers[0].container_number == "CSNU6229185"
    assert n.containers[0].container_type == "45G1"
    assert len(n.events) == 5
    assert [e.is_estimated for e in n.events] == [False, False, False, True, True]
    assert n.events[0].code == "GTIN"


def test_events_are_time_sorted():
    n = _parse()
    times = [e.event_datetime for e in n.events]
    assert times == sorted(times)


# ---- ingest ----
@pytest.mark.django_db
def test_ingest_creates_then_updates_idempotently():
    shipment, created = ingest_shipment(_parse())
    assert created is True
    assert shipment.bill_of_lading == "COSU6229185001"
    assert shipment.containers.count() == 1
    assert shipment.events.count() == 5

    shipment2, created2 = ingest_shipment(_parse())
    assert created2 is False
    assert shipment2.pk == shipment.pk
    assert Shipment.objects.filter(bill_of_lading="COSU6229185001").count() == 1
    assert shipment2.containers.count() == 1
    assert shipment2.events.count() == 5            # replaced, not duplicated
    assert TrackingEvent.objects.filter(shipment=shipment2).count() == 5


@pytest.mark.django_db
def test_ingested_shipment_is_searchable_via_api(client):
    ingest_shipment(_parse())
    body = client.get("/api/traceapi/trace/", {"bill_of_lading": "COSU6229185001"}).json()
    assert body["count"] == 1
    assert body["results"][0]["transport"]["vessel"] == "COSCO SHIPPING ARIES"


@pytest.fixture
def client():
    from rest_framework.test import APIClient
    return APIClient()


# ---- network behaviour (mocked) ----
class _Resp:
    def __init__(self, status, payload=None, text=""):
        self.status_code = status
        self._payload = payload if payload is not None else []
        self.text = text

    def json(self):
        return self._payload


def test_fetch_requires_config(settings):
    settings.DCSA_BASE_URL = ""
    settings.DCSA_API_KEY = ""
    with pytest.raises(FeedConfigError):
        DcsaFeed().fetch(reference="COSU1", reference_type="bol")


def test_fetch_success(settings, monkeypatch):
    settings.DCSA_BASE_URL = "https://api.example-carrier.com/dcsa/tnt/v2"
    settings.DCSA_API_KEY = "test-key"
    monkeypatch.setattr("tracktrace.feeds.dcsa.requests.get",
                        lambda *a, **k: _Resp(200, _sample_events()))
    n = DcsaFeed().fetch(reference="COSU6229185001", reference_type="bol")
    assert n.destination_code == "USLAX" and len(n.events) == 5


@pytest.mark.parametrize("status,exc", [(401, FeedAuthError), (404, FeedNotFound), (500, FeedError)])
def test_fetch_http_errors(settings, monkeypatch, status, exc):
    settings.DCSA_BASE_URL = "https://api.example-carrier.com/dcsa/tnt/v2"
    settings.DCSA_API_KEY = "test-key"
    monkeypatch.setattr("tracktrace.feeds.dcsa.requests.get",
                        lambda *a, **k: _Resp(status, text="err"))
    with pytest.raises(exc):
        DcsaFeed().fetch(reference="X", reference_type="bol")


def test_unknown_provider():
    with pytest.raises(FeedError):
        get_feed("nope")
