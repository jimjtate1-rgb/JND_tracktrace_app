import json
from pathlib import Path

import pytest

from tracktrace.feeds.aircargo import AirCargoFeed
from tracktrace.feeds.base import FeedAuthError, FeedConfigError
from tracktrace.feeds.ingest import ingest_shipment

SAMPLE = Path("tracktrace/feeds/samples/aircargo_fsu_sample.json")


def _parse():
    payload = json.loads(SAMPLE.read_text())
    return AirCargoFeed.parse_payload(payload, reference="160-22334454", reference_type="awb",
                                      carrier_name="Cathay Cargo", carrier_code="160")


def test_parse_fsu_events():
    n = _parse()
    assert n.mode == "air"
    assert n.awb_number == "16022334454"          # dashes stripped
    assert n.origin_code == "HKG" and n.destination_code == "ORD"
    assert n.origin_port == "Hong Kong" and n.destination_port == "Chicago"
    assert n.flight_number == "CX846"
    assert n.status == "available"                # latest actual FSU is NFD
    assert len(n.events) == 7
    assert n.events[0].code == "FOH"
    assert len(n.cargo) == 1 and n.cargo[0].pieces == 1080


@pytest.mark.django_db
def test_ingest_air_idempotent():
    s, created = ingest_shipment(_parse())
    assert created and s.mode == "air"
    assert s.awb_number == "16022334454"
    assert s.cargo.count() == 1 and s.events.count() == 7
    s2, created2 = ingest_shipment(_parse())
    assert not created2 and s2.pk == s.pk
    assert s2.events.count() == 7 and s2.cargo.count() == 1


@pytest.mark.django_db
def test_air_searchable_via_api(client):
    ingest_shipment(_parse())
    body = client.get("/api/traceapi/trace/", {"awb_number": "160-22334454"}).json()
    assert body["count"] == 1
    r = body["results"][0]
    assert r["mode"] == "air" and r["transport"]["flight_number"] == "CX846"


def test_air_fetch_requires_config(settings):
    settings.AIR_FEED_BASE_URL = ""
    settings.AIR_FEED_API_KEY = ""
    with pytest.raises(FeedConfigError):
        AirCargoFeed().fetch(reference="160-22334454", reference_type="awb")


def test_air_fetch_success(settings, monkeypatch):
    settings.AIR_FEED_BASE_URL = "https://air.example.com/v1"
    settings.AIR_FEED_API_KEY = "k"

    class R:
        status_code = 200
        def json(self): return json.loads(SAMPLE.read_text())
    monkeypatch.setattr("tracktrace.feeds.aircargo.requests.get", lambda *a, **k: R())
    n = AirCargoFeed().fetch(reference="160-22334454", reference_type="awb")
    assert n.destination_code == "ORD" and len(n.events) == 7
