"""
Ocean BOL carriers supported by track-trace.com (66 companies), pulled from
https://touch.track-trace.com/bol on 2026-06-13.

SCAC provenance:
  * Confirmed by the source page: ANL=ANLC, APL=APLU, CMA CGM=CMDU.
  * All other SCACs below are standard public NMFTA codes filled in for the
    major carriers so prefix autodetection works on the common lanes. Carriers
    can hold multiple SCACs (and legacy ones, e.g. HMM also appears as HDMU),
    so verify against your own records / NMFTA before operational use.
  * `None` means no SCAC has been assigned here yet.

`detect_carrier()` mirrors the source's rule: the first 4 letters of a BOL or
container number identify the company.
"""

# (display name, SCAC or None) in the order track-trace lists them.
OCEAN_CARRIERS: list[tuple[str, str | None]] = [
    ("4 ELEPHANTS GROUP", None),
    ("ACL", None),
    ("ANL", "ANLC"),                     # source-confirmed
    ("APL", "APLU"),                     # source-confirmed
    ("Arkas Line", None),
    ("Bahri", None),
    ("BAL", None),
    ("Camellia Line", None),
    ("CK LINE", None),
    ("CMA CGM", "CMDU"),                 # source-confirmed
    ("COSCO SHIPPING Lines", "COSU"),
    ("Crowley", None),
    ("CULines", None),
    ("Deep Sea Routes", None),
    ("Dong Young Shipping", None),
    ("Dongjin Shipping", None),
    ("ECU Worldwide", None),
    ("Eimskip", None),
    ("Emirates Shipping Line", None),
    ("EUKOR", None),
    ("Evergreen", "EGLV"),
    ("G2 Ocean", None),
    ("Gold Star Line", None),
    ("Hapag-Lloyd", "HLCU"),
    ("Hede Shipping", None),
    ("Heung-A Line", None),
    ("HMM", "HMMU"),
    ("HNA Shipping", None),
    ("HS LINE", None),
    ("Höegh Autoliners", None),
    ("Interasia Lines", None),
    ("Jinjiang Shipping", None),
    ("Kambara Kisen", None),
    ("Korea Marine Transport", None),
    ("Laurel Navigation", None),
    ("Maersk Line", "MAEU"),
    ("Marfret", None),
    ("Margarita Shipping", None),
    ("Matson", "MATS"),
    ("Mediterranean Shipping", "MSCU"),
    ("Messina Line", None),
    ("MOL ACE", None),
    ("Namsung", None),
    ("Nirint Shipping", None),
    ("ONE", "ONEY"),
    ("OOCL", "OOLU"),
    ("Pan Continental Shipping", None),
    ("Pan Ocean", None),
    ("PIL", None),
    ("RCL", None),
    ("Samudera Shipping", None),
    ("SCI", None),
    ("Sea Hawk Lines", None),
    ("Sealand", None),
    ("SETH Shipping", None),
    ("Sinokor Merchant Marine", None),
    ("Sinotrans", None),
    ("SM Line", None),
    ("Swire Shipping", None),
    ("Swire Shipping North America", None),
    ("T.S. Lines", None),
    ("Turkon Line", None),
    ("Wallenius Wilhelmsen", None),
    ("Wan Hai Lines", "WHLC"),
    ("Yang Ming", "YMLU"),
    ("ZIM", "ZIMU"),
]

# SCAC -> carrier name (only for carriers that have a SCAC here).
SCAC_TO_CARRIER: dict[str, str] = {
    scac: name for name, scac in OCEAN_CARRIERS if scac
}


def carriers(with_scac_only: bool = False) -> list[dict]:
    return [
        {"name": name, "scac": scac}
        for name, scac in OCEAN_CARRIERS
        if scac or not with_scac_only
    ]


def detect_carrier(number: str) -> dict | None:
    """Identify a carrier from the first 4 letters of a BOL/container number."""
    cleaned = "".join(ch for ch in (number or "").upper() if ch.isalnum())
    prefix = cleaned[:4]
    name = SCAC_TO_CARRIER.get(prefix)
    if name:
        return {"name": name, "scac": prefix}
    return None
