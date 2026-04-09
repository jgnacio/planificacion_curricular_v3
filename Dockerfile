FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# API deps
COPY api/requirements.txt api/requirements.txt
RUN pip install --no-cache-dir -r api/requirements.txt

# Agent deps (not in api/requirements.txt)
RUN pip install --no-cache-dir \
    google-adk \
    google-cloud-aiplatform[agent_engines] \
    duckduckgo-search \
    beautifulsoup4

# Application source
COPY api/ api/
COPY teacher_agent/ teacher_agent/
COPY data/ data/

RUN mkdir -p pdfs

EXPOSE 8080

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
