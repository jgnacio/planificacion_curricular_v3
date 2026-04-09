FROM python:3.11-slim

WORKDIR /app

# System deps for PyMuPDF and other native packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt requirements.txt
COPY api/requirements.txt api_requirements.txt
RUN pip install --no-cache-dir -r requirements.txt -r api_requirements.txt \
    google-adk httpx pydantic duckduckgo-search beautifulsoup4

# Copy application source
COPY api/ api/
COPY teacher_agent/ teacher_agent/
COPY data/ data/

# PDFs are optional — mount via volume in production
RUN mkdir -p pdfs

EXPOSE 8001

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8001"]
