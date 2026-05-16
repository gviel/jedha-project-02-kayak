# Spécifications script : load_to_db.py

## Prérequis — initialisation de la base de données
Avant le premier lancement de `load_to_db.py`, créer le schéma PostgreSQL :

```bash
psql $DATABASE_URL -f sql/schema.sql
```

Le script `sql/schema.sql` crée les 5 tables (`cities`, `weather_scores`, `weather_scores_daily`, `hotels`, `history`) avec leurs contraintes PRIMARY KEY. À rejouer intégralement sur une nouvelle base (idempotent via `CREATE TABLE IF NOT EXISTS`).

## Configuration
Variables d'environnement requises (dans `.env`) :
  - `DATABASE_URL` — URL de connexion PostgreSQL (AWS RDS ou Neon DB)
  - `S3_BUCKET` — nom du bucket S3 utilisé
  - `TOP_N_HOTELS` — nombre max d'hôtels chargés par ville depuis S3 (défaut : `20` ; appliqué via `LIMIT` SQL)

## Entrées
- Bucket S3 : `S3_BUCKET`

## Sorties
- Base de données : PostgreSQL via SQLAlchemy avec la variable d'env `DATABASE_URL`

# Phase chargement PostgreSQL
script `src/load_to_db.py` - charge les fichier CSV du bucket S3 dans PostgreSQL (AWS RDS ou Neon DB) avec SQLAlchemy / psycopg2

1. lire les fichiers CSV depuis le bucket S3 via boto3/s3fs  :
   - `cities.csv` → table `cities` (colonnes : `city_id, city_name, lat, lon`)
   - `weather-scores-daily-<YYYYMMDD>.csv` → table `weather_scores_daily` (colonnes : `city_id, city_name, date_forecast, score_day`)
   - `weather-scores-<YYYYMMDD>.csv` → table `weather_scores` (colonnes : `city_id, city_name, mean, median, min, max, std, score_final`)
   - `<YYYYMMDD>/hotels-<city_id>-<YYYYMMDD>.csv` → table `hotels` (colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url, load_date`)

2. connexion PostgreSQL via SQLAlchemy avec la variable d'env `DATABASE_URL` (format : `postgresql://user:password@host:port/dbname`)

3. stratégie d'insertion :
  - `if_exists='replace'` pour `cities` (données de référence stables) et `weather_scores` (agrégat 4j recalculé quotidiennement)
  - stratégie upsert pour `weather_scores_daily` : clé = `(city_id, date_forecast)` — `ON CONFLICT (city_id, date_forecast) DO UPDATE SET score_day` — la table historise tous les scores jour par ville ; une contrainte PRIMARY KEY sur `(city_id, date_forecast)` est requise en base
  - stratégie upsert pour `hotels` : une seule ligne par hôtel (clé = `city_id` + `hotel_name`), load_date la plus récente conservée — réécriture complète de la table à chaque chargement

4. table `history` (upsert après chaque chargement) :
  - Permet de tracer à quelle date sont faits les chargements en base de données
  - colonnes : `table_name` (PK), `load_date`
  - `load_date` = nom du répertoire S3 `YYYYMMDD` pour les tables `weather_scores`, `weather_scores_daily` et `hotels`
  - `load_date`= date système pour la table `cities`
  - créée automatiquement si elle n'existe pas (`CREATE TABLE IF NOT EXISTS`)