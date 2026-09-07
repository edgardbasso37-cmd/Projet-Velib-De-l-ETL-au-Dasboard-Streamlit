#!/bin/bash
set -e

# Démarrage de FastAPI en arrière-plan
uv run uvicorn api.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# Courte attente pour laisser FastAPI s'initialiser avant que Streamlit
# ne commence à envoyer des requêtes lors du premier rendu
sleep 2

# Démarrage de Streamlit en premier plan (processus principal)
exec uv run streamlit run app/streamlit_app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true
