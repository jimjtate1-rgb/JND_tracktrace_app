"""
Air waybill (AWB) prefix -> airline, with each airline's cargo-tracking site.

An AWB is `PPP-NNNNNNNC`: the first 3 digits (PPP) are the IATA airline prefix.
Like track-trace.com/aircargo, we use that prefix to send the user straight to the
right airline's cargo tracking. Cargo-portal URLs are the carriers' own sites
(as listed on track-trace.com); extend this map to cover more airlines.
"""
from __future__ import annotations

# prefix: (airline name, IATA code, cargo tracking URL)
AIRLINE_PREFIXES: dict[str, tuple[str, str, str]] = {
    "001": ("American Airlines Cargo", "AA", "https://www.aacargo.com/"),
    "006": ("Delta Cargo", "DL", "https://www.deltacargo.com/"),
    "012": ("Delta Cargo (ex-Northwest)", "DL", "https://www.deltacargo.com/"),
    "014": ("Air Canada Cargo", "AC", "https://www.aircanada.com/cargo/en/"),
    "016": ("United Cargo", "UA", "https://www.unitedcargo.com/"),
    "020": ("Lufthansa Cargo", "LH", "https://lufthansa-cargo.com/"),
    "023": ("FedEx", "FX", "https://www.fedex.com/en-us/tracking.html"),
    "027": ("Alaska Air Cargo", "AS", "https://www.alaskacargo.com/"),
    "045": ("LATAM Cargo", "LA", "https://www.latamcargo.com/"),
    "055": ("ITA Airways Cargo", "AZ", "https://www.ita-airways-cargo.com/"),
    "057": ("Air France-KLM (AF-KL-MP) Cargo", "AF", "https://www.afklcargo.com/"),
    "065": ("Saudia Cargo", "SV", "https://saudiacargo.com/"),
    "071": ("Ethiopian Cargo", "ET", "https://cargo.ethiopianairlines.com/"),
    "074": ("Air France-KLM (KLM) Cargo", "KL", "https://www.afklcargo.com/"),
    "075": ("IAG Cargo (Iberia)", "IB", "https://www.iagcargo.com/"),
    "076": ("Middle East Airlines", "ME", "https://www.mea.com.lb/english/plan-and-book/cargo"),
    "077": ("EgyptAir Cargo", "MS", "https://www.egyptair.com/"),
    "079": ("Philippine Airlines Cargo", "PR", "https://cargo.pal.com.ph/"),
    "080": ("LOT Polish Cargo", "LO", "https://www.lot.com/cargo"),
    "081": ("Qantas Freight", "QF", "https://freight.qantas.com/"),
    "086": ("Air New Zealand Cargo", "NZ", "https://www.airnewzealandcargo.com/"),
    "098": ("Air India Cargo", "AI", "https://cargo.airindia.com/"),
    "112": ("China Cargo Airlines", "CK", "https://www.ckair.com/"),
    "117": ("SAS Cargo", "SK", "https://www.sascargo.com/"),
    "125": ("IAG Cargo (British Airways)", "BA", "https://www.iagcargo.com/"),
    "129": ("Martinair Cargo", "MP", "https://www.afklcargo.com/"),
    "131": ("Japan Airlines (JAL) Cargo", "JL", "https://www.jal.co.jp/en/jalcargo/"),
    "139": ("Aeroméxico Cargo", "AM", "https://amcargo.aeromexico.com/"),
    "157": ("Qatar Airways Cargo", "QR", "https://www.qrcargo.com/"),
    "160": ("Cathay Cargo", "CX", "https://www.cathaycargo.com/"),
    "172": ("Cargolux", "CV", "https://www.cargolux.com/"),
    "176": ("Emirates SkyCargo", "EK", "https://www.skycargo.com/"),
    "180": ("Korean Air Cargo", "KE", "https://cargo.koreanair.com/"),
    "203": ("Cebu Pacific Cargo", "5J", "https://www.cebupacificair.com/"),
    "205": ("ANA Cargo", "NH", "https://www.anacargo.jp/en/int/"),
    "214": ("Pakistan International (PIA) Cargo", "PK", "https://www.piac.com.pk/"),
    "217": ("Thai Airways Cargo", "TG", "https://www.thaicargo.com/"),
    "229": ("Kuwait Airways Cargo", "KU", "https://www.kuwaitairways.com/"),
    "230": ("Copa Airlines Cargo", "CM", "https://www.copacargo.com/"),
    "232": ("MASkargo (Malaysia)", "MH", "https://www.maskargo.com/"),
    "235": ("Turkish Cargo", "TK", "https://www.turkishcargo.com/en"),
    "279": ("JetBlue Cargo", "B6", "https://www.jetblue.com/help/cargo"),
    "288": ("Air Hong Kong", "LD", "https://www.airhongkong.com.hk/"),
    "297": ("China Airlines Cargo", "CI", "https://cargo.china-airlines.com/"),
    "356": ("Cargolux Italia", "C8", "https://www.cargolux-italia.com/"),
    "403": ("Polar Air Cargo", "PO", "https://www.polaraircargo.com/"),
    "465": ("Air Astana Cargo", "KC", "https://airastana.com/"),
    "479": ("Shenzhen Airlines Cargo", "ZH", "http://cargo.shenzhenair.com/"),
    "489": ("Cargojet", "W8", "https://cargojet.com/"),
    "512": ("Royal Jordanian Cargo", "RJ", "https://rj-cargo.com/"),
    "580": ("AirBridgeCargo", "RU", "https://www.airbridgecargo.com/"),
    "607": ("Etihad Cargo", "EY", "https://www.etihadcargo.com/"),
    "615": ("DHL Aviation (EAT)", "QY", "https://aviationcargo.dhl.com/"),
    "618": ("Singapore Airlines Cargo", "SQ", "https://www.siacargo.com/"),
    "695": ("EVA Air Cargo", "BR", "https://www.brcargo.com/"),
    "706": ("Kenya Airways Cargo", "KQ", "https://www.kqcargo.com/"),
    "716": ("MNG Airlines", "MB", "https://www.mngairlines.com/"),
    "724": ("Swiss WorldCargo", "LX", "https://www.swissworldcargo.com/"),
    "738": ("Vietnam Airlines Cargo", "VN", "https://www.vietnamairlines.com/cargo"),
    "774": ("Shanghai Airlines", "FM", "https://www.ckair.com/"),
    "781": ("China Eastern Cargo", "MU", "https://www.ceaircargo.com/"),
    "784": ("China Southern Cargo", "CZ", "https://tang.csair.com/Index.aspx?lan=en-us"),
    "881": ("Condor", "DE", "https://www.condor.com/"),
    "910": ("Oman Air Cargo", "WY", "https://cargo.omanair.com/"),
    "923": ("Corsair Cargo", "SS", "https://www.corsair.fr/"),
    "933": ("Nippon Cargo Airlines", "KZ", "https://www.nca.aero/e/"),
    "936": ("DHL Aviation", "D0", "https://aviationcargo.dhl.com/"),
    "988": ("Asiana Cargo", "OZ", "https://www.asianacargo.com/home.do?lang=en"),
    "996": ("Air Europa Cargo", "UX", "https://cargo.aireuropa.com/"),
    "999": ("Air China Cargo", "CA", "https://www.airchinacargo.com/en/"),
}


def lookup(prefix: str):
    """Return (name, iata, url) for a 3-digit prefix, or None."""
    return AIRLINE_PREFIXES.get(prefix)


def airlines_sorted() -> list[dict]:
    """All supported airlines (for the manual picker), sorted by name."""
    out = [{"prefix": p, "name": n, "iata": i, "url": u}
           for p, (n, i, u) in AIRLINE_PREFIXES.items()]
    out.sort(key=lambda a: a["name"].lower())
    return out
