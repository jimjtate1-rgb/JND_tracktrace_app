from tracktrace.feeds.aircargo import AirCargoFeed
from tracktrace.feeds.base import CarrierFeed, FeedError
from tracktrace.feeds.dcsa import DcsaFeed

FEEDS: dict[str, type[CarrierFeed]] = {
    DcsaFeed.name: DcsaFeed,          # ocean (DCSA Track & Trace v2)
    AirCargoFeed.name: AirCargoFeed,  # air (IATA Cargo-IMP FSU)
}

# Default provider per reference type (used when --provider isn't given).
DEFAULT_PROVIDER_BY_REF = {
    "bol": "dcsa", "booking": "dcsa", "container": "dcsa", "awb": "aircargo",
}


def get_feed(name: str) -> CarrierFeed:
    try:
        return FEEDS[name]()
    except KeyError:
        raise FeedError(f"Unknown feed provider '{name}'. Available: {', '.join(sorted(FEEDS))}.")
