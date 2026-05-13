#!/usr/bin/env python
# coding: utf-8

# KAYAK project phase 3 : weather scoring
# Reads glom-transformed JSON files from data/json/weather/ (produced by
# scraper_weather.py), scores each city per day using daytime slots (08:00-20:00),
# and outputs two CSVs to data/csv/:
#   weather_scores_daily_<YYYY-MM-DD>.csv   — score per city × day
#   weather_scores_<YYYY-MM-DD>.csv         — aggregate per city (mean/median/min/max)

import glob
import json
import os
from datetime import datetime, timedelta

import pandas as pd
from dotenv import load_dotenv

load_dotenv()

DATA_DIR = "data"
DATA_DIR_CSV = f"{DATA_DIR}/csv"
DATA_DIR_JSON_WEATHER = f"{DATA_DIR}/json/weather"
os.makedirs(DATA_DIR_CSV, exist_ok=True)

_today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
TODAY_ISO = _today.strftime("%Y%m%d")
DATA_DIR_CSV_TODAY = os.path.join(DATA_DIR_CSV, TODAY_ISO)
os.makedirs(DATA_DIR_CSV_TODAY, exist_ok=True)

FORECAST_DAYS = [_today + timedelta(days=i) for i in range(1, 5)]


# ── Scoring functions (return 0–10) ──────────────────────────────────────────

def score_temperature(feels_like: float) -> float:
    if feels_like < 0:      return 0.0
    if feels_like <= 10:    return 2.0
    if feels_like <= 17:    return 5.0
    if feels_like <= 28:    return 10.0
    if feels_like <= 33:    return 5.0
    return 0.0


def score_precipitation(rain_proba: float) -> float:
    # rain_proba is 0.0–1.0 (OWM pop); no mm data on free tier
    return (1.0 - rain_proba) * 10.0


def score_wind(wind_speed_ms: float) -> float:
    # OWM wind_speed is in m/s (units=metric) → convert to km/h for thresholds
    kmh = wind_speed_ms * 3.6
    if kmh <= 15:  return 10.0
    if kmh <= 28:  return 8.0
    if kmh <= 38:  return 5.0
    if kmh <= 61:  return 2.0
    return 0.0


def score_clouds(clouds_pct: float) -> float:
    # OWM clouds is 0–100%; thresholds use dixièmes (0–10)
    oktas = clouds_pct / 10.0
    if oktas <= 4:  return 10.0
    if oktas <= 9:  return 6.0
    return 2.0


def score_humidity(humidity: float) -> float:
    if 40 <= humidity <= 70:   return 10.0
    if 70 < humidity <= 80:    return 7.0
    if 20 <= humidity < 40:    return 7.0
    return 3.0  # <20 or >80


def score_pressure(pressure: float) -> float:
    if pressure < 980:    return 1.0
    if pressure <= 995:   return 3.0
    if pressure <= 1005:  return 6.0
    if pressure <= 1015:  return 10.0
    if pressure <= 1025:  return 8.0
    if pressure <= 1035:  return 6.0
    return 3.0


def composite_score(slot: dict) -> float:
    s = (
        score_temperature(slot["feels_like"])   * 0.30
        + score_precipitation(slot["rain_proba"]) * 0.30
        + score_wind(slot["wind_speed"])          * 0.15
        + score_clouds(slot["clouds"])            * 0.10
        + score_humidity(slot["humidity"])        * 0.10
        + score_pressure(slot["pressure"])        * 0.05
    )
    return round(s * 10, 2)  # weighted sum 0–10 → scale to 0–100


# ── Main ─────────────────────────────────────────────────────────────────────

records_daily = []

for day in FORECAST_DAYS:
    iso_date  = day.strftime("%Y-%m-%d")
    file_date = day.strftime("%Y%m%d")
    pattern = os.path.join(DATA_DIR_JSON_WEATHER, file_date, f"weather-*-{file_date}.json")
    for fpath in sorted(glob.glob(pattern)):
        basename = os.path.basename(fpath)
        city_id   = basename[len("weather-"):-len(f"-{file_date}.json")]
        city_name = city_id.replace("_", " ")

        with open(fpath, "r", encoding="utf-8") as f:
            slots = json.load(f)

        day_slots = [s for s in slots if "08:00:00" <= s["time"] <= "20:00:00"]
        if not day_slots:
            continue

        scores = [composite_score(s) for s in day_slots]
        records_daily.append({
            "city_id":   city_id,
            "city_name": city_name,
            "date":      iso_date,
            "score_day": round(sum(scores) / len(scores), 2),
        })

if not records_daily:
    print("No data to score — run scraper_weather.py first.")
    raise SystemExit(1)

df_daily = pd.DataFrame(records_daily)

out_daily = os.path.join(DATA_DIR_CSV_TODAY, f"weather-scores-daily-{TODAY_ISO}.csv")
df_daily.to_csv(out_daily, index=False, encoding="utf-8")
print(f"Saved daily scores   → {out_daily}")

records_summary = []
for (city_id, city_name), grp in df_daily.groupby(["city_id", "city_name"]):
    s = grp["score_day"]
    mean   = round(s.mean(), 2)
    std    = round(s.std(), 2)
    s_min  = round(s.min(), 2)
    s_max  = round(s.max(), 2)
    # pénalité cumulative pour variabilité excessive : -10 si min < mean-3σ, -10 si max > mean+3σ
    penalty = (-10 if s_min < mean - 3 * std else 0) + (-10 if s_max > mean + 3 * std else 0)
    records_summary.append({
        "city_id":     city_id,
        "city_name":   city_name,
        "mean":        mean,
        "median":      round(s.median(), 2),
        "min":         s_min,
        "max":         s_max,
        "std":         std,
        "score_final": round(mean + penalty, 2),
    })

out_summary = os.path.join(DATA_DIR_CSV_TODAY, f"weather-scores-{TODAY_ISO}.csv")
(pd.DataFrame(records_summary)
   .sort_values("score_final", ascending=False)
   .to_csv(out_summary, index=False, encoding="utf-8"))
print(f"Saved summary scores → {out_summary}")
