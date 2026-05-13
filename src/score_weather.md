# Spécifications script : score_weather.py

# Définition du système de notation

On réalise une classification par tranche des valeurs de météo. Ces seuils et scores sont issus d’études climatologiques (ICT de Mieczkowski) et de standards utilisés par les institutions météorologiques, adaptés aux besoins du tourisme pour offrir un indice synthétique fiable.

1. Scoring Température : champ `feels_like`
  - <0 : très froid, score 0/10
  - 0-10 : froid, score 2/10
  - 11-17 : frais, score 5/10
  - 18-28 : idéal, score 10/10
  - 29-33 : chaud, score 5/10
  - \>33 : très chaud, score 0/10

2. Scoring Précipitations: champ `rain_proba`
  - 0 mm : Sec, idéal, score 10/10.
  - 0,1-1 mm : Faible pluie/bruine, score 8/10.
  - 1-10 mm : Pluie modérée, score 5/10.
  - 11-30 mm : Pluie forte, score 2/10.
  - 30 mm : Pluie très forte, score 0/10.
  
Mais le niveau de précipitation n'est pas présent dans les données gratuites de l'API, donc on utilise le champ `rain_proba` (OWM `pop`, valeur 0.0–1.0) avec la formule : `score = (1 − rain_proba) × 10`
 
3. Scoring Vent : champ `wind_speed`
  L'API OWM renvoie `wind_speed` en m/s (paramètre `units=metric`) ; conversion appliquée : `kmh = wind_speed × 3.6`
  - 0-15 km/h : Agréable ou léger, score 10/10.
  - 16-28 km/h : Modéré, score 8/10.
  - 29-38 km/h : Bonne brise, score 5/10.
  - 39-61 km/h : Vent frais ou grand frais, score 2/10.
  - >61 km/h : Fort coup de vent/tempête, score 0/10.

4. Scoring Couverture nuageuse : champ `clouds`
  L'API OWM renvoie `clouds.all` en pourcentage (0–100 %) ; conversion appliquée : `oktas = clouds / 10`
  - 0-4 dixièmes (0–40 %) : dégagé à généralement dégagé, score 10/10.
  - 5-9 dixièmes (50–90 %) : généralement nuageux, score 6/10.
  - 10 dixièmes (100 %) : nuageux, score 2/10.

5. Scoring Humidité relative : champ `humidity`
  - 40-70% : Confortable, score 10/10.
  - 70-80% : Humide, score 7/10.
  - 20-39% : Sec, score 7/10.
  - \<20% ou >80% : Très inconfortable, score 3/10

6. Scoring Pression atmosphérique (hPa) : champ `pressure`
  - < 980 : Dépression sévère, mauvais temps probable, socre 1/10
  - 980–995 : Basse pression : instabilité, risque pluie/vent, score 3/10
  - 996–1005 :  Légère instabilité à modérée, score 6/10                     
  - 1006–1015 : Zone idéale, temps stable, score 10/10
  - 1016–1025 : Haute pression, possible ciel dégagé, score 8/10           
  - 1026–1035 : Anticyclone marqué, air sec, risque canicule, score 6/10
  - \>1035 : Très forte pression : canicule ou brouillard, score 3/10 

7. Scoring Description générale du temps : champs `wheather_id` `weather_desc`
Donnée difficilement utilisable et difficile à synthétiser/agréger : on n'utilisera pas cette donnée pour l'instant
  - 2xx : thunderstorm
  - 3xx : drizzle
  - 5xx : rain
  - 6xx : snow
  - 7xx : atmosphere
  - 8xx : clear

# Pondération et aggrégations des résultats par prévision

1. Pour chaque ville, on a des données de prévision toutes les 3h pour chaque journée J+1 jusque J+4, donc 8 données/jour/ville.
On va effectuer une aggrégation en prenant la moyenne des valeurs de 08:00 à 20:00 pour chaque jour par ville afin d'obtenir une prévision/jour/ville (au lieu de 8).

2. Définition des poids pour chaque critère selon la destination et la saison (par exemple, la pluie vaut plus pour la visite de monuments).

| Critère | Pondération (%) | Justification |
| :-- | :-- | :-- |
| Température | 30 | Crucial pour le confort et la sécurité lors des activités extérieures |
| Précipitations | 30 | Forte pluie, neige ou grêle impactent négativement la plupart des activités touristiques. |
| Vent | 15 | Vent fort gêne les déplacements, crée des risques pour certaines activités. |
| Couverture nuageuse | 10 | Les journées très couvertes ou brumeuses affectent la visibilité et l’ambiance. |
| Humidité | 10 | Taux d’humidité élevé ou très faible peut altérer le confort. |
| Pression atmosphérique | 5 | Indice complémentaire, associé aux conditions (anticyclone/dépression) |
 
3. Calcul d'un score global pour chaque journée pour chaque ville

Proposition d'une échelle de 0 à 100, où :
  - 80-100 : Conditions idéales pour le tourisme
  - 60-79  : Conditions acceptables, quelques désagréments possibles
  - 40-59  : Conditions médiocres, tourisme possible mais limité
  - 0-39   : Conditions défavorables, tourisme déconseillé

Score = (Température×0.3) + (Précipitations×0.3) + (Vent×0.15) + (Couverture nuageuse×0.10) + (Humidité×0.1) + (Pression atmo×0.05)

4. Calcul score final pour la période de 4 jours
On calcule la moyenne, médiane, min, max et écart-type (std) des scores journaliers.

Puis on applique une **pénalité cumulative** pour variabilité excessive :
- `-10` si `min < mean − 3 × std` (score plancher anormalement bas)
- `-10` supplémentaire si `max > mean + 3 × std` (score plafond anormalement haut)
- La pénalité totale peut donc atteindre `-20`

`score_final = mean + penalty`  (penalty ∈ {0, −10, −20})

Cette pénalité permet de déclasser les destinations dont la météo est trop instable sur la période, même si leur moyenne est élevée.

# Production fichiers résultats

Fichiers d'entrée lus : `data/json/weather/<yyyyMMdd>/weather-<city_name>-<yyyyMMdd>.json` pour chaque ville et chaque jour J+1 à J+4 produits par @src/scraper_weather.py

Seuls les slots horaires **08:00:00 à 20:00:00** (champ `time`) sont retenus pour l'agrégation journalière (moyenne des slots diurnes).

Fichiers de sortie générés dans `data/csv/<YYYYMMDD>/` :
  - `weather-scores-daily-<YYYYMMDD>.csv` : colonnes `city_id`, `city_name`, `date`, `score_day` — une ligne par ville × jour
  - `weather-scores-<YYYYMMDD>.csv` : colonnes `city_id`, `city_name`, `mean`, `median`, `min`, `max`, `std`, `score_final` — une ligne par ville, trié par `score_final` décroissant
