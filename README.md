# JND Track & Trace

An accessible **web app + JSON API** for tracking ocean (BOL / container) and air
(AWB) freight. Enter a reference number and see status, route, milestone timeline,
cargo (with HS codes), and destination weather.

Built on the HackSoft Django-Styleguide layout. Runs on SQLite with zero external
services; PostgreSQL, Redis, Celery and OpenWeatherMap are optional.

## Website

**JND Track & Trace** — an accessible front end at `/` (Django templates + one
stylesheet + one small script, no build step). Search by BOL, booking, container,
or AWB; filter by mode or carrier; copy any reference or container number to the
clipboard with one tap.

Themes: a **Miami-neon dark theme is the default** (hot-pink/cyan on deep indigo,
glow accents), with a header toggle to a light "manifest" theme. The choice is
remembered via a cookie, applied before first paint (no flash), and degrades
silently where cookies are blocked.

Accessibility: semantic landmarks, a skip link, labelled controls, an `aria-live`
result count, a screen-reader status region that announces copy actions, visible
keyboard focus, AA-contrast status colours (never colour alone), `prefers-reduced-
motion` respected (the neon glow pulse is disabled), and it works to 320px **with
JavaScript off** — the page is server-rendered; JS only adds the theme toggle and
copy buttons. Copy uses the async Clipboard API with an `execCommand` fallback.

The JND logo appears in the header (in a white badge so it stays legible on the dark themes) and as the favicon.

`freight_tracking_preview.html` is a **standalone single-file build** (same UI,
neon theme, toggle, and copy buttons, sample data embedded) you can open in any
browser with no server.

## Endpoint

```
GET /api/traceapi/trace/?bill_of_lading=<bol>
GET /api/traceapi/trace/?container_number=<cntr>     # resolves to its ocean shipment
GET /api/traceapi/trace/?awb_number=<awb>            # dashed or plain
GET /api/traceapi/trace/?booking_number=<bkg>
GET /api/traceapi/trace/?carrier=<name-or-scac>
GET /api/traceapi/trace/?mode=ocean|air
GET /api/traceapi/trace/?search=<text>              # any ref no., carrier, port, container
GET /api/traceapi/trace/                            # paginated list (limit/offset)

GET /api/traceapi/carriers/                         # supported ocean carriers (66)
GET /api/traceapi/carriers/?with_scac=true          # only carriers with a SCAC mapped
GET /api/traceapi/carriers/?search=evergreen        # filter by name or SCAC
GET /api/traceapi/carriers/?detect=CMDU1234567      # identify carrier from BOL/container prefix
```

Example — ocean by BOL:

```bash
curl "http://127.0.0.1:8000/api/traceapi/trace/?bill_of_lading=MAEU562301487"
```

```jsonc
{
  "limit": 10, "offset": 0, "count": 1, "next": null, "previous": null,
  "results": [{
    "mode": "ocean",
    "status": "in-transit",
    "carrier": {"name": "Maersk", "code": "MAEU"},
    "references": {"bill_of_lading": "MAEU562301487", "booking_number": "562301487", "awb_number": null},
    "shipper":   {"name": "...", "address": "..."},
    "consignee": {"name": "...", "address": "..."},
    "origin":      {"port": "Shanghai", "code": "CNSHA", "country": "China"},
    "destination": {"port": "Los Angeles", "code": "USLAX", "country": "United States", "city": "Los Angeles"},
    "transport": {"vessel": "MAERSK EMDEN", "voyage": "512W", "etd": "2026-06-01", "eta": "2026-06-20"},
    "containers": [{"number": "MSKU0762594", "type": "40HC", "seal": "ML-AX88231"}, ...],
    "cargo": [{"description": "LED illuminated signage", "hs_code": "9405.61.6000", "pieces": 320, "weight_kg": 4180.0}, ...],
    "events": [{"datetime": "2026-06-01T14:00:00+00:00", "code": "LOAD", "description": "Loaded on vessel",
                "location": "Shanghai", "location_code": "CNSHA", "vessel_or_flight": "MAERSK EMDEN 512W", "estimated": false}, ...],
    "weather": {"temperature": 295.4, "wind_speed": 3.1}
  }]
}
```

Air responses use the same envelope: `references.awb_number` is set,
`transport.flight_number` replaces vessel/voyage, and `containers` is `[]`.

Website at `/`. Swagger UI at `/api/docs/`, OpenAPI schema at `/api/schema/`.

## Supported carriers

`tracktrace/traceapi/carriers.py` holds the **66 ocean BOL carriers** supported by
[track-trace.com](https://touch.track-trace.com/bol), exposed via
`GET /api/traceapi/carriers/`. `?detect=<number>` mirrors track-trace's rule that
the first 4 letters of a BOL/container number identify the company (SCAC-based).

SCAC provenance: `ANL=ANLC`, `APL=APLU`, `CMA CGM=CMDU` are confirmed by the source
page. The other 12 (Maersk, MSC, COSCO, Hapag-Lloyd, ONE, Evergreen, OOCL, Yang Ming,
HMM, ZIM, Wan Hai, Matson) are standard public NMFTA SCACs filled in for the majors.
Carriers can hold multiple/legacy SCACs (e.g. HMM also appears as HDMU), so verify
against NMFTA / your own records before operational use. The remaining carriers have
`scac: null` until you map them.

## Live carrier feeds (ocean + air)

Tracking data is pulled through a provider abstraction (`tracktrace/feeds/`). Add a
provider = one `CarrierFeed` subclass returning a `NormalizedShipment`; the ingest
service and API don't change.

**Ocean — DCSA Track & Trace v2** (`dcsa`). The vendor-neutral standard implemented
by Maersk, Hapag-Lloyd, CMA CGM, COSCO, ONE, Evergreen, Yang Ming, HMM and ZIM, so
one adapter spans carriers. Tracks by BOL / booking / container.

**Air — IATA Cargo-IMP FSU** (`aircargo`). Consumes air-waybill status events whose
codes (RCS, MAN, DEP, ARR, RCF, NFD, DLV, …) are the universal air-cargo vocabulary
(modern REST successors: Cargo-XML, IATA ONE Record). Tracks by AWB.

Configure in `.env`:

```
# ocean
DCSA_BASE_URL=https://api.<carrier>.com/dcsa/tnt/v2
DCSA_API_KEY=<carrier developer-portal key>
DCSA_API_KEY_HEADER=API-Key
DCSA_CARRIER_NAME=COSCO Shipping
DCSA_CARRIER_SCAC=COSU
# air
AIR_FEED_BASE_URL=https://<air-provider>/v1
AIR_FEED_API_KEY=<key>
```

Pull a shipment (provider auto-selected from the reference; idempotent):

```bash
python manage.py pull_shipment --bol COSU6229185001 --scac COSU --carrier "COSCO Shipping"
python manage.py pull_shipment --container CSNU6229185
python manage.py pull_shipment --awb 160-22334454 --carrier "Cathay Cargo"
```

Try the whole pipeline **offline** with the bundled samples (no key, no network):

```bash
python manage.py pull_shipment --sample tracktrace/feeds/samples/dcsa_events_sample.json --bol COSU6229185001 --scac COSU --carrier "COSCO Shipping"
python manage.py pull_shipment --sample tracktrace/feeds/samples/aircargo_fsu_sample.json --awb 160-22334454 --carrier "Cathay Cargo"
```

What feeds populate vs. not: they derive route, vessel/voyage or flight, ETD/ETA,
containers (ocean), a cargo line from AWB piece/weight (air), the milestone timeline
and a status. Ocean T&T feeds do **not** include shipper/consignee or cargo line
items (those live in gated Booking / Shipping-Instruction APIs), so those stay blank.

### Auto-updates via webhooks (ocean + air)

Instead of polling, register a DCSA **subscription** so the carrier pushes events to
our callback. Inbound endpoint: `POST /api/feeds/dcsa/webhook/`.

- Each callback is verified with `Notification-Signature` (HMAC-SHA256 of the raw
  body using the secret shared at subscription time); bad signatures get 401.
- Pushed events are parsed, the shipment reference is derived from them, and events
  are **merged** (new ones appended, status only advanced) — so deltas don't erase
  history. Replaying a callback is a no-op.

```
DCSA_WEBHOOK_SECRET=<secret from subscription>
DCSA_WEBHOOK_SIGNATURE_HEADER=Notification-Signature
```

Register the subscription (carrier → your webhook):

```bash
python manage.py dcsa_subscribe --callback-url https://<your-host>/api/feeds/dcsa/webhook/ --bol COSU6229185001
```

Air works the same way at `POST /api/feeds/air/webhook/` — an HMAC-signed FSU
callback (air has no single standard callback spec, so the header/secret are
configurable). It derives the AWB from the payload and merges status events.

```
AIR_WEBHOOK_SECRET=<secret from your air provider>
AIR_WEBHOOK_SIGNATURE_HEADER=X-Signature
```

```bash
python manage.py air_subscribe --callback-url https://<your-host>/api/feeds/air/webhook/ --awb 160-22334454
```

Getting keys: each carrier runs its own developer portal; public API-key access
returns standard equipment/transport moves + planned dates, private (OAuth2) access
adds inland/rail moves and is gated to parties on the booking. Spec:
github.com/dcsaorg/DCSA-OpenAPI.

### Aggregator: TrackCargo (ocean + air, one key)

TrackCargo covers ocean (BL / booking / container) and air (AWB) through a single
key, so it's the simplest way to track real shipments across many carriers. It's
**asynchronous**: you submit a reference (creates a tracking order), TrackCargo
fetches from the carrier, and data arrives over time (ocean refreshes ~daily, air
~2-hourly) — it can also push updates to a webhook.

Setup:
1. Sign up at trackcargo.co, get an API key.
2. In Render → the web service → **Environment**, add:
   `TRACKCARGO_API_KEY=<key>` and `FEED_PROVIDER=trackcargo` (routes all lookups to it).
3. Redeploy. Add a shipment from the service **Shell**:
   `python manage.py pull_shipment --bol <real BOL>` (or `--container` / `--awb`).
   The first call may be "pending" (async) — run again shortly, or set up the webhook.
4. (Optional) In TrackCargo, point a webhook at
   `https://<your-app>.onrender.com/api/feeds/trackcargo/webhook/`, and set
   `TRACKCARGO_WEBHOOK_SECRET` so updates verify and flow in automatically.

Finalising the field mapping: TrackCargo's exact JSON field names aren't published,
so `trackcargo.py` maps them tolerantly. To lock it to reality, run
`python manage.py trackcargo_probe --bol <real BOL>` and share the printed JSON —
the mapping is centralised in `TrackCargoFeed.parse_payload`.

### Air cargo router (track-trace.com/aircargo-style)

`/aircargo` behaves like track-trace.com/aircargo: enter an AWB and it reads the
first 3 digits (the IATA airline prefix) to send you straight to that airline's
cargo tracking — free, instant, no API key. About 70 airlines are mapped in
`tracktrace/web/airlines.py` (the China->US lane plus major freighters); an
unrecognised prefix shows a manual airline picker, and an invalid check digit
warns before routing. The same prefix-routing can be added for ocean container/BL
using the SCAC detection already in `carriers.py`.

### Ocean router (container & B/L)

`/ocean` is the ocean counterpart of the air-cargo router: enter a container or
B/L number and it reads the first 4 letters to send you to the shipping line's
tracking. A container number is `AAAU1234567` (an ISO 6346 owner prefix such as
`MSKU` = Maersk); a B/L usually starts with the line's SCAC (such as `MEDU` = MSC).
`tracktrace/web/shipping_lines.py` maps ~21 lines, each with its SCAC plus common
container prefixes (Maersk, MSC, CMA CGM, COSCO, Hapag-Lloyd, ONE, Evergreen, OOCL,
Yang Ming, HMM, ZIM, PIL, Wan Hai, Matson, and more). A genuine 11-character
container number with a bad ISO check digit is flagged as a likely typo (with a
"track anyway" link) instead of silently routing; unknown prefixes show a manual
picker. Free, instant, no API key — same as the air router.

## Run it (SQLite, no Docker needed)

```bash
python -m venv venv && source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
python manage.py migrate
python manage.py seed_data        # 2 ocean + 2 air sample shipments (China -> US)
python manage.py runserver        # website: http://127.0.0.1:8000/
pytest                            # 42 tests
```

## Optional: PostgreSQL + live weather + scheduled refresh

1. `cp .env.example .env` and fill in values.
2. `DATABASE_URL=psql://user:pass@host:5432/db` to use PostgreSQL.
3. `WEATHER_API_KEY=...` (https://openweathermap.org/api). Without it, weather
   fetching is skipped and any seeded weather is still returned. Only the
   destinations of non-delivered shipments are refreshed, at most once / 2h.
4. With `REDIS_LOCATION` set, run the scheduled refresh:
   ```bash
   python manage.py setup_periodic_tasks
   celery -A config worker -l info
   celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
   ```

## Layout

```
config/                 settings, urls, wsgi, celery app
tracktrace/
  common/models.py      BaseModel (created_at / updated_at)
  api/pagination.py     LimitOffsetPagination + paginated-response helper
  weather/
    models.py           Weather (per destination city)
    services.py         OpenWeatherMap client + 2-hour refresh logic
    tasks.py            weather_update Celery task
    management/commands/setup_periodic_tasks.py
  traceapi/
    models.py           Shipment, Container, CargoItem, TrackingEvent
    validators.py       ISO 6346 + IATA AWB check-digit validation
    carriers.py         66 track-trace.com ocean carriers + SCAC autodetect
    filters.py          mode / BOL / booking / container / AWB / carrier / search
    selectors.py        get_traces + container/cargo/event serializers (read layer)
    apis.py             TraceApi + CarrierListApi (thin views)
    urls.py, admin.py
    management/commands/seed_data.py
  web/                  accessible front end
    views.py            track_view (server-rendered search + results)
    templates/web/      base.html, index.html
    static/web/         styles.css, app.js, jnd-logo.png (brand logo + favicon)
  feeds/                live carrier-feed integration
    base.py             CarrierFeed interface + NormalizedShipment
    dcsa.py             DCSA Track & Trace v2 adapter (ocean)
    aircargo.py         IATA Cargo-IMP FSU adapter (air)
    ingest.py           idempotent upsert (replace for polling, merge for webhooks)
    webhooks.py         signed DCSA + air FSU callback receivers (merge mode)
    registry.py         provider lookup + default-by-reference
    urls.py             /api/feeds/{dcsa,air}/webhook/
    samples/            offline DCSA + air FSU payloads for --sample
    management/commands/  pull_shipment, dcsa_subscribe, air_subscribe
  tests/                pytest API + validator + feed tests
```

`freight_tracking_preview.html` (repo root) is a standalone, no-server demo of the same UI.

## Notes / extending

- One BOL → many containers is modelled (`Container` FK); look up by either.
- Free-text `search` uses case-insensitive matching so it's identical on SQLite
  and PostgreSQL. For production scale, add a Postgres `SearchVector` + GIN index.
- Events carry an `estimated` flag (planned vs actual) so ETAs and actuals share
  one timeline.
- To plug in real carrier feeds later, add a `services.py` per integration
  (e.g. a DCSA-standard ocean feed, or a Cargo-IMP/Cargo-XML air feed) that
  writes `TrackingEvent` rows; the API layer doesn't change.

## Deploy live on Render

This repo is Render-ready: `gunicorn` (prod server), WhiteNoise (serves the
CSS/JS/logo with `DEBUG=False`), a `render.yaml` blueprint, and `CSRF_TRUSTED_ORIGINS`
wired for the live domain.

1. Push this repo to GitHub.
2. In Render: **New → Blueprint**, connect the repo. It reads `render.yaml` and
   provisions a web service + a Postgres database, sets `DEBUG=False`, generates a
   `SECRET_KEY`, and wires `DATABASE_URL` automatically.
3. The build installs deps and runs `collectstatic`; on startup the service runs
   `migrate` and seeds the sample shipments, then starts gunicorn.
   The site comes up at `https://<your-app>.onrender.com` — `ALLOWED_HOSTS` and
   `CSRF_TRUSTED_ORIGINS` pick that hostname up on their own.
4. (Optional) Open the service **Shell** and run `python manage.py createsuperuser`
   for `/admin`. The sample shipments are seeded automatically on the first deploy:
   the build runs `seed_data --if-empty`, which seeds only an empty database and is a
   no-op on later deploys, so it never wipes real data. To launch with an empty
   database instead, drop `python manage.py seed_data --if-empty &&` from
   `startCommand` in `render.yaml`.

Going live with real carrier data: add `DCSA_BASE_URL` / `DCSA_API_KEY` /
`DCSA_WEBHOOK_SECRET` and the `AIR_FEED_*` / `AIR_WEBHOOK_*` keys under the service's
**Environment**. Your webhook endpoints are then:

```
https://<your-app>.onrender.com/api/feeds/dcsa/webhook/
https://<your-app>.onrender.com/api/feeds/air/webhook/
```

Caveats on the free plan: the web service sleeps after ~15 min idle (first request
then takes 30–50s to wake), and Render's free Postgres is removed after ~30 days —
upgrade the `databases` plan in `render.yaml` to keep data long-term. The $7/mo
Starter web plan removes the sleep.
