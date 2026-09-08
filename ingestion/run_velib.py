import logging

from fetchers.velib_fetcher import VelibFetcher

logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    VelibFetcher().run()