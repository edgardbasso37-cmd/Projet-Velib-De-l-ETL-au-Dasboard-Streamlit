FROM debian:bookworm-slim

WORKDIR /app

# Certificats requis par uv pour les téléchargements HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Version épinglée pour des builds reproductibles (jamais "latest")
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

# Configuration uv
ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=auto

# Variables Streamlit
ENV STREAMLIT_SERVER_PORT=8501
ENV STREAMLIT_SERVER_ADDRESS=0.0.0.0

# Installation des dépendances (lock file commité pour des builds reproductibles)
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

# Copie du code source
COPY . .

RUN chmod +x start.sh

# FastAPI (8000) + Streamlit (8501)
EXPOSE 8000 8501

CMD ["./start.sh"]