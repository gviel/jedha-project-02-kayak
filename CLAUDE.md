# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

KAYAK travel recommendation engine that ranks 35 French tourist cities by weather score and surfaces matching hotel data.

The full pipeline: geocode cities → fetch weather forecasts → score destinations → scrape hotels → upload to S3 → load into RDS PostgreSQL → display maps in Streamlit UI

## Regles générales
- montrer les diffs lorsqu'il y a des modifications

## Convention de commits (Conventional Commits)
| Préfixe | Usage |
|---|---|
| `feat:` | nouvelle fonctionnalité |
| `fix:` | correction de bug |
| `docs:` | documentation uniquement |
| `refactor:` | restructuration sans changement de comportement |
| `test:` | ajout/modification de tests |
| `chore:` | maintenance, config, outillage (ne modifie pas la logique applicative) |

## Environment Setup
- Python 3.13
- Utilisation de conda : vérifie toujours qu'on est bien dans l'environnement conda `kayak`
- Opérations pour l'installation de l'environnement
```bash
conda env create --file env_kayak.yml
conda activate kayak
python -m ipykernel install --user --name kayak --display-name "KAYAK project"
# playwright est installé via pip par env_kayak.yml (paquet PyPI-only, non disponible sur conda-forge en Python)
conda run -n kayak playwright install chromium   # installe le binaire Chromium (~110 MB), requis pour le scraping local
# Alternative Docker : docker build -t kayak . && docker run --env-file .env kayak
```
- API keys go in `.env` (already gitignored):
  - `API_KEY_OWM` — OpenWeatherMap
  - AWS credentials for S3 and RDS access
  - création d'un fichier `.env_template` qui est la copie de `.env`avec les mêmes variables mais avec des valeurs fictives pour raison de sécurité. Ce fichier doit être maintenu dès que le `.env` est modifié

## Déploiement
1. déploiement dans un conteneur Docker linux des scripts
2. base Dockerfile sur python 3.12 => https://playwright.dev/python/docs/docker
```
FROM python:3.12-bookworm

RUN pip install playwright==@1.55.0 && \
    playwright install --with-deps
```
ou bien avec une image docker mcr.microsoft.com/playwright/python:v1.59.0-noble (cf. https://playwright.dev/python/docs/docker)
3. configuration par fichier .env pour les clés (si nécessaire)
4. installation du navigateur chromium pour playwright

## Project structure
- Dockerfile : image Docker unifiée pour l'ensemble du pipeline (inclut Playwright + cron)
- entrypoint.sh : expose les variables d'env Docker à cron au démarrage du container
- pipeline.sh : orchestre les scripts dans l'ordre (exécuté par cron à 06:00 quotidiennement)
- requirements.txt : dépendances pip communes (pipeline + Playwright)
- Main specifications are in file 01-Plan_your_trip_with_Kayak.ipynb
- file Kayak.ipynb should be ignored
- config/ : fichiers de configuration — `cities.txt` (liste des villes, une par ligne)
- src/ : source code
- docs/ : miscellaneous documentation
- data/ : contains the data (see specs @data/CLAUDE.md ) — sous-dossiers : json/cities, json/weather, csv, html
- .env : contains AWS credentials for S3, OpenWeatherMap API key and PostgreSQL DB (AWS RDS or Neon)

## Running the Pipeline

Le pipeline complet est orchestré par `pipeline.sh`, exécuté automatiquement par cron à 06:00 dans le container Docker. Chaque étape lit la sortie de la précédente.

```bash
# lancement Docker (recommandé)
docker build -t kayak .
docker run -d --env-file .env -v $(pwd)/data:/app/data kayak
docker exec <container> tail -f /var/log/kayak.log

# lancement local
bash pipeline.sh
```

Steps run in order; each step's output feeds the next:

1. **Geocode cities** — `src/scraper_cities.py` calls Nominatim API (no auth, 1 req/s limit) and caches results per-city under `data/json/cities/`. Running it again skips already-cached cities. See specs in @src/scraper_cities.md

2. **Weather forecasts** — script `src/scraper_weather.py` calls OpenWeatherMap 4-day forecast endpoint; glom-transformed JSON split into 4 files per city with pattern `data/json/weather/<yyyyMMdd>/weather-<city_name>-<yyyyMMdd>.json` (J+1 to J+4).
See specs in @src/scraper_weather.md

3. **Score & transform** — script `src/score_weather.py` reads per-slot JSON files, aggregates daytime slots (08:00–20:00) per city/day and applies the weighted scoring model. Produces two CSVs: `weather-scores-daily-<YYYYMMDD>.csv` (score par ville × jour) and `weather-scores-<YYYYMMDD>.csv` (agrégat 4j par ville).
See specs in @src/score_weather.md

4. **Scrape hotels** — script `src/scraper_hotels.py` drives a headless Chromium browser (Playwright) against Booking.com for the top-N cities from step 3. Raw HTML lands in `data/html/` for debug (optional). Run locally or via `docker run --env-file .env kayak`.
   ```bash
   conda run -n kayak python src/scraper_hotels.py [N] [from_date] [to_date]  # N: nb villes (défaut 5), dates YYYY-MM-DD (défaut J+1→J+4)
   ```
See specs in @src/scraper_hotels.md

5. **Upload to S3** — boto3/s3fs writes processed CSVs to the data lake bucket. See specs @src/load_csv_to_s3.md

6. **Load CSV data in bucket S3 to PostgreSQL DB (AWS RDS or Neon)** — See specs @src/load_to_db.md

7. **UI Streamlit** - script `src/kayak_ui.py` pour visualiser les données de la base de données sous forme de cartes - voir specs @src/kayak_ui.md

## Architecture

```
Nominatim API  ──►  src/scraper_cities.py       ──►  data/json/cities/  (per-city cache)
                                                    │
OpenWeatherMap ──►  src/scraper_weather.py      ──►  data/json/weather/<yyyyMMdd>/weather-<city>-<yyyyMMdd>.json  (×4 par ville)
                                                    │
Weather scoring ──► src/score_weather.py        ──►  data/csv/  (scored cities)
                                                    │
Booking.com    ──►  src/scraper_hotels.py       ──►  data/html/ → data/csv/hotels
                                     │
Datalake       ──►  src/load_csv_to_s3.py       ──►  AWS S3  (data lake)
                                                    │
Data warehouse ──►  src/load_to_db.py           ──►  PostgreSQL (data warehouse)
                                                    │
User Interface  ──► src/kayak_ui.py             ──► Plotly and/or Streamlit UI  ──►  Interactive maps (Top-5 cities, Top-20 hotels)
```

## Weather Scoring Model
- see specs @src/score_weather.md and `docs/systeme scoring avec openweathermap API.md`.

## Interface utilisateur : Streamlit UI
```bash
streamlit run src/kayak_ui.py --server.headless true --server.port 8501
```

## Known Issues
- Booking.com scraping requires realistic User-Agent headers and may require a proxy to avoid blocks.
