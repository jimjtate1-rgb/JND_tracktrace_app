"""
Inbound DCSA Subscription Callback receiver.

DCSA T&T v2.2 carriers push event notifications to a callback URL you register.
Each request carries a `Notification-Signature` (HMAC-SHA256 of the raw body using
the secret shared at subscription time) and a `Subscription-ID`. We verify the
signature, parse the pushed events, and ingest them — so shipments update
automatically instead of being polled.

Signature header name / algorithm can vary slightly by carrier; both are
configurable. Verify against your carrier's DCSA version.
"""
import hashlib
import hmac
import json
import re

from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from tracktrace.feeds.aircargo import AirCargoFeed
from tracktrace.feeds.dcsa import DcsaFeed
from tracktrace.feeds.ingest import ingest_shipment


def verify_signature(raw_body: bytes, header_value: str, secret: str) -> bool:
    """Constant-time HMAC-SHA256 check of the raw request body."""
    if not secret or not header_value:
        return False
    expected = hmac.new(secret.encode(), raw_body, hashlib.sha256).hexdigest()
    candidate = header_value.strip().lower()
    # Accept "sha256=<hex>" or bare hex.
    if candidate.startswith("sha256="):
        candidate = candidate[len("sha256="):]
    return hmac.compare_digest(expected, candidate)


@csrf_exempt
@require_POST
def dcsa_webhook(request):
    raw = request.body
    secret = settings.DCSA_WEBHOOK_SECRET
    sig = request.headers.get(settings.DCSA_WEBHOOK_SIGNATURE_HEADER, "")

    if secret:
        if not verify_signature(raw, sig, secret):
            return JsonResponse({"detail": "invalid signature"}, status=401)
    elif not settings.DEBUG:
        # Refuse unauthenticated callbacks outside local development.
        return JsonResponse({"detail": "webhook secret not configured"}, status=503)

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)

    events = DcsaFeed._extract_events(payload)
    if not events:
        return JsonResponse({"detail": "no events in payload"}, status=422)

    ref_type, reference = DcsaFeed.extract_reference(events)
    if not reference:
        return JsonResponse({"detail": "no shipment reference found in events"}, status=422)

    normalized = DcsaFeed.parse(
        events, reference=reference, reference_type=ref_type,
        carrier_name=settings.DCSA_CARRIER_NAME, carrier_code=settings.DCSA_CARRIER_SCAC,
    )
    shipment, created = ingest_shipment(normalized, replace_events=False)
    return JsonResponse({
        "status": "accepted",
        "reference": reference,
        "reference_type": ref_type,
        "created": created,
        "events": shipment.events.count(),
        "subscription_id": request.headers.get("Subscription-ID"),
    }, status=200)


@csrf_exempt
@require_POST
def air_webhook(request):
    """
    Inbound air-cargo status callback (IATA Cargo-IMP FSU model).

    Air has no single standard callback spec, so this is a generic HMAC-signed
    receiver: it accepts the same air-waybill JSON the air feed consumes, verifies
    the signature, derives the AWB from the payload, and merges the FSU events
    (status only advances; replays are no-ops). Header name / secret are
    configurable per provider.
    """
    raw = request.body
    secret = settings.AIR_WEBHOOK_SECRET
    sig = request.headers.get(settings.AIR_WEBHOOK_SIGNATURE_HEADER, "")

    if secret:
        if not verify_signature(raw, sig, secret):
            return JsonResponse({"detail": "invalid signature"}, status=401)
    elif not settings.DEBUG:
        return JsonResponse({"detail": "webhook secret not configured"}, status=503)

    try:
        payload = json.loads(raw or b"{}")
    except ValueError:
        return JsonResponse({"detail": "invalid JSON"}, status=400)
    if not isinstance(payload, dict):
        return JsonResponse({"detail": "expected an air waybill object"}, status=422)

    awb = re.sub(r"[\s-]", "", str(payload.get("awb") or payload.get("awbNumber") or ""))
    if not awb:
        return JsonResponse({"detail": "no AWB in payload"}, status=422)
    if not (payload.get("events") or payload.get("statusEvents")):
        return JsonResponse({"detail": "no status events in payload"}, status=422)

    normalized = AirCargoFeed.parse_payload(payload, reference=awb, reference_type="awb")
    shipment, created = ingest_shipment(normalized, replace_events=False)
    return JsonResponse({
        "status": "accepted",
        "awb": awb,
        "created": created,
        "events": shipment.events.count(),
    }, status=200)
