#!/usr/bin/env python
# coding: utf-8

# KAYAK project phase 2 : fetch and split weather forecasts from OpenWeatherMap API
# Reads data/csv/cities.csv, fetches 5-day/3h forecast per city, applies glom
# transform, and saves 4 files per city:
#   data/json/weather/weather-<city_name>-<yyyyMMdd>.json  (J+1 to J+4)

import json
import os
import time
from datetime import datetime, timedelta

import pandas as pd
import requests
from dotenv import load_dotenv
from glom import glom

load_dotenv()

API_KEY_OWM = os.environ["API_KEY_OWM"]

DATA_DIR = "data"
DATA_DIR_CSV = f"{DATA_DIR}/csv"
DATA_DIR_JSON_WEATHER = f"{DATA_DIR}/json/weather"
os.makedirs(DATA_DIR_JSON_WEATHER, exist_ok=True)

BASE_URL_OWM = "https://api.openweathermap.org/data/2.5"

# J+1 to J+4
_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
FORECAST_DAYS = [
    ((_today + timedelta(days=i)).strftime("%Y-%m-%d"),
     (_today + timedelta(days=i)).strftime("%Y%m%d"))
    for i in range(1, 5)
]
# list of (iso_date "YYYY-MM-DD", file_date "yyyyMMdd")


def tstamp_to_date(tstamp):
    return datetime.fromtimestamp(tstamp).strftime("%Y-%m-%d")


def tstamp_to_time(tstamp):
    return datetime.fromtimestamp(tstamp).strftime("%H:%M:%S")


GLOM_SPEC = {
    "dt":           "dt",
    "dt_str":       "dt_txt",
    "date":         ("dt", tstamp_to_date),
    "time":         ("dt", tstamp_to_time),
    "temp":         "main.temp",
    "feels_like":   "main.feels_like",
    "temp_min":     "main.temp_min",
    "temp_max":     "main.temp_max",
    "pressure":     "main.pressure",
    "humidity":     "main.humidity",
    "weather_id":   "weather.0.id",
    "weather_desc": "weather.0.main",
    "clouds":       "clouds.all",
    "wind_speed":   "wind.speed",
    "rain_proba":   "pop",
}


def _sanitize(name: str) -> str:
    return name.replace(" ", "_").replace("'", "_")


def weather_day_path(city_name: str, file_date: str) -> str:
    day_dir = os.path.join(DATA_DIR_JSON_WEATHER, file_date)
    os.makedirs(day_dir, exist_ok=True)
    return os.path.join(day_dir, f"weather-{_sanitize(city_name)}-{file_date}.json")


def fetch_forecast(lat: float, lon: float) -> dict | None:
    params = {
        "lat": lat, "lon": lon,
        "cnt": 100,
        "units": "metric",
        "appid": API_KEY_OWM,
    }
    resp = requests.get(url=f"{BASE_URL_OWM}/forecast", params=params, timeout=10)
    if resp.status_code == 200:
        return resp.json()
    print(f"  OWM error {resp.status_code}: {resp.text[:200]}")
    return None


df_cities = pd.read_csv(os.path.join(DATA_DIR_CSV, "cities.csv"))

for _, row in df_cities.iterrows():
    name = row["city_name"]
    lat, lon = row.get("lat"), row.get("lon")

    if pd.isna(lat) or pd.isna(lon):
        print(f"[SKIP] {name}: no coordinates")
        continue

    raw = fetch_forecast(float(lat), float(lon))
    if raw is None:
        print(f"[FAIL] {name}")
        time.sleep(1.0)
        continue

    all_slots = glom(raw.get("list", []), [GLOM_SPEC])

    saved = 0
    for iso_date, file_date in FORECAST_DAYS:
        day_slots = [s for s in all_slots if s["date"] == iso_date]
        if day_slots:
            with open(weather_day_path(name, file_date), "w", encoding="utf-8") as f:
                json.dump(day_slots, f, ensure_ascii=False, indent=2)
            saved += 1

    print(f"[OK] {name}: {saved} day(s) saved")
    time.sleep(1.0)  # free tier: 60 req/min

print("Done.")
