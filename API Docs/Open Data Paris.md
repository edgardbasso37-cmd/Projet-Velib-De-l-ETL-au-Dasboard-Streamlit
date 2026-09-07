#  API Vélib - Vélos et bornes - Disponibilité temps réel

On se limitera uniquement aux stations situées à Paris. Les données sont actualisés chaque minute.
La limite de 100 résultats est imposée par l'API, il faudra faire plusieurs requêtes pour récupérer les données de toutes les stations, avec une pagination basée sur le paramètre `offset`.

URL : `https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/velib-disponibilite-en-temps-reel/records?order_by=capacity%20DESC&limit=100&offset=0&refine=nom_arrondissement_communes%3A%22Paris%22&timezone=Europe%2FParis`

- `stationcode` : code de la station
- `name` : nom de la station
- `is_installed` : station installée ou non
- `capacity` : nombre total de bornes de la station
- `numdocksavailable` : nombre de bornes disponibles pour attacher un vélo
- `numbikesavailable` : nombre de vélos disponibles à la location
- `mechanical` : nombre de vélos mécaniques disponibles
- `ebike` : nombre de vélos électriques disponibles
- `is_renting` : variable binaire indiquant si la station peut louer des vélos (is_renting=1 si le statut de la station est Operative)
- `is_returning` : variable binaire indiquant si la station peut recevoir des vélos (is_renting=1 si le statut de la station est Operative)
- `duedate` : date de la dernière mise à jour des données
- `lon` et `lat` : coordonnées géographiques de la station
- `nom_arrondissement_communes` : nom de la commune ou arrondissement où se situe la station
- `code_insee_commune` : code INSEE de la commune où se situe la station

## Réponse 

```json
{
  "total_count": 994,
  "results": [
    {
      "stationcode": "12507",
      "name": "Hippodrome de Paris Vincennes",
      "is_installed": "OUI",
      "capacity": 105,
      "numdocksavailable": 97,
      "numbikesavailable": 3,
      "mechanical": 2,
      "ebike": 1,
      "is_renting": "NON",
      "is_returning": "NON",
      "duedate": "2026-02-22T18:30:40+00:00",
      "coordonnees_geo": {
        "lon": 2.4502807724015,
        "lat": 48.820484866661
      },
      "nom_arrondissement_communes": "Paris",
      "code_insee_commune": "75056",
      "station_opening_hours": null
    },
    {
      "stationcode": "15104",
      "name": "Hôpital Européen Georges Pompidou",
      "is_installed": "OUI",
      "capacity": 78,
      "numdocksavailable": 0,
      "numbikesavailable": 75,
      "mechanical": 67,
      "ebike": 8,
      "is_renting": "OUI",
      "is_returning": "OUI",
      "duedate": "2026-04-02T07:37:37+00:00",
      "coordonnees_geo": {
        "lon": 2.2753742337227,
        "lat": 48.837695319163
      },
      "nom_arrondissement_communes": "Paris",
      "code_insee_commune": "75056",
      "station_opening_hours": null
    },
    ...
  ]
}
```
