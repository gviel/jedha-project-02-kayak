# JEDHA : Projet KAYAK (bloc 1) — Recommandation de destinations touristiques en France

Projet de data engineering qui classe 35 villes touristiques françaises par score météo sur 4 jours et affiche les meilleurs hôtels (d'un site de réservation en ligne) pour chaque destination.

**NB: pas de Notebook dans ce projet étant donné que c'est un pipeline data automatisé. L'UI sous forme de dashboard fera office de Notebook pour visualiser les résultats.**


## Objectifs

- **Collecter** les coordonnées GPS des villes (API Nominatim) et les prévisions météo (API OpenWeatherMap)
- **Scorer** chaque ville sur 4 jours selon un modèle pondéré (température, précipitations, vent, nuages, humidité, pression)
- **Scraper** les hôtels des meilleures destinations sur Booking.com (Playwright)
- **Stocker** les résultats dans un data lake S3 et un data warehouse PostgreSQL (AWS RDS ou Neon)
- **Visualiser** les résultats dans un dashboard Streamlit interactif (cartes + classements)

## Architecture du pipeline

```
Nominatim API  ──►  scraper_cities.py   ──►  data/json/cities/  (cache)
OpenWeatherMap ──►  scraper_weather.py  ──►  data/json/weather/<YYYYMMDD>/
                    score_weather.py    ──►  data/csv/  (scores météo)
Booking.com    ──►  scraper_hotels.py   ──►  data/csv/<YYYYMMDD>/hotels-*.csv
                    load_csv_to_s3.py   ──►  AWS S3  (data lake)
                    load_to_db.py       ──►  PostgreSQL  (data warehouse)
                    kayak_ui.py         ──►  Streamlit  (dashboard)
```

## Prérequis

- Docker (recommandé) **ou** Python 3.13 + conda
- Clés API : OpenWeatherMap, AWS S3, AWS RDS ou Neon pour la base de données PostgreSQL

## Installation et configuration

### 1. Variables d'environnement

Copier le template et renseigner les valeurs :

```bash
cp .env_template .env
```

Variables requises dans `.env` :

| Variable | Description |
|---|---|
| `API_KEY_OWM` | Clé OpenWeatherMap |
| `AWS_ACCESS_KEY_ID` | Clé AWS |
| `AWS_SECRET_ACCESS_KEY` | Secret AWS |
| `AWS_REGION` | Région AWS (ex. `eu-west-3`) |
| `S3_BUCKET` | Nom du bucket S3 |
| `DATABASE_URL` | URL PostgreSQL (`postgresql://user:pass@host:port/db`) |

Variables optionnelles (valeur par défaut indiquée) :

| Variable | Défaut | Description |
|---|---|---|
| `S3_PREFIX` | `csv/` | Préfixe des clés S3 |
| `TOP_N_CITIES` | `5` | Nb de villes top à scraper (hôtels) |
| `TOP_N_HOTELS` | `20` | Nb max d'hôtels affichés (UI + BDD) |
| `LOCAL_RETENTION_DAYS` | `30` | Nb de répertoires `data/csv/YYYYMMDD/` conservés localement après upload S3 |
| `HISTORY_DAYS` | `30` | Étendue du graphique historique des scores (jours) |
| `CRON_SCHEDULE` | `0 7 * * *` | Planning cron du pipeline (heure Paris, TZ=Europe/Paris) |

### 2. Liste des villes

Éditer `config/cities.txt` — une ville par ligne (35 villes par défaut).

## Utilisation

### Initialisation de la base de données (une seule fois)

Avant le premier lancement du pipeline, créer le schéma PostgreSQL :

```bash
psql $DATABASE_URL -f sql/schema.sql
```

### Via Docker (recommandé)

Le pipeline s'exécute automatiquement chaque jour selon `CRON_SCHEDULE` (défaut : 07h00 heure de Paris) via cron.

```bash
# Build de l'image
docker build -t kayak .

# Lancement du container (pipeline automatique via cron)
docker run -d --env-file .env -v $(pwd)/data:/app/data kayak

# Suivi des logs
docker exec <container_id> tail -f /var/log/kayak.log

# Exécution manuelle immédiate du pipeline
docker exec <container_id> bash /app/pipeline.sh
```

### En local (conda)

```bash
# Créer et activer l'environnement
conda env create --file env_kayak.yml
conda activate kayak

# Installer le navigateur Chromium pour Playwright
conda run -n kayak playwright install chromium

# Lancer le pipeline complet
bash pipeline.sh

# Ou étape par étape
python src/scraper_cities.py     # 1. Géocodage des villes
python src/scraper_weather.py    # 2. Prévisions météo
python src/score_weather.py      # 3. Calcul des scores
python src/scraper_hotels.py     # 4. Scraping Booking.com
python src/load_csv_to_s3.py    # 5. Upload vers S3
python src/load_to_db.py        # 6. Chargement PostgreSQL
```

## Dashboard Streamlit

```bash
streamlit run src/kayak_ui.py
```

Ou en ligne sur [Streamlit Cloud](https://jedha-project-02-kayak-4kzhtcxgjjwncdsldqjdmq.streamlit.app/) et configurer dans les secrets de l'application
  - `DATABASE_URL` : adresse et paramètres d'accès à la base de données (obligatoire)
  - `TOP_N_HOTELS` : nombre d'hotels à afficher dans la carte et le tableau (optionnel, par défaut 20)

## Structure du projet

```
├── config/
│   └── cities.txt          # Liste des villes (une par ligne)
├── data/
│   ├── csv/                # Fichiers CSV générés par le pipeline
│   ├── json/               # Cache Nominatim et données OWM
│   └── html/               # Pages HTML Booking.com (debug)
├── docs/                   # Documentation complémentaire
├── sql/
│   └── schema.sql          # Création des 5 tables PostgreSQL (idempotent)
├── src/
│   ├── scraper_cities.py   # Phase 1 : géocodage Nominatim
│   ├── scraper_weather.py  # Phase 2 : prévisions OWM
│   ├── score_weather.py    # Phase 3 : calcul des scores météo
│   ├── scraper_hotels.py   # Phase 4 : scraping Booking.com
│   ├── load_csv_to_s3.py   # Phase 5 : upload S3
│   ├── load_to_db.py       # Phase 6 : chargement PostgreSQL
│   └── kayak_ui.py         # Phase 7 : dashboard Streamlit
├── Dockerfile              # Image unifiée pipeline + Playwright + cron
├── entrypoint.sh           # Expose les variables d'env à cron
├── pipeline.sh             # Orchestrateur des phases 1–6
├── env_kayak.yml           # Dépendances conda
└── requirements.txt        # Dépendances pip (Docker)
```

## Modèle de scoring météo

Score composite sur 4 jours (moyennes des créneaux 08h–20h) :

| Critère | Poids |
|---|---|
| Température (`feels_like`) | 30 % |
| Précipitations (`rain_proba`) | 30 % |
| Vent (`wind_speed`) | 15 % |
| Couverture nuageuse (`clouds`) | 10 % |
| Humidité (`humidity`) | 10 % |
| Pression atmosphérique (`pressure`) | 5 % |

Score de 0 à 100 — les 5 premières villes sont mises en avant dans le dashboard.
