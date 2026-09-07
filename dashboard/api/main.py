"""
FastAPI — backend du dashboard Vélib.

Expose des endpoints JSON pour chaque couche de la pipeline (bronze, gold)
ainsi que les statistiques et les coordonnées des stations pour la carte.
"""

import logging
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo

import psycopg2
import psycopg2.extras
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo("Europe/Paris")


def _fmt_paris(dt: datetime) -> str:
    """
    Formate un datetime en chaîne lisible heure de Paris.

    - datetime timezone-aware (TIMESTAMPTZ, stocké UTC par psycopg2) : on convertit.
    - datetime naïf (TIMESTAMP, déjà en heure de Paris après cast dbt ::TIMESTAMP) :
      on formate directement sans conversion pour éviter le décalage +2h.
    """
    if dt.tzinfo is not None:
        dt = dt.astimezone(PARIS_TZ)
    return dt.strftime("%d/%m/%Y %H:%M")


def localize_rows(rows: list[dict]) -> list[dict]:
    """
    Convertit les colonnes datetime (TIMESTAMPTZ → UTC) en chaînes
    heure de Paris dans les réponses destinées aux dataframes Streamlit.
    Les endpoints de graphique (historique) n'utilisent PAS cette fonction
    afin de conserver des timestamps ISO parsables par Plotly/pandas.
    """
    out = []
    for row in rows:
        out.append({
            k: _fmt_paris(v) if isinstance(v, datetime) else v
            for k, v in row.items()
        })
    return out


# ─── Configuration ────────────────────────────────────────────────────────────

class Settings(BaseSettings):
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "velib"
    postgres_password: str = "password"
    postgres_db: str = "velib_db"

    model_config = {"env_file": ".env"}


settings = Settings()


# ─── Application ──────────────────────────────────────────────────────────────

app = FastAPI(title="Vélib Dashboard API", version="1.0.0")

# Streamlit tourne sur le même hôte — on autorise localhost:8501
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501"],
    allow_methods=["GET"],
    allow_headers=["*"],
)


# ─── Helpers DB ───────────────────────────────────────────────────────────────

@contextmanager
def get_db():
    conn = psycopg2.connect(
        host=settings.postgres_host,
        port=settings.postgres_port,
        user=settings.postgres_user,
        password=settings.postgres_password,
        dbname=settings.postgres_db,
    )
    try:
        yield conn
    finally:
        conn.close()


def query_one(sql: str, params=None) -> dict | None:
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            row = cur.fetchone()
            return dict(row) if row else None


def query_all(sql: str, params=None) -> list[dict]:
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(sql, params)
            return [dict(row) for row in cur.fetchall()]


# ─── Routes ───────────────────────────────────────────────────────────────────

@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/status")
def get_status():
    """Dates de dernière collecte et compteurs pour Vélib et Météo."""
    try:
        velib = query_one("""
            SELECT
                MAX(ingested_at)            AS last_ingestion,
                MAX(duedate)                AS last_update,
                COUNT(*)                    AS total_rows,
                COUNT(DISTINCT stationcode) AS unique_stations
            FROM bronze.velib_stations
        """)
        meteo = query_one("""
            SELECT
                MAX(ingested_at)  AS last_ingestion,
                MAX(measured_at)  AS last_measure,
                COUNT(*)          AS total_rows
            FROM bronze.meteo_paris
        """)
        return {"velib": velib, "meteo": meteo}
    except Exception as exc:
        logger.exception("Erreur dans /api/status")
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bronze/velib/stats")
def velib_bronze_stats():
    """Statistiques agrégées de bronze.velib_stations."""
    try:
        return query_one("""
            SELECT
                COUNT(*)                          AS total_rows,
                COUNT(DISTINCT stationcode)       AS unique_stations,
                MIN(duedate)                      AS earliest_measure,
                MAX(duedate)                      AS latest_measure,
                MIN(ingested_at)                  AS earliest_ingestion,
                MAX(ingested_at)                  AS latest_ingestion,
                ROUND(AVG(numbikesavailable)::numeric, 2) AS avg_bikes_available,
                ROUND(AVG(numdocksavailable)::numeric, 2) AS avg_docks_available,
                ROUND(AVG(capacity)::numeric, 2)          AS avg_capacity
            FROM bronze.velib_stations
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bronze/velib/preview")
def velib_bronze_preview(limit: int = Query(default=10, ge=1, le=100)):
    """Derniers enregistrements de bronze.velib_stations (dates en heure de Paris)."""
    try:
        rows = query_all(
            "SELECT * FROM bronze.velib_stations ORDER BY ingested_at DESC LIMIT %s",
            (limit,),
        )
        return localize_rows(rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bronze/meteo/stats")
def meteo_bronze_stats():
    """Statistiques agrégées de bronze.meteo_paris."""
    try:
        return query_one("""
            SELECT
                COUNT(*)                                       AS total_rows,
                MIN(measured_at)                               AS earliest_measure,
                MAX(measured_at)                               AS latest_measure,
                MIN(ingested_at)                               AS earliest_ingestion,
                MAX(ingested_at)                               AS latest_ingestion,
                ROUND(AVG(temperature_2m)::numeric, 2)        AS avg_temperature,
                ROUND(AVG(relative_humidity_2m)::numeric, 2)  AS avg_humidity,
                ROUND(AVG(wind_speed_10m)::numeric, 2)        AS avg_wind_speed
            FROM bronze.meteo_paris
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/bronze/meteo/preview")
def meteo_bronze_preview(limit: int = Query(default=10, ge=1, le=100)):
    """Derniers enregistrements de bronze.meteo_paris (dates en heure de Paris)."""
    try:
        rows = query_all(
            "SELECT * FROM bronze.meteo_paris ORDER BY measured_at DESC LIMIT %s",
            (limit,),
        )
        return localize_rows(rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/gold/stats")
def gold_stats():
    """Statistiques agrégées de gold.fct_velib_meteo."""
    try:
        return query_one("""
            SELECT
                COUNT(*)                                    AS total_rows,
                COUNT(DISTINCT stationcode)                 AS unique_stations,
                MIN(duedate)                                AS earliest_record,
                MAX(duedate)                                AS latest_record,
                ROUND(AVG(occupancy_rate)::numeric, 2)     AS avg_occupancy_rate,
                ROUND(MIN(occupancy_rate)::numeric, 2)     AS min_occupancy_rate,
                ROUND(MAX(occupancy_rate)::numeric, 2)     AS max_occupancy_rate,
                ROUND(AVG(temperature_2m)::numeric, 2)     AS avg_temperature
            FROM gold.fct_velib_meteo
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/gold/preview")
def gold_preview(limit: int = Query(default=10, ge=1, le=100)):
    """Derniers enregistrements de gold.fct_velib_meteo (dates en heure de Paris)."""
    try:
        rows = query_all(
            "SELECT * FROM gold.fct_velib_meteo ORDER BY duedate DESC LIMIT %s",
            (limit,),
        )
        return localize_rows(rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/stations")
def get_stations():
    """
    Retourne une entrée par station (dédupliquée sur stationcode),
    avec ses coordonnées GPS.
    """
    try:
        return query_all("""
            SELECT DISTINCT ON (stationcode)
                stationcode,
                name                          AS station_name,
                lat,
                lon,
                nom_arrondissement_communes   AS commune,
                capacity
            FROM bronze.velib_stations
            WHERE lat IS NOT NULL
              AND lon IS NOT NULL
            ORDER BY stationcode, ingested_at DESC
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/gold/export")
def gold_export():
    """Export complet de gold.fct_velib_meteo (toutes les lignes, dates heure de Paris)."""
    try:
        rows = query_all("SELECT * FROM gold.fct_velib_meteo ORDER BY duedate DESC")
        return localize_rows(rows)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/stations/occupancy")
def get_stations_occupancy():
    """
    Stations avec leur taux d'occupation le plus récent (depuis gold.fct_velib_meteo).
    Retourne une liste vide si la couche gold n'est pas encore alimentée.
    """
    try:
        return query_all("""
            SELECT DISTINCT ON (g.stationcode)
                g.stationcode,
                b.name                                      AS station_name,
                b.lat,
                b.lon,
                b.nom_arrondissement_communes               AS commune,
                b.capacity,
                ROUND(g.occupancy_rate::numeric, 2)        AS occupancy_rate,
                g.bikes_available,
                g.docks_available
            FROM gold.fct_velib_meteo g
            JOIN (
                SELECT DISTINCT ON (stationcode)
                    stationcode, name, lat, lon,
                    nom_arrondissement_communes, capacity
                FROM bronze.velib_stations
                WHERE lat IS NOT NULL AND lon IS NOT NULL
                ORDER BY stationcode, ingested_at DESC
            ) b ON g.stationcode = b.stationcode
            ORDER BY g.stationcode, g.duedate DESC
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/stations/list")
def get_stations_list():
    """Liste triée des stations (code + nom) pour le sélecteur du dashboard."""
    try:
        return query_all("""
            SELECT DISTINCT ON (stationcode)
                stationcode,
                name AS station_name,
                capacity
            FROM bronze.velib_stations
            ORDER BY stationcode, ingested_at DESC
        """)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/station/{stationcode}/history")
def get_station_history(
    stationcode: str,
    period: str = Query(default="today", pattern="^(today|7d|30d|month)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    """
    Historique d'occupation d'une station sur une période donnée.

    Périodes disponibles :
    - today  : dernières 24 heures
    - 7d     : 7 derniers jours
    - 30d    : 30 derniers jours
    - month  : mois calendaire (paramètre `month` requis, format YYYY-MM)
    """
    try:
        if period == "today":
            where_extra = "AND duedate >= NOW() - INTERVAL '1 day'"
            params: tuple = (stationcode,)
        elif period == "7d":
            where_extra = "AND duedate >= NOW() - INTERVAL '7 days'"
            params = (stationcode,)
        elif period == "30d":
            where_extra = "AND duedate >= NOW() - INTERVAL '30 days'"
            params = (stationcode,)
        else:  # month
            if not month:
                raise HTTPException(
                    status_code=422,
                    detail="Le paramètre 'month' (format YYYY-MM) est requis pour period=month",
                )
            where_extra = "AND DATE_TRUNC('month', duedate) = DATE_TRUNC('month', %s::date)"
            params = (stationcode, month + "-01")

        rows = query_all(
            f"""
            SELECT
                duedate,
                ROUND(occupancy_rate::numeric, 2)     AS occupancy_rate,
                bikes_available,
                docks_available,
                ROUND(temperature_2m::numeric, 1)     AS temperature_2m,
                ROUND(precipitation::numeric, 2)      AS precipitation
            FROM gold.fct_velib_meteo
            WHERE stationcode = %s
              {where_extra}
            ORDER BY duedate
            """,
            params,
        )
        return rows
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/city/trend")
def get_city_trend(
    period: str = Query(default="7d", pattern="^(today|7d|30d|month)$"),
    month: str | None = Query(default=None, pattern=r"^\d{4}-\d{2}$"),
):
    """
    Tendance globale Paris : occupation moyenne de toutes les stations,
    température et précipitations, agrégées par heure.

    Périodes disponibles :
    - today  : dernières 24 heures
    - 7d     : 7 derniers jours (défaut)
    - 30d    : 30 derniers jours
    - month  : mois calendaire (paramètre `month` requis, format YYYY-MM)
    """
    try:
        if period == "today":
            where_clause = "WHERE duedate >= NOW() - INTERVAL '1 day'"
            params: tuple = ()
        elif period == "7d":
            where_clause = "WHERE duedate >= NOW() - INTERVAL '7 days'"
            params = ()
        elif period == "30d":
            where_clause = "WHERE duedate >= NOW() - INTERVAL '30 days'"
            params = ()
        else:  # month
            if not month:
                raise HTTPException(
                    status_code=422,
                    detail="Le paramètre 'month' (format YYYY-MM) est requis pour period=month",
                )
            where_clause = "WHERE DATE_TRUNC('month', duedate) = DATE_TRUNC('month', %s::date)"
            params = (month + "-01",)

        rows = query_all(
            f"""
            SELECT
                DATE_TRUNC('hour', duedate)                        AS ts,
                ROUND(AVG(occupancy_rate)::numeric, 2)             AS avg_occupancy,
                ROUND(AVG(temperature_2m)::numeric, 1)             AS temperature_2m,
                -- precipitation est identique pour toutes les stations (méteo citywide)
                ROUND(AVG(precipitation)::numeric, 2)              AS precipitation
            FROM gold.fct_velib_meteo
            {where_clause}
            GROUP BY DATE_TRUNC('hour', duedate)
            ORDER BY ts
            """,
            params,
        )
        return rows
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
