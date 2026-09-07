"""
Fetcher Vélib : appel API Open Data Paris -> insertion bronze.velib_stations

Flux :
  API Open Data Paris -> pagination -> aplatissement geo -> PostgreSQL bronze

L'API Opendatasoft v2.1 limite la pagination par offset à ~900 records.
Paris compte ~994 stations : on récupère les 900 premières (triées par capacity DESC).
La déduplication est gérée par la contrainte uq_velib_station_update (stationcode, duedate).
"""

import logging
import time

import httpx
import psycopg2
import psycopg2.extensions

from config import settings

logger = logging.getLogger(__name__)

INTER_PAGE_DELAY_SECONDS = 0.2  # politesse envers l'API publique


class VelibFetcher:
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
        logger.info("Démarrage de la collecte Vélib…")
        try:
            stations = self._fetch_all_stations()
        except Exception:
            logger.exception("Erreur lors de la collecte Vélib")
            return

        logger.info("%d stations récupérées -> insertion en base", len(stations))
        try:
            inserted = self._insert_stations(stations)
            logger.info(
                "✓ %d nouvelles lignes insérées dans bronze.velib_stations (%d doublons ignorés)",
                inserted,
                len(stations) - inserted,
            )
        except Exception:
            logger.exception("Erreur lors de l'insertion Vélib")

    def _fetch_all_stations(self) -> list[dict]:
        stations: list[dict] = []
        offset = 0

        with httpx.Client(timeout=30.0) as client:
            while True:
                params = {
                    # stationcode en secondaire garantit un ordre stable entre pages
                    # (capacity seule peut créer des ex-aequo et rater des records)
                    "order_by": "capacity DESC, stationcode ASC",
                    "limit": settings.velib_api_page_size,
                    "offset": offset,
                    "refine": 'nom_arrondissement_communes:"Paris"',
                    "timezone": "Europe/Paris",
                }
                response = client.get(settings.velib_api_base_url, params=params)
                response.raise_for_status()
                payload = response.json()

                results: list[dict] = payload.get("results", [])
                if not results:
                    break

                for record in results:
                    # L'API renvoie les coordonnées dans un objet imbriqué.
                    # On l'aplatit pour simplifier le schéma Bronze.
                    geo = record.pop("coordonnees_geo", None) or {}
                    record["lon"] = geo.get("lon")
                    record["lat"] = geo.get("lat")
                    # Champ toujours null dans les données actuelles, on le retire
                    record.pop("station_opening_hours", None)
                    stations.append(record)

                offset += len(results)
                total: int = payload.get("total_count", 0)
                logger.debug("Page offset=%d/%d récupérée", offset, total)

                if offset >= total:
                    break

                time.sleep(INTER_PAGE_DELAY_SECONDS)

        return stations

    def _insert_stations(self, stations: list[dict]) -> int:
        """Insère les stations dans bronze.velib_stations, retourne le nombre de lignes insérées."""
        conn = self._get_conn()
        inserted = 0
        with conn.cursor() as cur:
            for station in stations:
                cur.execute(
                    """
                    INSERT INTO bronze.velib_stations (
                        stationcode, name, is_installed, capacity,
                        numdocksavailable, numbikesavailable, mechanical, ebike,
                        is_renting, is_returning, duedate, lon, lat,
                        nom_arrondissement_communes, code_insee_commune
                    ) VALUES (
                        %(stationcode)s, %(name)s, %(is_installed)s, %(capacity)s,
                        %(numdocksavailable)s, %(numbikesavailable)s, %(mechanical)s, %(ebike)s,
                        %(is_renting)s, %(is_returning)s, %(duedate)s, %(lon)s, %(lat)s,
                        %(nom_arrondissement_communes)s, %(code_insee_commune)s
                    )
                    
                    ON CONFLICT ON CONSTRAINT uq_velib_station_update DO NOTHING
                    """,
                    station,
                )
                inserted += cur.rowcount
        conn.commit()
        return inserted
