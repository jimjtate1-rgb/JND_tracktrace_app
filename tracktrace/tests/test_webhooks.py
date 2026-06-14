import hashlib
import hmac
import json

import pytest

from tracktrace.feeds.webhooks import verify_signature

URL = "/api/feeds/dcsa/webhook/"
SECRET = "whsec_test"

TC = {"carrierVoyageNumber": "047E",
      "location": {"locationName": "Los Angeles", "UNLocationCode": "USLAX"},
      "vessel": {"vesselName": "COSCO SHIPPING ARIES"}}
DOCREFS = [{"documentTypeCode": "TRD", "documentReference": "COSU9000001"}]
EVENTS = [
    {"eventType": "TRANSPORT", "eventClassifierCode": "ACT", "eventDateTime": "2026-06-17T15:30:00-07:00",
     "transportEventTypeCode": "ARRI", "transportCall": TC, "documentReferences": DOCREFS},
    {"eventType": "EQUIPMENT", "eventClassifierCode": "ACT", "eventDateTime": "2026-06-18T09:10:00-07:00",
     "equipmentEventTypeCode": "DISC", "equipmentReference": "CSNU9000001", "transportCall": TC,
     "documentReferences": DOCREFS},
]


def _sign(raw: bytes) -> str:
    return hmac.new(SECRET.encode(), raw, hashlib.sha256).hexdigest()


def test_verify_signature():
    raw = b'{"a":1}'
    good = _sign(raw)
    assert verify_signature(raw, good, SECRET)
    assert verify_signature(raw, "sha256=" + good, SECRET)
    assert not verify_signature(raw, "nope", SECRET)
    assert not verify_signature(raw, good, "wrong-secret")


@pytest.mark.django_db
def test_webhook_valid_signature_ingests(client, settings):
    settings.DCSA_WEBHOOK_SECRET = SECRET
    raw = json.dumps(EVENTS).encode()
    resp = client.post(URL, data=raw, content_type="application/json",
                       headers={"Notification-Signature": _sign(raw)})
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["reference"] == "COSU9000001"
    assert body["events"] == 2
    # appears in the API
    assert client.get("/api/traceapi/trace/", {"bill_of_lading": "COSU9000001"}).json()["count"] == 1


@pytest.mark.django_db
def test_webhook_bad_signature_rejected(client, settings):
    settings.DCSA_WEBHOOK_SECRET = SECRET
    raw = json.dumps(EVENTS).encode()
    resp = client.post(URL, data=raw, content_type="application/json",
                       headers={"Notification-Signature": "deadbeef"})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_webhook_missing_reference(client, settings):
    settings.DCSA_WEBHOOK_SECRET = SECRET
    payload = [{"eventType": "SHIPMENT", "eventClassifierCode": "ACT",
                "eventDateTime": "2026-06-17T00:00:00Z", "shipmentEventTypeCode": "RECE"}]
    raw = json.dumps(payload).encode()
    resp = client.post(URL, data=raw, content_type="application/json",
                       headers={"Notification-Signature": _sign(raw)})
    assert resp.status_code == 422


@pytest.mark.django_db
def test_webhook_get_not_allowed(client, settings):
    settings.DCSA_WEBHOOK_SECRET = SECRET
    assert client.get(URL).status_code == 405


# ---- air webhook ----
AIR_URL = "/api/feeds/air/webhook/"
AIR_PAYLOAD = {
    "awb": "160-22334454",
    "carrier": {"name": "Cathay Cargo", "prefix": "160"},
    "origin": "HKG", "destination": "ORD", "pieces": 1080, "weightKg": 742.5,
    "events": [
        {"statusCode": "RCS", "airport": "HKG", "timestamp": "2026-06-10T01:30:00+08:00"},
        {"statusCode": "DEP", "airport": "HKG", "flight": "CX846", "timestamp": "2026-06-10T08:05:00+08:00"},
        {"statusCode": "ARR", "airport": "ORD", "flight": "CX846", "timestamp": "2026-06-10T11:25:00-05:00"},
    ],
}


@pytest.mark.django_db
def test_air_webhook_valid_signature_ingests(client, settings):
    settings.AIR_WEBHOOK_SECRET = SECRET
    raw = json.dumps(AIR_PAYLOAD).encode()
    resp = client.post(AIR_URL, data=raw, content_type="application/json",
                       headers={"X-Signature": _sign(raw)})
    assert resp.status_code == 200, resp.content
    body = resp.json()
    assert body["awb"] == "16022334454"
    assert body["events"] == 3
    api = client.get("/api/traceapi/trace/", {"awb_number": "160-22334454"}).json()
    assert api["count"] == 1 and api["results"][0]["mode"] == "air"


@pytest.mark.django_db
def test_air_webhook_merge_advances_status(client, settings):
    settings.AIR_WEBHOOK_SECRET = SECRET
    raw = json.dumps(AIR_PAYLOAD).encode()
    client.post(AIR_URL, data=raw, content_type="application/json",
                headers={"X-Signature": _sign(raw)})
    delta = {"awb": "160-22334454",
             "events": [{"statusCode": "DLV", "airport": "ORD", "timestamp": "2026-06-11T14:20:00-05:00"}]}
    draw = json.dumps(delta).encode()
    resp = client.post(AIR_URL, data=draw, content_type="application/json",
                       headers={"X-Signature": _sign(draw)})
    assert resp.status_code == 200
    assert resp.json()["events"] == 4   # merged, not replaced
    r = client.get("/api/traceapi/trace/", {"awb_number": "160-22334454"}).json()["results"][0]
    assert r["status"] == "delivered"


@pytest.mark.django_db
def test_air_webhook_bad_signature(client, settings):
    settings.AIR_WEBHOOK_SECRET = SECRET
    raw = json.dumps(AIR_PAYLOAD).encode()
    resp = client.post(AIR_URL, data=raw, content_type="application/json",
                       headers={"X-Signature": "bad"})
    assert resp.status_code == 401


@pytest.mark.django_db
def test_air_webhook_missing_awb(client, settings):
    settings.AIR_WEBHOOK_SECRET = SECRET
    raw = json.dumps({"events": [{"statusCode": "DLV", "airport": "ORD",
                                  "timestamp": "2026-06-11T00:00:00Z"}]}).encode()
    resp = client.post(AIR_URL, data=raw, content_type="application/json",
                       headers={"X-Signature": _sign(raw)})
    assert resp.status_code == 422
