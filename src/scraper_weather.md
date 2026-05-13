# Spécifications script : scraper_weather.py

## Role
Phase extraction puis transformation des données météo.

## Entrées
- Fichier : `data/csv/cities.csv`
- API OpenWeatherMap (OWM) :
  - on utilisera les paramètères cnt=100 et units=metric appid=<API key>
  - on passera les valeurs `lon` et `lat` de la ville à l'API
  - le retour de l'API est en JSON

## Sorties
- Répertoire : `data/json/weather/<YYYYMMDD>` avec YYYYMMDD la date de la prévision météo (valeur J+1 à J+4) au jour J
- Fichiers : 1 pattern `weather-<city_name>-<yyyyMMdd>.json` par jour de prévision
- Format : `.json`

## Déroulement

### 1. Extraction
Pour chaque ville : en utilisant les coordonnées de chaque ville contenues dans le fichier @data/csv/cities.csv, extraire les données météo avec l'API OWM de J+1 à J+4 (sur 4 jours avec 8 valeurs par jour).

### 2. Transformation
On transformera la réponse JSON obtenue de l'API OWM pour la ville avec les specs GLOM suivantes :
`glom_transformation_specs = {
    "dt": "dt",
    "dt_str": "dt_txt",
    "date": ("dt", tstamp_to_date),
    "time": ("dt", tstamp_to_time),
    "temp": "main.temp",
    "feels_like": "main.feels_like",
    "temp_min": "main.temp_min",
    "temp_max": "main.temp_max",
    "pressure": "main.pressure",
    "humidity": "main.humidity",
    "weather_id": "weather.0.id",
    "weather_desc": "weather.0.main",
    "clouds" : "clouds.all",
    "wind_speed": "wind.speed",
    "rain_proba": "pop"
}`

### 3. Sauvegarde
J étant la date de l'extraction, le résultat de la transformation GLOM sera sauvé dans 4 fichiers différents avec le pattern `data/json/weather/<yyyyMMdd>/weather-<city_name>-<yyyyMMdd>.json` avec yyyyMMdd pouvant prendre les valeurs J+1, J+2, J+3 et J+4.
Si le fichier existe déjà pour un des jours donnés, on n'envoie pas la requete et on ne le sauve pas et on regarder le jour suivant.
