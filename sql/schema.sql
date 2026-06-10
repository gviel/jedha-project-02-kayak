-- KAYAK project — schéma PostgreSQL
-- Génération : 2026-05-16
-- Usage : psql $DATABASE_URL -f sql/schema.sql
--         ou exécuter bloc par bloc depuis un client SQL (DBeaver, psql, Neon console…)

-- ============================================================
-- TABLE : cities
-- Référentiel des villes (coordonnées géographiques WSG84).
-- Rechargée entièrement à chaque pipeline (if_exists='replace').
-- ============================================================
CREATE TABLE IF NOT EXISTS cities (
    city_id   VARCHAR PRIMARY KEY,
    city_name VARCHAR NOT NULL,
    lat       FLOAT,
    lon       FLOAT
);

-- ============================================================
-- TABLE : weather_scores
-- Agrégat 4 jours par ville (mean, median, min, max, std, score_final).
-- Rechargée entièrement à chaque pipeline (if_exists='replace').
-- ============================================================
CREATE TABLE IF NOT EXISTS weather_scores (
    city_id     VARCHAR PRIMARY KEY,
    city_name   VARCHAR NOT NULL,
    mean        FLOAT,
    median      FLOAT,
    min         FLOAT,
    max         FLOAT,
    std         FLOAT,
    score_final FLOAT
);

-- ============================================================
-- TABLE : weather_scores_daily
-- Scores météo journaliers par ville (historisation complète).
-- Stratégie upsert ON CONFLICT (city_id, date).
-- ============================================================
CREATE TABLE IF NOT EXISTS weather_scores_daily (
    city_id       VARCHAR  NOT NULL,
    city_name     VARCHAR  NOT NULL,
    date_forecast DATE     NOT NULL,
    score_day     FLOAT,
    PRIMARY KEY (city_id, date_forecast)
);

-- ============================================================
-- TABLE : hotels
-- Hôtels scrapés sur Booking.com (top-N villes).
-- Stratégie upsert : clé (city_id, hotel_name), load_date la plus récente.
-- ============================================================
CREATE TABLE IF NOT EXISTS hotels (
    city_id     VARCHAR  NOT NULL,
    city_name   VARCHAR,
    hotel_name  VARCHAR  NOT NULL,
    lat         FLOAT,
    lon         FLOAT,
    description TEXT,
    score       FLOAT,
    url         VARCHAR,
    address     VARCHAR,
    zip_code    VARCHAR,
    city_label  VARCHAR,
    load_date   VARCHAR,
    PRIMARY KEY (city_id, hotel_name)
);

-- ============================================================
-- TABLE : history
-- Traçabilité des chargements (une ligne par table).
-- ============================================================

CREATE TABLE IF NOT EXISTS history (
    table_name VARCHAR PRIMARY KEY,
    load_date  VARCHAR
);

