import json
import requests

# Uradni API državnega portala Goriva.si za radij 10 km okrog Nove Gorice
API_URL = "https://goriva.si/api/v1/search/?position=Nova+Gorica&radius=10"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json"
}

# Seznam ključnih postaj na Goriškem s fiksnimi podatki za prikaz
LOCAL_STATIONS = [
    {
        "id": 1,
        "name_match": "Šempeter pri Gorici",
        "brand_match": "FE",
        "brand": "FE-Trading (Hofer)",
        "name": "FE-Trading Šempeter pri Gorici",
        "address": "Cesta Prekomorskih brigad 4, Šempeter",
        "distance": 3.8,
        "isHighway": False,
        "hours": "00:00 - 24:00 (Avtomat)",
        "mapsUrl": "https://maps.google.com/?q=FE+Trading+Hofer+Šempeter+pri+Gorici",
        "fallback_prices": {"dizel": 1.489, "95": 1.469, "100": None, "lpg": None}
    },
    {
        "id": 2,
        "name_match": "Šempeter pri Gorici",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Šempeter pri Gorici",
        "address": "Vrtojbenska cesta 19, Šempeter",
        "distance": 4.1,
        "isHighway": False,
        "hours": "06:00 - 22:00",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Šempeter+pri+Gorici",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.749, "lpg": 0.889}
    },
    {
        "id": 3,
        "name_match": "Tolminskih puntarjev",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Nova Gorica - Tolminskih puntarjev",
        "address": "Ulica Tolminskih puntarjev 14, Nova Gorica",
        "distance": 0.6,
        "isHighway": False,
        "hours": "06:00 - 22:00",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Ulica+Tolminskih+puntarjev+Nova+Gorica",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.749, "lpg": 0.899}
    },
    {
        "id": 4,
        "name_match": "Vojkova",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Nova Gorica - Vojkova",
        "address": "Vojkova cesta 32, Nova Gorica",
        "distance": 1.2,
        "isHighway": False,
        "hours": "06:00 - 22:00",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Vojkova+cesta+Nova+Gorica",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.749, "lpg": None}
    },
    {
        "id": 5,
        "name_match": "Prvomajska",
        "brand_match": "MOL",
        "brand": "MOL",
        "name": "MOL Nova Gorica - Prvomajska",
        "address": "Prvomajska ulica 48, Nova Gorica",
        "distance": 1.5,
        "isHighway": False,
        "hours": "06:00 - 22:00",
        "mapsUrl": "https://maps.google.com/?q=MOL+Prvomajska+Nova+Gorica",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.739, "lpg": 0.879}
    },
    {
        "id": 6,
        "name_match": "Rožna Dolina",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Rožna Dolina (Obmejni prehod)",
        "address": "Vipavska cesta 1, Rožna Dolina",
        "distance": 2.1,
        "isHighway": False,
        "hours": "00:00 - 24:00 (Non-stop)",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Rožna+Dolina",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.749, "lpg": 0.899}
    },
    {
        "id": 7,
        "name_match": "Solkan",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Solkan",
        "address": "Prvomajska ulica 112, Solkan",
        "distance": 2.4,
        "isHighway": False,
        "hours": "06:00 - 21:00",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Solkan",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": None, "lpg": None}
    },
    {
        "id": 8,
        "name_match": "Mednarodni prehod",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Vrtojba (Izven avtoceste / Meja)",
        "address": "Mednarodni prehod 2b, Vrtojba",
        "distance": 5.4,
        "isHighway": False,
        "hours": "00:00 - 24:00 (Non-stop)",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Mednarodni+prehod+Vrtojba",
        "fallback_prices": {"dizel": 1.499, "95": 1.479, "100": 1.749, "lpg": 0.889}
    },
    {
        "id": 9,
        "name_match": "Vrtojba",
        "brand_match": "MOL",
        "brand": "MOL",
        "name": "MOL Vrtojba AC (Avtocesta H4)",
        "address": "Avtocesta H4, Vrtojba (smer Italija)",
        "distance": 6.1,
        "isHighway": True,
        "hours": "00:00 - 24:00 (Non-stop)",
        "mapsUrl": "https://maps.google.com/?q=MOL+Vrtojba+avtocesta",
        "fallback_prices": {"dizel": 1.769, "95": 1.749, "100": 1.949, "lpg": 0.999}
    },
    {
        "id": 10,
        "name_match": "Vrtojba",
        "brand_match": "Petrol",
        "brand": "Petrol",
        "name": "Petrol Vrtojba AC (Avtocesta H4)",
        "address": "Avtocesta H4, Vrtojba (smer Razdrto)",
        "distance": 6.3,
        "isHighway": True,
        "hours": "00:00 - 24:00 (Non-stop)",
        "mapsUrl": "https://maps.google.com/?q=Petrol+Vrtojba+avtocesta",
        "fallback_prices": {"dizel": 1.779, "95": 1.759, "100": 1.959, "lpg": 0.999}
    }
]

def fetch_live_prices():
    try:
        response = requests.get(API_URL, headers=HEADERS, timeout=12)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Napaka pri klicu API: {e}")
    return None

def main():
    print("Pridobivam uradne cene z Goriva.si...")
    api_data = fetch_live_prices()
    results = []

    for station in LOCAL_STATIONS:
        st_data = {
            "id": station["id"],
            "brand": station["brand"],
            "name": station["name"],
            "address": station["address"],
            "distance": station["distance"],
            "isHighway": station["isHighway"],
            "hours": station["hours"],
            "mapsUrl": station["mapsUrl"],
            "prices": dict(station["fallback_prices"])
        }

        # Če API vrne podatke, posodobimo cene
        if api_data and "results" in api_data:
            for item in api_data["results"]:
                item_name = item.get("name", "")
                item_brand = item.get("brand", "")

                if station["name_match"].lower() in item_name.lower() and station["brand_match"].lower() in item_brand.lower():
                    # Preberi cene goriv
                    for fuel in item.get("prices", []):
                        fuel_type = fuel.get("type", "").lower()
                        price_val = fuel.get("price")
                        if price_val:
                            if "dizel" in fuel_type or "diesel" in fuel_type:
                                st_data["prices"]["dizel"] = float(price_val)
                            elif "95" in fuel_type:
                                st_data["prices"]["95"] = float(price_val)
                            elif "100" in fuel_type:
                                st_data["prices"]["100"] = float(price_val)
                            elif "lpg" in fuel_type or "plin" in fuel_type:
                                st_data["prices"]["lpg"] = float(price_val)

        results.append(st_data)

    with open("cene.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(f"Uspešno posodobljeno {len(results)} črpalk v cene.json!")

if __name__ == "__main__":
    main()
