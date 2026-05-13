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
   - `weather-scores-daily-<YYYYMMDD>.csv` → table `weather_scores_daily` (colonnes : `city_id, city_name, date, score_day`)
   - `weather-scores-<YYYYMMDD>.csv` → table `weather_scores` (colonnes : `city_id, city_name, mean, median, min, max`)
   - `<YYYYMMDD>/hotels-<city_id>-<YYYYMMDD>.csv` → table `hotels` (colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url, load_date`)

2. connexion PostgreSQL via SQLAlchemy avec la variable d'env `DATABASE_URL` (format : `postgresql://user:password@host:port/dbname`)

3. stratégie d'insertion :
  - `if_exists='replace'` pour les tables de scores (données quotidiennes recalculées)
  - `if_exists='append'` pour les hotels, avec les règles suivantes :
    - ajouter une colonne `load_date` (valeur `YYYYMMDD` extraite du nom de fichier S3) au DataFrame avant insert
    - avant chaque insert, supprimer les lignes existantes dont `load_date = TODAY` (opération idempotente : relancer le pipeline le même jour ne crée pas de doublons)
    - si la table n'existe pas encore (premier run), la suppression est ignorée silencieusement