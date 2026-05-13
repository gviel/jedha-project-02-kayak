# Spécifications script : load_to_db.py

## Configuration
Variables d'environnement requises (dans `.env`) :
  - `DATABASE_URL` — URL de connexion PostgreSQL (AWS RDS ou Neon DB)
  - `S3_BUCKET` - nom du bucket S3 utilisé

## Entrées
- Bucket S3 : `S3_BUCKET`

## Sorties
- Base de données : PostgreSQL via SQLAlchemy avec la variable d'env `DATABASE_URL`

# Phase chargement PostgreSQL
script `src/load_to_db.py` - charge les fichier CSV du bucket S3 dans PostgreSQL (AWS RDS ou Neon DB) avec SQLAlchemy / psycopg2

1. lire les fichiers CSV depuis le bucket S3 via boto3/s3fs  :
   - `cities.csv` → table `cities` (colonnes : `city_id, city_name, lat, lon`)
   - `weather-scores-daily-<YYYYMMDD>.csv` → table `weather_scores_daily` (colonnes : `city_id, city_name, date, score_day`)
   - `weather-scores-<YYYYMMDD>.csv` → table `weather_scores` (colonnes : `city_id, city_name, mean, median, min, max, std, score_final`)
   - `<YYYYMMDD>/hotels-<city_id>-<YYYYMMDD>.csv` → table `hotels` (colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url, load_date`)

2. connexion PostgreSQL via SQLAlchemy avec la variable d'env `DATABASE_URL` (format : `postgresql://user:password@host:port/dbname`)

3. stratégie d'insertion :
  - `if_exists='replace'` pour `cities` (données de référence stables) et les tables de scores (données quotidiennes recalculées)
  - stratégie upsert pour `hotels` : une seule ligne par hôtel (clé = `city_id` + `hotel_name`), load_date la plus récente conservée — réécriture complète de la table à chaque chargement