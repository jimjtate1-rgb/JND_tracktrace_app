import pytest
from rest_framework.test import APIClient


@pytest.fixture
def client():
    return APIClient()


def test_lists_all_66_carriers(client):
    body = client.get("/api/traceapi/carriers/").json()
    assert body["count"] == 66
    assert {"name": "Maersk Line", "scac": "MAEU"} in body["carriers"]
    assert {"name": "ZIM", "scac": "ZIMU"} in body["carriers"]


def test_with_scac_filter(client):
    body = client.get("/api/traceapi/carriers/", {"with_scac": "true"}).json()
    assert all(c["scac"] for c in body["carriers"])
    assert body["count"] == 15


def test_search_by_name(client):
    body = client.get("/api/traceapi/carriers/", {"search": "evergreen"}).json()
    assert body["count"] == 1
    assert body["carriers"][0]["scac"] == "EGLV"


def test_detect_from_bol_prefix(client):
    body = client.get("/api/traceapi/carriers/", {"detect": "CMDU1234567"}).json()
    assert body["carrier"] == {"name": "CMA CGM", "scac": "CMDU"}


def test_detect_unknown_prefix(client):
    body = client.get("/api/traceapi/carriers/", {"detect": "ZZZZ0000000"}).json()
    assert body["carrier"] is None
