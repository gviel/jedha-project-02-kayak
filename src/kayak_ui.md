# Spécification script : kayak_ui.py

## Role
Cette interface utilisateur doit permettre de visualiser les résultats de la base de données sous la forme

## Configuration
Variables d'environnement lues par le script (via `.env` en local, ou secrets Streamlit Cloud en déploiement) :

| Variable | Obligatoire | Défaut | Description |
|---|---|---|---|
| `DATABASE_URL` | oui | — | URL de connexion PostgreSQL (`postgresql://user:pass@host:port/db`) |
| `TOP_N_HOTELS` | non | `20` | Nombre max d'hôtels affichés par ville (LIMIT SQL + tableau UI) |

En l'absence de `DATABASE_URL`, l'UI tente un fallback sur les fichiers CSV locaux (`data/csv/`).

## Entrées
  - Base de données Postgresql (chez AWS RDS ou Neon)

## Sortie
  - carte 1 : permettant de visualiser le scoring météo des destination de voyage, pour la liste de villes de France choisies, grâce au scoring météo obtenu grâce aux appels API Nominatim et OWM. On mettra en évidence le scoring pour les 5 premières destinations.
  - carte 2 : permettant d'afficher les meilleurs hotels pour une ville choisie sur la carte
  - graphique historique : courbe des scores météo journaliers de la ville sélectionnée sur les 30 derniers jours

## Description de l'UI
  - Design : de type agence de voyage
  - en sous-titre: indiquer que les scores météo sont pour les jour J+1 à J+4 (les 4 dates les plus récentes de `weather_scores_daily`) et les données extraites à J (date d'upload des données)
  - premier bloc :
    - carte 1 : l'importance du scoring représenté avec des ronds de taille plus ou moins importante et dégradé de couleur du rouge (mauvais score) au vert (meilleur score)
    - à droite de la carte : mettre le tableau des villes classées dans l'ordre de leur score météo (avec juste les champs `city_name` et `mean` visibles; on mettra un icone de type 'étoile jaune' devant le city_name des 5 premières villes
    - en dessous une combo box avec la liste des 10 premières villes classées par leur scoring; la taille de la combo box doit être dimensionnée sur la ville ayant le nom le plus long
  - deuxième bloc :
    - carte 2
      - affichage global avec niveau de zoom contenant tous les hotels (calcul bounding box) et centrée sur le meilleur hotel
      - de type openstreetmap qui montre tous les hotels d'une ville choisie par clic dans la carte précédente
      - lorsque l'on clique sur un hotel (représenté par un icone), affichage de descriptif de l'hotel et son score
    - à droite de la carte 2, tableau avec la liste des 20 premiers hôtels correspondants à la carte avec les champs `hotel_name`, `score`,`url` vers Booking.com
  - troisième bloc (sous le deuxième) :
    - graphique linéaire (`score_day`) sur les 30 derniers jours pour la ville sélectionnée dans la carte 2
    - données lues depuis `weather_scores_daily` filtrées sur `city_id` et `date >= CURRENT_DATE - 30 jours`
    - fond coloré par zones de score : vert (80–100), jaune (60–80), orange (40–60), rouge (0–40)
    - si aucune donnée, afficher un message d'info invitant à attendre les prochaines extractions