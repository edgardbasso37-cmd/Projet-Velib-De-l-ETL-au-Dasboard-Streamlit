SELECT
    v.stationcode,
    v.station_name,
    v.commune,
    v.code_insee_commune,
    v.lat,
    v.lon,
    v.capacity,
    v.docks_available,
    v.bikes_available,
    v.mechanical,
    v.ebike,
    v.duedate,
    m.measured_at AS meteo_measured_at,
    m.temperature_2m,
    m.humidity,
    m.apparent_temperature,
    m.is_day,
    m.precipitation,
    m.rain,
    m.showers,
    m.snowfall,
    m.cloud_cover,
    m.wind_speed_10m
FROM {{ ref('stg_velib') }} v
INNER JOIN LATERAL (
    SELECT *
    FROM {{ ref('stg_meteo') }} m
    WHERE m.measured_at BETWEEN v.duedate - INTERVAL '15 minutes' AND
          v.duedate + INTERVAL '15 minutes'
    ORDER BY ABS(EXTRACT(EPOCH FROM (m.measured_at - v.duedate)))
    LIMIT 1
) m ON true
WHERE v.is_installed AND v.is_renting
