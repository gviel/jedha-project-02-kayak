# Spécifications script : load_csv_to_s3.py

## Role
Phase load : charge les CSV vers le bucket S3 avec boto3/s3fs

## Entrées
- Répertoire : `data/csv`

## Sorties
- Vers bucket S3 :
  - `s3://{S3_BUCKET}/{S3_PREFIX}cities.csv` — fichier de référence (sans date-dir)
  - `s3://{S3_BUCKET}/{S3_PREFIX}<YYYYMMDD>/` — fichiers datés (scores météo et hotels)

## Configuration
Variables d'environnement requises (dans `.env`) :
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`
   - `AWS_REGION`
   - `S3_BUCKET`
   - `S3_PREFIX` (optionnel, défaut : `csv/`)

## Déroulement
1. lire les fichiers CSV produits par le pipeline dans `data/csv/` :
   - `cities.csv` — fichier de référence des villes (produit par `src/scraper_cities.py`), colonnes : `city_id, city_name, lat, lon`
   - `weather-scores-daily-<YYYYMMDD>.csv` — un fichier par jour d'extraction (produit par `src/score_weather.py`), colonnes : `city_id, city_name, date, score_day`
   - `weather-scores-<YYYYMMDD>.csv` — agrégat 4 jours par ville (produit par `src/score_weather.py`), colonnes : `city_id, city_name, mean, median, min, max`, trié par `mean` décroissant
   - `<YYYYMMDD>/hotels-<city_id>-<YYYYMMDD>.csv` — un fichier par ville scrapée (produit par `src/scraper_hotels.py`), colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url`

2. uploader chaque fichier CSV vers le bucket S3 défini par la variable d'env `S3_BUCKET` avec boto3 :
  - `cities.csv` → uploadé directement sous `{S3_PREFIX}cities.csv` (pas de sous-répertoire de date, fichier de référence)
  - fichiers datés → uploadés sous `{S3_PREFIX}<YYYYMMDD>/` (date extraite du nom de fichier via regex `\d{8}`)
  - préfixe configurable via `S3_PREFIX`