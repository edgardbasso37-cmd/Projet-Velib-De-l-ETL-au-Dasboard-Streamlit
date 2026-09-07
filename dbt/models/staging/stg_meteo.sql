SELECT
    measured_at,
    temperature_2m,
    relative_humidity_2m AS humidity,
    apparent_temperature,
    is_day = 1 AS is_day,
    precipitation,
    rain,
    showers,
    snowfall,
    cloud_cover,
    wind_speed_10m
FROM {{ source('bronze', 'meteo_paris') }}
