FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Instalar uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Copiar lockfile y pyproject primero (cache layer)
COPY pyproject.toml uv.lock ./

# Instalar deps desde el lockfile
RUN uv sync --frozen --no-install-project --no-dev

# Application source
COPY api/ api/
COPY teacher_agent/ teacher_agent/
COPY data/ data/

RUN mkdir -p pdfs

EXPOSE 8080

ENV APP_MODULE=api.main:app

CMD ["/bin/sh", "-c", ".venv/bin/uvicorn ${APP_MODULE} --host 0.0.0.0 --port 8080"]
