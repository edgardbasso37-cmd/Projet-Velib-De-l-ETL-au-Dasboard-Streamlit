SELECT

    stationcode,
    station_name,
    commune,
    code_insee_commune,
    lat,
    lon,
    capacity,
    docks_available,
    bikes_available,
    mechanical,
    ebike,

    (duedate AT TIME ZONE 'Europe/Paris')::TIMESTAMP AS duedate,
    (meteo_measured_at AT TIME ZONE 'Europe/Paris')::TIMESTAMP AS meteo_measured_at,

    EXTRACT(HOUR FROM duedate AT TIME ZONE 'Europe/Paris')::SMALLINT AS hours_of_day,
    EXTRACT(DOW FROM duedate AT TIME ZONE 'Europe/Paris')::SMALLINT AS day_of_week,
    EXTRACT(MONTH FROM duedate AT TIME ZONE 'Europe/Paris')::SMALLINT AS month,
    EXTRACT(DOW FROM duedate AT TIME ZONE 'Europe/Paris') IN (0, 6) AS is_weekend,

    temperature_2m,
    humidity,
    apparent_temperature,
    is_day,
    precipitation,
    rain,
    showers,
    snowfall,
    cloud_cover,
    wind_speed_10m,

    ROUND(
        bikes_available::numeric / NULLIF(bikes_available + docks_available, 0) * 100,
        2
    ) AS occupancy_rate

FROM {{ ref('int_velib_meteo') }}