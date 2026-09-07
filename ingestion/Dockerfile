FROM debian:bookworm-slim

WORKDIR /app

# Certificats requis par uv pour les téléchargements HTTPS
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# On épingle la version d'uv pour des builds reproductibles
COPY --from=ghcr.io/astral-sh/uv:0.11.3 /uv /uvx /bin/

# Configuration uv
ENV UV_NO_DEV=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_PYTHON_DOWNLOADS=auto

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project --no-dev

COPY . .
RUN uv sync --frozen --no-dev
# On lance le fichier main.py

CMD [ "uv","run","main.py" ]