#!/bin/bash
set -e
cd /app

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── KAYAK pipeline start ──"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 1: geocode cities"
python src/scraper_cities.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 2: fetch weather forecasts"
python src/scraper_weather.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 3: score weather"
python src/score_weather.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 4: scrape hotels"
python src/scraper_hotels.py ${TOP_N_CITIES:-5}

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 5: upload CSVs to S3"
python src/load_csv_to_s3.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 6: load S3 data to PostgreSQL"
python src/load_to_db.py

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── KAYAK pipeline done ──"
