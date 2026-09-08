FROM apache/airflow:2.10.4-python3.12

USER root
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates \
    && rm -rf /var/lib/apt/lists/*

RUN mkdir -p /opt/dbt-venv /opt/ingestion /opt/dbt /opt/airflow-extras \
    && chown -R airflow:root /opt/dbt-venv /opt/ingestion /opt/dbt /opt/airflow-extras

USER airflow

# PYTHONPATH garantit que les packages sont visibles par tous les tasks Airflow,
# même si PYTHONNOUSERSITE est actif dans le sous-process du scheduler.
ENV PYTHONPATH=/opt/airflow-extras

# Dépendances supplémentaires pour les fetchers (httpx, psycopg2).
# --target installe dans un dossier explicite plutôt que dans le user site,
# ce qui évite toute ambiguïté sur le chemin calculé par pip.
COPY --chown=airflow:root airflow/requirements.txt ./
RUN pip install --no-cache-dir --target /opt/airflow-extras -r requirements.txt

# Venv isolé pour dbt-postgres (évite les conflits de dépendances avec Airflow).
# dbt est épinglé à ==1.9.0 pour correspondre exactement à la version du projet dbt.
RUN python -m venv /opt/dbt-venv \
    && /opt/dbt-venv/bin/pip install --no-cache-dir dbt-postgres==1.9.0

# Code source des fetchers (importé par PythonOperator dans le DAG)
COPY --chown=airflow:root ingestion/ /opt/ingestion/

# Projet dbt complet (modèles, macros, profiles.yml, dbt_project.yml)
COPY --chown=airflow:root dbt/ /opt/dbt/

# DAGs
COPY --chown=airflow:root airflow/dags/ ${AIRFLOW_HOME}/dags/

# Script d'initialisation de la base de métadonnées Airflow
COPY --chown=airflow:root airflow/init_db.py /opt/airflow/init_db.py