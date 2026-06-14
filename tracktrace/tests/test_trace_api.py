import pytest
from django.core.management import call_command
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def seeded(db):
    call_command("seed_data")


def _get(client, **params):
    resp = client.get("/api/traceapi/trace/", params)
    assert resp.status_code == 200, resp.content
    return resp.json()


def test_ocean_lookup_by_bill_of_lading(client, seeded):
    body = _get(client, bill_of_lading="MAEU562301487")
    assert body["count"] == 1
    r = body["results"][0]
    assert r["mode"] == "ocean"
    assert r["carrier"] == {"name": "Maersk", "code": "MAEU"}
    assert r["transport"]["vessel"] == "MAERSK EMDEN"
    assert len(r["containers"]) == 2
    assert r["destination"]["code"] == "USLAX"
    assert r["weather"] is not None
    assert any(c["hs_code"] == "9405.61.6000" for c in r["cargo"])
    # events present and time-ordered
    times = [e["datetime"] for e in r["events"]]
    assert times == sorted(times)


def test_ocean_lookup_by_container_number(client, seeded):
    # find a seeded container number, then look the shipment up by it
    bol = _get(client, bill_of_lading="MAEU562301487")["results"][0]
    container = bol["containers"][0]["number"]
    body = _get(client, container_number=container)
    assert body["count"] == 1
    assert body["results"][0]["references"]["bill_of_lading"] == "MAEU562301487"


def test_air_lookup_by_awb(client, seeded):
    # AWB of the Cathay shipment (prefix 160)
    listing = _get(client, mode="air")
    awb = next(r["references"]["awb_number"] for r in listing["results"] if r["carrier"]["code"] == "160")
    body = _get(client, awb_number=awb)
    assert body["count"] == 1
    r = body["results"][0]
    assert r["mode"] == "air"
    assert r["transport"]["flight_number"] == "CX880"
    assert r["containers"] == []  # air has no containers
    assert r["destination"]["code"] == "ORD"


def test_air_awb_accepts_dashed_format(client, seeded):
    listing = _get(client, mode="air")
    awb = next(r["references"]["awb_number"] for r in listing["results"] if r["carrier"]["code"] == "160")
    dashed = f"{awb[:3]}-{awb[3:]}"
    body = _get(client, awb_number=dashed)
    assert body["count"] == 1


def test_mode_filter(client, seeded):
    assert _get(client, mode="ocean")["count"] == 2
    assert _get(client, mode="air")["count"] == 2


def test_search_by_destination_port(client, seeded):
    body = _get(client, search="Chicago")
    assert body["count"] == 2  # both air shipments land in Chicago
    assert all(r["mode"] == "air" for r in body["results"])


def test_search_by_carrier_code(client, seeded):
    body = _get(client, search="COSU")
    assert body["count"] == 1
    assert body["results"][0]["carrier"]["name"] == "COSCO Shipping"


def test_no_match_returns_empty(client, seeded):
    assert _get(client, bill_of_lading="NOPE000000")["count"] == 0
