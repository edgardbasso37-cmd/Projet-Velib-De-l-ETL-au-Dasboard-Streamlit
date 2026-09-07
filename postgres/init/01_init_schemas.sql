CREATE SCHEMA IF NOT EXISTS bronze;
CREATE SCHEMA IF NOT EXISTS silver;
CREATE SCHEMA IF NOT EXISTS gold;

CREATE TABLE IF NOT EXISTS bronze.velib_stations (
    id BIGSERIAL PRIMARY KEY,
    stationcode VARCHAR(20) NOT NULL,
    is_installed VARCHAR(5),
    name TEXT,
    capacity SMALLINT,
    numdocksavailable SMALLINT,
    numbikesavailable SMALLINT,
    mechanical SMALLINT,
    ebike SMALLINT,
    is_renting VARCHAR(5),
    is_returning VARCHAR(5),
    duedate TIMESTAMPTZ,
    lon DOUBLE PRECISION,
    lat DOUBLE PRECISION,
    nom_arrondissement_communes VARCHAR(50),
    code_insee_commune VARCHAR(10),
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_velib_station_update UNIQUE (stationcode, duedate)
);

CREATE INDEX IF NOT EXISTS idx_velib_duedate ON bronze.velib_stations USING BRIN (duedate);
CREATE INDEX IF NOT EXISTS idx_velib_stationcode ON bronze.velib_stations (stationcode);

CREATE TABLE IF NOT EXISTS bronze.meteo_paris (
    id BIGSERIAL PRIMARY KEY,
    measured_at TIMESTAMPTZ NOT NULL,
    temperature_2m REAL,
    relative_humidity_2m SMALLINT,
    apparent_temperature REAL,
    is_day SMALLINT,
    precipitation REAL,
    rain REAL, 
    showers REAL,
    snowfall REAL,
    cloud_cover SMALLINT,
    wind_speed_10m REAL,
    ingested_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CONSTRAINT uq_meteo_measured_at UNIQUE (measured_at)
);

CREATE INDEX IF NOT EXISTS idx_meteo_measured_at ON bronze.meteo_paris USING BRIN (measured_at);