#!/bin/bash
set -e
cd /app

echo "[$(date '+%Y-%m-%d %H:%M:%S')] ── KAYAK pipeline start ──"

# Purge des fichiers HTML de debug et snapshots de plus de 4 jours
# (le scraper hotels produit ~20 fichiers/ville/jour — sans purge le volume croît indéfiniment)
echo "[$(date '+%Y-%m-%d %H:%M:%S')] Step 0: purge HTML/snapshots > 4 jours"
find data/html -maxdepth 1 -name "*.html" -mtime +4 -delete
find data/html/snap -name "*.png" -mtime +4 -delete 2>/dev/null || true
echo "Purge OK"

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
