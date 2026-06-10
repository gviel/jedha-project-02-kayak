# Spécifications script : scraper_hotels.py

 ## Role
 Phase scraping d'hotels sur Booking.com pour les villes souhaitées.

## Configuration
Variable d'environnement (dans `.env`) :
  - `TOP_N_CITIES` — nombre de villes top à scraper (défaut : `5` si absent)

## Entrées
- Fichier : `data/csv/cities.csv`
- Site Booking.com : base URL `https://www.booking.com` (partie française en utilisant la page d'accueil `index.fr.html`)
- Paramètre CLI optionnel : `N` (écrase `TOP_N_CITIES` si fourni)

## Sorties
- Répertoires : `data/csv/<YYYYMMDD>/` (même structure que S3)
- Fichiers : 1 fichier par ville `hotels-{city_id}-{yyyyMMdd}.csv` pour le jour J (`city_id` = nom sanitized, underscores)
- Colonnes CSV : `city_id, city_name, hotel_name, lat, lon, description, score, url, address, city_label, zip_code`
- Encodage : UTF-8

## Stratégie d'extraction

Booking.com injecte les résultats de recherche dans un objet Apollo/GraphQL embarqué dans un `<script>` de la page de listing. Chaque hôtel est délimité par `{"__typename":"SearchResultProperty"}` et contient tous les champs nécessaires (`lat`, `lon`, `score`, `description`, `address`, `city`, `pageName`). Le champ `zipCode`/`postalCode` est tenté en fallback (présence incertaine selon la version du JSON Apollo).

Cette approche élimine la visite de chaque fiche hôtel individuelle, ce qui réduit le nombre de navigations Playwright de `1 + N_hotels` à `1` par ville.

## Déroulement
Les tâches avec playwright doivent être faites en async.

1. lire les top-N villes depuis `data/csv/<YYYYMMDD>/weather-scores-<YYYYMMDD>.csv` → retourne une liste de `city_id`
2. lancer un navigateur chromium avec playwright
3. aller sur l'accueil de booking.com en français
4. attendre le chargement
5. fermer les éventuelles popups
6. récupérer les cookies
7. sauvegarder la session (optionel)
8. pour chaque `city_id` (dériver `city_name = city_id.replace("_", " ")`) :
    1. cliquer dans l'input box de recherche
    2. tout séletionner et tout effacer
    3. taper le texte `city_name` + délai pour simuler un humain
    4. attendre la liste de propositions et cliquer sur la première
    5. lancer la recherche
    6. cliquer à gauche + supprimer éventuelles popups
    7. appliquer le filtre case à cocher 'Hotels'
    8. sauver la page html pour debug (optionnel)
    9. parser le JSON Apollo embarqué dans le HTML (`parse_hotels_from_listing`) pour extraire `hotel_name`, `lat`, `lon`, `score`, `description`, `url`, `address`
    10. sauver les données dans un fichier CSV par ville (`hotels-{city_id}-{yyyyMMdd}.csv`) avec colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url, address`
