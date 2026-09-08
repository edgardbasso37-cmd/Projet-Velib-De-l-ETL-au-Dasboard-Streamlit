import os
import psycopg2

conn = psycopg2.connect(
    host=os.environ["POSTGRES_HOST"],
    port=int(os.environ.get("POSTGRES_PORT", 5432)),
    user=os.environ["POSTGRES_USER"],
    password=os.environ["POSTGRES_PASSWORD"],
    dbname="postgres"
)

conn.autocommit = True
cur = conn.cursor()

db_name = os.environ["AIRFLOW_DB_NAME"]
cur.execute(f"SELECT 1 FROM pg_database WHERE datname = %s", (db_name, ))
if not cur.fetchone():
    cur.execute(f'CREATE DATABASE "{db_name}"')
    print("OK")
else:
    print("pas ok")

conn.close()