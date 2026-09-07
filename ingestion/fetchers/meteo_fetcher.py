"""
Fetcher météo : appel API Open-Meteo -> insertion bronze.meteo_paris

Flux :
  API Open-Meteo -> extraction objet "current" -> PostgreSQL bronze

L'API rafraîchit les données toutes les 15 minutes.
La déduplication est gérée par la contrainte uq_meteo_measured_at (measured_at).
Si on collecte toutes les 10 min, une mesure sur deux sera un doublon ignoré silencieusement.
"""

import logging
from datetime import datetime
from zoneinfo import ZoneInfo

import httpx
import psycopg2
import psycopg2.extensions

from config import settings
import time

logger = logging.getLogger(__name__)


class MeteoFetcher:
    def __init__(self) -> None:
        self._conn: psycopg2.extensions.connection | None = None

    def _get_conn(self) -> psycopg2.extensions.connection:
        # Reconnexion transparente si la connexion a été perdue entre deux runs
        if self._conn is None or self._conn.closed:
            self._conn = self._connect_with_retry()
        return self._conn

    def _connect_with_retry(
        self, attempts: int = 10, delay: float = 3.0
    ) -> psycopg2.extensions.connection:
        for attempt in range(1, attempts + 1):
            try:
                conn = psycopg2.connect(
                    host=settings.postgres_host,
                    port=settings.postgres_port,
                    user=settings.postgres_user,
                    password=settings.postgres_password,
                    dbname=settings.postgres_db
                )
                logger.info("Connexion PostgreSQL établie (tentative %d)", attempt)
                return conn
            except psycopg2.OperationalError as exc:
                logger.warning(
                    "PostgreSQL non disponible (tentative %d/%d) : %s",
                    attempt,
                    attempts,
                    exc,
                )
                if attempt < attempts:
                    time.sleep(delay)
        raise RuntimeError(
            f"Impossible de se connecter à PostgreSQL après {attempts} tentatives"
        )

    def run(self) -> None:
        logger.info("Démarrage de la collecte météo…")
        try:
            weather = self._fetch_current_weather()
        except Exception:
            logger.exception("Erreur lors de la collecte météo")
            return

        if weather is None:
            logger.warning("Réponse météo vide, rien à insérer")
            return

        try:
            inserted = self._insert_weather(weather)
            if inserted:
                logger.info("Météo insérée pour %s", weather["time"])
            else:
                logger.info("Météo déjà présente pour %s (doublon ignoré)", weather["time"])
        except Exception:
            logger.exception("Erreur lors de l'insertion météo")

    def _fetch_current_weather(self) -> dict | None:
        with httpx.Client(timeout=30.0) as client:
            response = client.get(settings.meteo_api_url)
            response.raise_for_status()
            data = response.json()

        current: dict = data.get("current", {})
        if not current:
            return None

        # "interval" est une métadonnée technique (durée de la fenêtre de mesure),
        # pas une feature utile
        current.pop("interval", None)

        # L'API renvoie "time" en heure locale (timezone=Europe/Paris dans l'URL),
        # sans suffixe de fuseau horaire (ex: "2026-04-07T16:15").
        # Sans annotation explicite, psycopg2 l'insèrerait comme UTC dans TIMESTAMPTZ,
        # ce qui décalerait l'heure de +2h à l'affichage. On attache le bon fuseau.
        raw_time: str = current["time"]
        current["time"] = datetime.fromisoformat(raw_time).replace(
            tzinfo=ZoneInfo("Europe/Paris")
        )
        return current

    def _insert_weather(self, weather: dict) -> bool:
        """Insère une mesure météo, retourne True si insérée (False si doublon)."""
        conn = self._get_conn()
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO bronze.meteo_paris (
                    measured_at, temperature_2m, relative_humidity_2m,
                    apparent_temperature, is_day, precipitation,
                    rain, showers, snowfall, cloud_cover, wind_speed_10m
                ) VALUES (
                    %(time)s, %(temperature_2m)s, %(relative_humidity_2m)s,
                    %(apparent_temperature)s, %(is_day)s, %(precipitation)s,
                    %(rain)s, %(showers)s, %(snowfall)s, %(cloud_cover)s, %(wind_speed_10m)s
                )
                
                ON CONFLICT ON CONSTRAINT uq_meteo_measured_at DO NOTHING
                """,
                weather,
            )
            inserted = cur.rowcount > 0
        conn.commit()
        return inserted
