import logging

from fetchers.meteo_fetcher import MeteoFetcher

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    MeteoFetcher().run()