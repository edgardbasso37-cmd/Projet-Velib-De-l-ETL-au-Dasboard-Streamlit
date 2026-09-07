import logging
import signal
import sys
from datetime import datetime

from apscheduler.schedulers.blocking import BlockingScheduler

from config import settings
from fetchers.meteo_fetcher import MeteoFetcher
from fetchers.velib_fetcher import VelibFetcher

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S",
)
logger = logging.getLogger(__name__)

def main():
    velib_fetcher = VelibFetcher()
    meteo_fetcher = MeteoFetcher()
    scheduler = BlockingScheduler(timezone="Europe/Paris")

    scheduler.add_job(
        velib_fetcher.run,
        trigger="interval",
        minutes=settings.fetch_interval_minutes,
        next_run_time=datetime.now(),
        id="velib_fetcher",
        name="Vélib fetcher",
        max_instances=1,
        misfire_grace_time=60
    )

    scheduler.add_job(
        meteo_fetcher.run,
        trigger="interval",
        minutes=settings.fetch_interval_minutes,
        next_run_time=datetime.now(),
        id="meteo_fetcher",
        name="Météo fetcher",
        max_instances=1,
        misfire_grace_time=60
    )

    def _shutdown(signum: int, _frame: object):
        logger.info("Signal reçu, arrêt en cours ...")
        scheduler.shutdown(wait=False)
        sys.exit(0)
    signal.signal(signal.SIGTERM, _shutdown)
    signal.signal(signal.SIGINT, _shutdown)

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Arrêt du scheduler")

if __name__== "__main__":
       main()

