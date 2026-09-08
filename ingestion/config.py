from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str
    postgres_password: str
    postgres_db: str
    
    velib_api_base_url: str = ("https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/velib-disponibilite-en-temps-reel/records")
    velib_api_page_size: int = 100
    meteo_api_url: str = ("https://api.open-meteo.com/v1/forecast?latitude=48.8534&longitude=2.3488&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,rain,showers,snowfall,cloud_cover,wind_speed_10m&timezone=Europe%2FParis&forecast_days=1")
    #fetch_interval_minutes:int =10 plus besoin 
    
settings = Settings()