import json
import math
import re
import sys
from datetime import datetime, timezone

import requests

# Windows konzola pogosto nima UTF-8 – naslovimo izhod
try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass

# Uradni API državnega portala Goriva.si.
# API NE sprejme "position=Nova Gorica" (vrne 0 zadetkov) – uporabiti je treba
# koordinati (lat/lon), nato pa razdaljo izračunati sami (Haversine).
API_URL = "https://goriva.si/api/v1/search/"

# Središče iskanja: Nova Gorica
CENTER_LAT = 45.9580549
CENTER_LNG = 13.6474706
RADIUS_KM = 10.0

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

# franchise id -> prikazna znamka
FRANCHISE_BRANDS = {
    1: "Petrol",
    2: "MOL",
    3: "M-ENERGIJA",
    4: "MOL",
    5: "Shell",
    6: "EKO-NAFTA",
    7: "LOGO ENERGIJA",
    9: "TehnoSTOR",
    10: "Butan plin",
}

# Črpalke ob ali na avtocesti (poimenuj "AC" ali avtocestni odsek),
# plus ročni seznam za tiste, ki imajo avtocestne cene, a tega nimajo v imenu.
HIGHWAY_EXPLICIT = {"BS MOL ŠEMPAS"}

# Slovenianski dnevi za razčlenitev urnika
DAY_ORDER = [
    "Ponedeljek", "Torek", "Sreda", "Četrtek", "Petek", "Sobota", "Nedelja",
]


def haversine_km(lat1, lng1, lat2, lng2):
    """Razdalja v km med dvema točkama na zemljevidu."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def sanitize_price(value):
    """API za nekatera goriva vrne šumno vrednost 0.001 – to NI cena."""
    try:
        p = float(value)
    except (TypeError, ValueError):
        return None
    if p < 0.1 or p > 100:
        return None
    return round(p, 3)


def compress_days(days_text):
    """'Ponedeljek, Torek, Sreda, Četrtek, Petek' -> 'Pon-Pet'."""
    tokens = [d.strip() for d in days_text.split(",") if d.strip()]
    known = [d for d in tokens if d in DAY_ORDER]
    if "Praznik" in tokens:
        known.append("Praznik")
    if not known:
        return days_text.strip()[:20]

    idx = [DAY_ORDER.index(d) for d in known if d in DAY_ORDER]
    if len(idx) == 7:
        return "Vsak dan"
    if idx and idx == list(range(idx[0], idx[0] + len(idx))) and len(idx) >= 3:
        return f"{DAY_ORDER[idx[0]][:3]}-{DAY_ORDER[idx[-1]][:3]}"
    return ", ".join(d[:3] for d in known)


def compact_hours(raw):
    """Večvrstični urnik iz API-ja pretvori v kratek enovrstični povzetek."""
    raw = (raw or "").strip()
    if not raw:
        return "Ni podatka"
    if raw.replace(" ", "") in ("24/7", "24ure"):
        return "00:00 - 24:00 (Non-stop)"

    groups = []
    cur_days, cur_hours = None, []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        if re.match(r"^\d{1,2}:\d{2}", line):
            cur_hours.append(line.replace(" ", ""))
        else:
            if cur_days is not None and cur_hours:
                groups.append((cur_days, ", ".join(cur_hours)))
            cur_days, cur_hours = line, []
    if cur_days is not None and cur_hours:
        groups.append((cur_days, ", ".join(cur_hours)))

    if not groups:
        return raw.replace("\n", " ")[:60]

    main_days, main_hours = groups[0]
    out = f"{compress_days(main_days)} {main_hours}"
    others = [h for _, h in groups[1:] if h != main_hours]
    if others:
        out += f" · drugače {others[0]}"
    return out[:80]


def is_highway_station(name, address):
    if name in HIGHWAY_EXPLICIT:
        return True
    hay = f"{name} {address}".upper()
    return " AC " in f" {hay} " or "AVTOCESTA" in hay or "H4" in hay


def build_maps_url(name, address):
    q = f"{name} {address}, Slovenija".replace(" ", "+")
    return f"https://maps.google.com/?q={q}"


def fetch_all_stations(session):
    """Prebere vse strani API-ja (paginacija)."""
    stations = []
    url = API_URL
    params = {"lat": CENTER_LAT, "lon": CENTER_LNG, "radius": RADIUS_KM}
    while url:
        resp = session.get(url, headers=HEADERS, params=params, timeout=20)
        resp.raise_for_status()
        data = resp.json()
        stations.extend(data.get("results", []))
        url = data.get("next")
        params = None  # next že vsebuje parametre
    return stations


def smart_title(text):
    """Lepo zapiše ime, pri tem pa ohrani kratice (BS, AC, H4 ...)."""
    keep_upper = {"BS", "AC", "H4", "LPG", "MOL", "FE", "CNG", "LNG", "HVO", "SHELL"}
    words = []
    for w in (text or "").split():
        if w.upper() in keep_upper:
            words.append(w.upper())
        else:
            words.append(w.capitalize())
    return " ".join(words)


def to_station_record(item, distance):
    prices_raw = item.get("prices") or {}
    franchise_id = item.get("franchise")
    brand = FRANCHISE_BRANDS.get(franchise_id, (item.get("name") or "Neznano").split()[0])
    name = item.get("name") or "Neznana črpalka"
    address = item.get("address") or ""

    return {
        "id": item.get("pk"),
        "brand": brand,
        "name": smart_title(name),
        "address": smart_title(address),
        "distance": round(distance, 1),
        "isHighway": is_highway_station(name, address),
        "hours": compact_hours(item.get("open_hours")),
        "mapsUrl": build_maps_url(name, address),
        "prices": {
            "dizel": sanitize_price(prices_raw.get("dizel")),
            "95": sanitize_price(prices_raw.get("95")),
            "100": sanitize_price(prices_raw.get("100")),
            "lpg": sanitize_price(prices_raw.get("avtoplin-lpg")),
        },
    }


def main():
    print(f"Pridobivam uradne cene z Goriva.si (radij {RADIUS_KM} km okrog Nove Gorice)...")
    session = requests.Session()

    try:
        all_stations = fetch_all_stations(session)
    except Exception as e:
        print(f"NAPAKA: API ni dosegljiv ({e}). Obstoječega cene.json NE prepišem.", file=sys.stderr)
        sys.exit(1)

    print(f"API je vrnil {len(all_stations)} črpalk v Sloveniji.")

    results = []
    for item in all_stations:
        lat, lng = item.get("lat"), item.get("lng")
        if lat is None or lng is None:
            continue
        dist = haversine_km(CENTER_LAT, CENTER_LNG, float(lat), float(lng))
        if dist <= RADIUS_KM:
            record = to_station_record(item, dist)
            # Izpusti črpalke, ki sploh nimajo nobene cene
            if any(record["prices"].values()):
                results.append(record)

    if not results:
        print("NAPAKA: API je vrnil 0 črpalk v radiju 10 km – verjetno je spremenjen format.",
              file=sys.stderr)
        sys.exit(1)

    results.sort(key=lambda s: (s["isHighway"], s["distance"]))

    output = {
        "updated": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "goriva.si (državni portal)",
        "center": {"name": "Nova Gorica", "lat": CENTER_LAT, "lng": CENTER_LNG},
        "radius_km": RADIUS_KM,
        "stations": results,
    }

    with open("cene.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"Uspešno posodobljenih {len(results)} črpalk v cene.json!")
    for s in results[:5]:
        print(f"  - {s['name']}: dizel {s['prices']['dizel']} € ({s['distance']} km)")


if __name__ == "__main__":
    main()
