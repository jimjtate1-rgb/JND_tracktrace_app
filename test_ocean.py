from django.conf import settings

from tracktrace.feeds.aircargo import AirCargoFeed
from tracktrace.feeds.base import CarrierFeed, FeedError
from tracktrace.feeds.dcsa import DcsaFeed
from tracktrace.feeds.trackcargo import TrackCargoFeed

FEEDS: dict[str, type[CarrierFeed]] = {
    DcsaFeed.name: DcsaFeed,            # ocean, direct carrier (DCSA v2)
    AirCargoFeed.name: AirCargoFeed,    # air, direct (IATA Cargo-IMP FSU)
    TrackCargoFeed.name: TrackCargoFeed,  # ocean + air aggregator (one key)
}

# Per-reference default when --provider isn't given.
DEFAULT_PROVIDER_BY_REF = {
    "bol": "dcsa", "booking": "dcsa", "container": "dcsa", "awb": "aircargo",
}


def default_provider(reference_type: str) -> str:
    """Global FEED_PROVIDER override (e.g. 'trackcargo') wins, else per-reference default."""
    forced = (getattr(settings, "FEED_PROVIDER", "") or "").strip()
    if forced in FEEDS:
        return forced
    return DEFAULT_PROVIDER_BY_REF.get(reference_type, "dcsa")


def get_feed(name: str) -> CarrierFeed:
    try:
        return FEEDS[name]()
    except KeyError:
        raise FeedError(f"Unknown feed provider '{name}'. Available: {', '.join(sorted(FEEDS))}.")
