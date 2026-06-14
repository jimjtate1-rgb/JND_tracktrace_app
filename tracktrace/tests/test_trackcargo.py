import pytest

from tracktrace.feeds.ingest import ingest_shipment
from tracktrace.feeds.trackcargo import TrackCargoFeed

OCEAN = {
    "orderId": "ord_1", "mode": "sea", "status": "In Transit",
    "carrierName": "Maersk", "scac": "MAEU", "blNumber": "MAEU123456789",
    "portOfLoading": "Shanghai", "polUnlocode": "CNSHA",
    "portOfDischarge": "Los Angeles", "podUnlocode": "USLAX",
    "vesselName": "MAERSK EMDEN", "voyageNumber": "512W",
    "etd": "2026-06-01", "eta": "2026-06-20",
    "containers": [{"containerNumber": "MSKU0762594", "containerType": "40HC", "sealNumber": "ML1"}],
    "events": [
        {"description": "Loaded on vessel", "location": "Shanghai", "unlocode": "CNSHA",
         "vessel": "MAERSK EMDEN", "timestamp": "2026-06-01T10:00:00Z"},
        {"description": "Vessel departed", "location": "Shanghai", "unlocode": "CNSHA",
         "timestamp": "2026-06-01T18:00:00Z"},
        {"description": "Estimated arrival", "location": "Los Angeles", "unlocode": "USLAX",
         "timestamp": "2026-06-20T08:00:00Z", "estimated": True},
    ],
}
AIR = {
    "orderId": "ord_2", "mode": "air", "status": "Arrived", "airline": "Cathay Cargo",
    "awbNumber": "160-22334454", "portOfLoading": "HKG", "portOfDischarge": "ORD",
    "flightNumber": "CX846", "pieces": 1080, "weightKg": 742.5,
    "events": [
        {"description": "Departed", "location": "HKG", "flight": "CX846", "timestamp": "2026-06-10T08:00:00Z"},
        {"description": "Arrived", "location": "ORD", "flight": "CX846", "timestamp": "2026-06-10T16:00:00Z"},
    ],
}


def test_parse_ocean():
    n = TrackCargoFeed.parse_payload(OCEAN, reference="MAEU123456789", reference_type="bol")
    assert n.mode == "ocean" and n.bill_of_lading == "MAEU123456789"
    assert n.carrier_name == "Maersk" and n.carrier_code == "MAEU"
    assert n.origin_code == "CNSHA" and n.destination_code == "USLAX"
    assert n.vessel_name == "MAERSK EMDEN" and n.voyage_number == "512W"
    assert len(n.containers) == 1 and n.containers[0].container_number == "MSKU0762594"
    assert len(n.events) == 3 and n.status == "departed"   # latest non-estimated milestone


def test_parse_air():
    n = TrackCargoFeed.parse_payload(AIR, reference="160-22334454", reference_type="awb")
    assert n.mode == "air" and n.awb_number == "16022334454"
    assert n.flight_number == "CX846" and n.status == "arrived"
    assert len(n.cargo) == 1 and n.cargo[0].pieces == 1080


def test_extract_reference():
    assert TrackCargoFeed.extract_reference(OCEAN) == ("bol", "MAEU123456789")
    assert TrackCargoFeed.extract_reference(AIR) == ("awb", "160-22334454")
    assert TrackCargoFeed.extract_reference({"containers": ["TCNU1234567"]}) == ("container", "TCNU1234567")


def test_fetch_create_then_track(settings, monkeypatch):
    settings.TRACKCARGO_API_KEY = "k"

    class Resp:
        def __init__(self, data, code=200):
            self._d, self.status_code, self.text = data, code, str(data)
        def json(self):
            return self._d

    monkeypatch.setattr("tracktrace.feeds.trackcargo.requests.post", lambda *a, **k: Resp({"orderId": "ord_1"}))
    monkeypatch.setattr("tracktrace.feeds.trackcargo.requests.get", lambda *a, **k: Resp(OCEAN))
    n = TrackCargoFeed().fetch(reference="MAEU123456789", reference_type="bol")
    assert n.destination_code == "USLAX" and len(n.events) == 3


@pytest.mark.django_db
def test_ingest_from_trackcargo(client):
    ingest_shipment(TrackCargoFeed.parse_payload(AIR, reference="160-22334454", reference_type="awb"))
    body = client.get("/api/traceapi/trace/", {"awb_number": "160-22334454"}).json()
    assert body["count"] == 1 and body["results"][0]["transport"]["flight_number"] == "CX846"
