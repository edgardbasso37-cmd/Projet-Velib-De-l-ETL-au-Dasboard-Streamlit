# API météo

On récupère la météo de Paris en temps réel via l'API Open-Meteo. Les données sont actualisées tous les quarts d'heure. 

URL : `https://api.open-meteo.com/v1/forecast?latitude=48.8534&longitude=2.3488&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,cloud_cover,wind_speed_10m&timezone=Europe%2FParis&forecast_days=1`

- `time` : horodatage de la mesure
- `interval` : données rafraîchies toutes les 15 min
- `temperature_2m` : température à 2m du sol
- `apparent_temperature` : ressenti (wind chill + humidité)
- `relative_humidity_2m` : humidité relative à 2m
- `is_day` : 1 = journée, 0 = nuit
- `precipitation` : précipitations totales (15 min écoulées)
- `rain` : part pluie
- `showers` : part averses
- `snowfall` : part neige
- `cloud_cover` : couverture nuageuse totale
- `wind_speed_10m` : vitesse du vent à 10m

## Réponse 

```json
{
  "latitude": 48.86,
  "longitude": 2.3399997,
  "generationtime_ms": 0.12743473052978516,
  "utc_offset_seconds": 7200,
  "timezone": "Europe/Paris",
  "timezone_abbreviation": "GMT+2",
  "elevation": 43,
  "current_units": {
    "time": "iso8601",
    "interval": "seconds",
    "temperature_2m": "°C",
    "relative_humidity_2m": "%",
    "apparent_temperature": "°C",
    "is_day": "",
    "precipitation": "mm",
    "rain": "mm",
    "showers": "mm",
    "snowfall": "cm",
    "cloud_cover": "%",
    "wind_speed_10m": "km/h"
  },
  "current": {
    "time": "2026-04-03T16:15",
    "interval": 900,
    "temperature_2m": 12.7,
    "relative_humidity_2m": 68,
    "apparent_temperature": 9.6,
    "is_day": 1,
    "precipitation": 0,
    "rain": 0,
    "showers": 0,
    "snowfall": 0,
    "cloud_cover": 100,
    "wind_speed_10m": 15.8
  }
}
```