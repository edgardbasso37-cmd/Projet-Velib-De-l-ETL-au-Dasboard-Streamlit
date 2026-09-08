import logging
import sys
from datetime import datetime
import os
from zoneinfo import ZoneInfo

from airflow.utils.email import send_email
from airflow.decorators import dag
from airflow.operators.bash import BashOperator
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

PARIS_TZ = ZoneInfo("Europe/Paris")

def _fm_date(dt):
    return dt.astimezone(PARIS_TZ).strftime("%d/%m/%Y à %H:%M:%S")

def _fetch_velib():
    sys.path.insert(0, "/opt/ingestion")
    from fetchers.velib_fetcher import VelibFetcher
    VelibFetcher().run()
    
def _fetch_meteo():
    sys.path.insert(0, "/opt/ingestion")
    from fetchers.meteo_fetcher import MeteoFetcher
    MeteoFetcher().run()

def _on_failure(context: dict):
    alert_email = os.getenv("AIRFLOW_ALERT_EMAIL")
    if not alert_email:
        return
    
    dag_id = context["dag"].dag_id
    run_id = context["run_id"]
    periode = _fm_date(context["execution_date"])
    exception = context.get("exception", "inconnue")
    send_email(
        to=[alert_email],
        subject=f"Alerte sur la pipeline Airflow - {dag_id}",
        html_content=f"""
        <h1> Alerte sur le DAG - {run_id}, {exception} </h1>
        """
    )

@dag(
    dag_id="velib_pipeline",
    description="Ingestion, transformation pour le projet Vélib",
    schedule="*/15 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    max_active_runs=1,
    tags=["Vélib", "Ingestion"],
    on_failure_callback=_on_failure
)
def dag_airflow():
    fetch_velib = PythonOperator(
        task_id="fetch_velib",
        python_callable=_fetch_velib,
    )
    
    fetch_meteo = PythonOperator(
        task_id="fetch_meteo",
        python_callable=_fetch_meteo,
    )
    
    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command=(
            "/opt/dbt-venv/bin/dbt run --profiles-dir /opt/dbt --project-dir /opt/dbt"
        ) 
    )
    
    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command=(
            "/opt/dbt-venv/bin/dbt test --profiles-dir /opt/dbt --project-dir /opt/dbt"
        ) 
    )
    
    [fetch_velib, fetch_meteo] >> dbt_run >> dbt_test

dag_airflow()