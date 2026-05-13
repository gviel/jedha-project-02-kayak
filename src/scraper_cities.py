#!/usr/bin/env python
# coding: utf-8

# # Projet KAYAK
#
# - on a une liste de villes en france
#     - il faut récupérer la position GPS de la ville https://nominatim.org/ => dans un dataframe et sauver dans S3 en CSV
#     - puis on récupère la météo 7j pour cette localisation https://openweathermap.org/api => sauver en CSV aussi
#     - créer un critère pour la météo (selon la saison?) et les classer selon ce critère (daily.pop daily.rain temperature?)
#     - ensuite trouver les 20 meilleurs hotels pour les top 10 destinations ayant la meilleure météo => scraping booking.com
#     - stocker dans S3
#     - afficher les meilleures destinations sur une carte avec plotly
#     - petit moteur de recherche?
#
import glob
import json
import os
import random
import time

import pandas as pd
import requests
from dotenv import load_dotenv

load_dotenv()

CITIES_CONFIG = "config/cities.txt"

def _load_cities(path: str = CITIES_CONFIG) -> list[str]:
    with open(path, encoding="utf-8") as f:
        return [line.strip() for line in f if line.strip()]

USER_AGENT = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
DATA_DIR = "data"
DATA_DIR_CSV = f"{DATA_DIR}/csv"
os.makedirs(DATA_DIR_CSV, exist_ok=True)
DATA_DIR_HTML = f"{DATA_DIR}/html"
os.makedirs(DATA_DIR_HTML, exist_ok=True)
DATA_DIR_JSON = f"{DATA_DIR}/json"
os.makedirs(DATA_DIR_JSON, exist_ok=True)
DATA_DIR_JSON_CITIES = f"{DATA_DIR_JSON}/cities"
os.makedirs(DATA_DIR_JSON_CITIES, exist_ok=True)

# 1) Phase 1 : Extract cities WGS84 long/lat coordinates
BASE_URL_NOMINATIM = "https://nominatim.openstreetmap.org"

HEADERS = {'User-Agent': USER_AGENT}
DEFAULT_PARAMS = {"format": "json"}


def _sanitize(name: str) -> str:
    return name.replace(" ", "_").replace("'", "_")


VALID_TYPES = {"city", "town", "village", "hamlet", "municipality", "islet", "historic", "tourism", "county", "gorge"}


def _pick_best(data: list) -> dict | None:
    for item in data:
        if item.get("addresstype") in VALID_TYPES:
            return item
    return None


def _cache_lookup(city_name: str):
    """Return path of existing cache file for city_name, or None."""
    p = os.path.join(DATA_DIR_JSON_CITIES, f"city-{_sanitize(city_name)}.json")
    return p if os.path.exists(p) else None


def load_from_cache(city_name: str):
    """Load city data from json file if exists in cache dir."""
    p = _cache_lookup(city_name)
    if p:
        with open(p, "r", encoding="utf-8") as f:
            try:
                return json.load(f)
            except Exception:
                return None
    return None


def save_to_cache(city_name: str, data):
    filename = f"city-{_sanitize(city_name)}.json"
    p = os.path.join(DATA_DIR_JSON_CITIES, filename)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def query_nominatim(city_name: str, delay: int = 2):
    """Get city infos with Nominatim - delay 2 sec by default between each query."""
    params = DEFAULT_PARAMS.copy()
    params["q"] = city_name
    params["countrycodes"] = "fr"
    resp = requests.get(url=f"{BASE_URL_NOMINATIM}/search", headers=HEADERS, params=params, timeout=10)
    status = resp.status_code
    if status == 200:
        try:
            data = resp.json()
        except ValueError:
            data = None
        time.sleep(delay)
        return data or None

    if status == 429 or status >= 500:
        wait = delay * 2 + random.uniform(0, 0.5)
        time.sleep(wait)
        return None
    return None


if __name__ == "__main__":
    cities = _load_cities()
    results = []
    for name in cities:
        data = load_from_cache(name)
        if data is None:
            data = query_nominatim(name)
            if data:
                save_to_cache(name, data)

        if data and isinstance(data, list) and len(data) > 0:
            item = _pick_best(data)
            if item:
                results.append({
                    "city_id":   _sanitize(name),
                    "city_name": name,
                    "lat":       item.get("lat"),
                    "lon":       item.get("lon")
                })
            else:
                results.append({"city_id": _sanitize(name), "city_name": name, "lat": None, "lon": None})
        else:
            results.append({"city_id": _sanitize(name), "city_name": name, "lat": None, "lon": None})

    df = pd.DataFrame(results)
    df.to_csv(os.path.join(DATA_DIR_CSV, "cities.csv"), index=False, encoding="utf-8")
    print("Saved", len(df), "rows to", os.path.join(DATA_DIR_CSV, "cities.csv"))
