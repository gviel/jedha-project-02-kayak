# Spécifications script : scraper_hotels.py

 ## Role
 Phase scraping d'hotels sur Booking.com pour les villes souhaitées.

## Entrées
- Fichier : `data/csv/cities.csv`
- Site Booking.com : base URL `https://www.booking.com` (partie française en utilisant la page d'accueil `index.fr.html`)
- Paramètre du script : TOP_N le nombre de villes au top (par défaut 5 si aucune valeur fournie)

## Sorties
- Répertoires : `data/csv/<YYYYMMDD>/` (même structure que S3)
- Fichiers : 1 fichier par ville `hotels-{city_id}-{yyyyMMdd}.csv` pour le jour J (`city_id` = nom sanitized, underscores)
- Colonnes CSV : `city_id, city_name, hotel_name, lat, lon, description, score, url`
- Encodage : UTF-8

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
    9. récupérer le nom de l'hotel et l'URL de la fiche de l'hotel
    10. pour chaque hotel :
        1. aller à la fiche de l'hotel
        2. sauver la page html pour debug (optionel)
        3. récupérer lat, lon, description et score
        4. sauver les données dans un fichier CSV par ville (`hotels-{city_id}-{yyyyMMdd}.csv`) avec colonnes : `city_id, city_name, hotel_name, lat, lon, description, score, url`
