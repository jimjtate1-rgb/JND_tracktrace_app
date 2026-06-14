"""
Container / B/L prefix -> shipping line, with each line's tracking page.

Ocean numbers identify the line by their first 4 letters: a container number is
`AAAU1234567` (an ISO 6346 owner prefix such as MSKU = Maersk), and a bill of
lading usually starts with the carrier's SCAC (such as MEDU = MSC). Like
track-trace.com/container, we read those 4 letters and send the user to the right
line's tracking. Each line lists the SCAC plus its common container owner prefixes.

Prefixes cover the major lines on the China->US lane and global majors; a carrier
can hold several prefixes (and legacy ones from mergers), so verify against your
own records before operational use. Unrecognised prefixes fall back to a manual
picker, exactly like the air-cargo router.
"""
from __future__ import annotations

# name, SCAC, tracking URL, [4-letter prefixes: SCAC + container owner codes]
SHIPPING_LINES: list[dict] = [
    {"name": "Maersk Line", "scac": "MAEU", "url": "https://www.maersk.com/tracking",
     "prefixes": ["MAEU", "MSKU", "MRKU", "MSWU", "MRSU", "MNBU", "PONU"]},
    {"name": "Mediterranean Shipping (MSC)", "scac": "MEDU", "url": "https://www.msc.com/en/track-a-shipment",
     "prefixes": ["MEDU", "MSCU", "MSDU", "MSMU", "MSNU"]},
    {"name": "CMA CGM", "scac": "CMDU", "url": "https://www.cma-cgm.com/ebusiness/tracking/search",
     "prefixes": ["CMDU", "CMAU", "CGMU"]},
    {"name": "APL", "scac": "APLU", "url": "https://www.apl.com/ebusiness/tracking",
     "prefixes": ["APLU", "APZU"]},
    {"name": "CNC Line", "scac": "CNCU", "url": "https://www.cnc-line.com/",
     "prefixes": ["CNCU"]},
    {"name": "ANL", "scac": "ANLC", "url": "https://www.anl.com.au/",
     "prefixes": ["ANLC", "ANLU"]},
    {"name": "COSCO SHIPPING Lines", "scac": "COSU", "url": "https://elines.coscoshipping.com/ebusiness/cargoTracking",
     "prefixes": ["COSU", "CBHU", "CCLU", "CSNU"]},
    {"name": "OOCL", "scac": "OOLU", "url": "https://www.oocl.com/eng/ourservices/eservices/cargotracking/",
     "prefixes": ["OOLU", "OOCU"]},
    {"name": "Hapag-Lloyd", "scac": "HLCU", "url": "https://www.hapag-lloyd.com/en/online-business/track/track-by-container-solution.html",
     "prefixes": ["HLCU", "HLXU", "HLBU", "HPLU", "UACU"]},
    {"name": "Ocean Network Express (ONE)", "scac": "ONEY", "url": "https://ecomm.one-line.com/one-ecom/manage-shipment/cargo-tracking",
     "prefixes": ["ONEY", "ONEU", "NYKU", "MOLU", "KKLU"]},
    {"name": "Evergreen", "scac": "EGLV", "url": "https://www.evergreen-marine.com/",
     "prefixes": ["EGLV", "EGHU", "EISU", "EITU", "EMCU"]},
    {"name": "Yang Ming", "scac": "YMLU", "url": "https://www.yangming.com/e-service/Track_Trace/track_trace_cargo.aspx",
     "prefixes": ["YMLU", "YMMU"]},
    {"name": "HMM", "scac": "HDMU", "url": "https://www.hmm21.com/",
     "prefixes": ["HDMU", "HMMU"]},
    {"name": "ZIM", "scac": "ZIMU", "url": "https://www.zim.com/tools/track-a-shipment",
     "prefixes": ["ZIMU", "ZCSU"]},
    {"name": "Pacific International Lines (PIL)", "scac": "PCIU", "url": "https://www.pilship.com/",
     "prefixes": ["PCIU"]},
    {"name": "Wan Hai Lines", "scac": "WHLC", "url": "https://www.wanhai.com/views/cargoTrack/CargoTrack.xhtml",
     "prefixes": ["WHLC", "WHLU", "WHSU"]},
    {"name": "Matson", "scac": "MATS", "url": "https://www.matson.com/",
     "prefixes": ["MATS", "MATU"]},
    {"name": "SM Line", "scac": "SMLM", "url": "https://www.smlines.com/",
     "prefixes": ["SMLM", "SMLU"]},
    {"name": "T.S. Lines", "scac": "TSLU", "url": "https://www.tslines.com/",
     "prefixes": ["TSLU"]},
    {"name": "Korea Marine Transport (KMTC)", "scac": "KMTU", "url": "http://www.kmtc.co.kr/",
     "prefixes": ["KMTU"]},
    {"name": "SITC", "scac": "SITU", "url": "http://www.sitcline.com/",
     "prefixes": ["SITU"]},
]

# prefix -> line (first match wins)
PREFIX_TO_LINE: dict[str, dict] = {p: line for line in SHIPPING_LINES for p in line["prefixes"]}


def lookup_line(prefix: str):
    """Return the line dict for a 4-letter prefix, or None."""
    return PREFIX_TO_LINE.get((prefix or "").upper())


def lines_sorted() -> list[dict]:
    """All supported lines (for the manual picker), sorted by name."""
    return sorted(SHIPPING_LINES, key=lambda l: l["name"].lower())
