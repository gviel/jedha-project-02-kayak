# Spécifications script : scraper_cities.py

## Role
Extraction des données des villes:
premier script du pipeline qui va récupérer les coordonnées géographiques WSG84 d'une liste de villes avec l'API Nominatim.

## Entrées
- Fichier de configuration : `config/cities.txt` — liste des villes, une par ligne, encodage UTF-8 (lignes vides ignorées)
- Répertoire cache : `data/json/cities` — fichiers JSON Nominatim par ville

## Sorties
- Fichier : `data/csv/cities.csv`
- Format : `.csv`
- Encodage : UTF-8

## Déroulement du script :

### Cache
- Fichier cache par ville : `data/json/cities/city-<city_name>.json` (espaces et apostrophes remplacés par `_`) — le `place_id` Nominatim n'est **pas** inclus dans le nom car il peut varier d'un jour à l'autre
- Recherche du fichier exact `city-<sanitized_name>.json` → si trouvé, données chargées depuis le cache sans appel API

### Pour chaque ville :
1. chercher dans le cache `data/json/cities/` via path exact `city-<sanitized_name>.json`
2. si absent du cache : appeler l'API Nominatim avec les paramètres `q=<city_name>`, `countrycodes=fr`, `format=json` — délai de 2s entre chaque requête (rate limit) ; en cas de 429 ou erreur 5xx : attente doublée + jitter aléatoire
3. si requête Nominatim positive : sauvegarder la réponse brute dans le cache (`city-<sanitized_name>-<place_id>.json`)
4. filtrer la réponse en retenant le premier résultat dont le champ `addresstype` est dans `['city', 'town', 'village', 'hamlet', 'municipality', 'islet', 'historic', 'tourism', 'county', 'gorge']`
5. si aucun résultat valide : enregistrer la ville avec `lat=None`, `lon=None`
6. construire une ligne avec les champs `city_id` (nom sanitized de la ville, stable et dérivé du nom — pas le `place_id` Nominatim qui varie), `city_name`, `lat`, `lon` dans un DataFrame pandas

### Sauvegarde
- Sauvegarder le DataFrame résultant (35 lignes maximum) dans `data/csv/cities.csv` (colonnes : `city_id, city_name, lat, lon`)