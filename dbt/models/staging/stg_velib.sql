SELECT
    stationcode,
    name AS station_name,
    capacity,
    numdocksavailable AS docks_available,
    numbikesavailable AS bikes_available,
    mechanical,
    ebike,
    is_installed = 'OUI' AS is_installed,
    is_renting = 'OUI' AS is_renting,
    duedate,
    lon,
    lat,
    nom_arrondissement_communes AS commune,
    code_insee_commune
FROM {{ source('bronze', 'velib_stations') }}
