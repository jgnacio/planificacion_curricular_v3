"""
Deploy teacher_agent to Vertex AI Agent Platform.

Run from planificacion_curricular_v3/:
    uv run python deploy_agent.py

On success, copy the printed resource name to AGENT_ENGINE_RESOURCE_NAME
in the facilitador-agente Cloud Run service env vars.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Set BEFORE importing teacher_agent — avoids the ValueError on startup
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "facilitador-docente")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "us-central1")
os.environ.setdefault("INTERNAL_API_URL", "https://facilitador-api-81545989837.us-central1.run.app")
os.environ.setdefault("INTERNAL_API_KEY", "iJmM9M3VCPri2gm8pqH5w5bF1X1qipdyjAhHPz4zDJ6W2qoMzlrBfJ7sL7VoIrsT")

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY", "")
if not GOOGLE_API_KEY:
    raise ValueError("GOOGLE_API_KEY no está en .env — necesaria para el Agent Platform")

import vertexai
from teacher_agent.agent import root_agent

PROJECT = "facilitador-docente"
LOCATION = "us-central1"

vertexai.init(project=PROJECT, location=LOCATION)
client = vertexai.Client(project=PROJECT, location=LOCATION)

print("Deploying facilitador-docente agent to Agent Platform...")
print(f"  Project : {PROJECT}")
print(f"  Location: {LOCATION}")
print()

remote_agent = client.agent_engines.create(
    agent=root_agent,
    config={
        "staging_bucket": "gs://facilitador-docente-agent-staging",
        "display_name": "facilitador-docente-agent",
        "description": "Facilitador Docente EBI — ADK agent para planificación curricular ANEP",
        "requirements": [
            "google-adk==1.33.0",
            "google-cloud-aiplatform[agent_engines]==1.153.1",
            "cloudpickle",
            "pydantic",
            "httpx",
            "duckduckgo-search",
            "beautifulsoup4",
            "python-dotenv",
        ],
        "extra_packages": ["teacher_agent"],
        "agent_framework": "google-adk",
        "env_vars": {
            "GOOGLE_GENAI_USE_VERTEXAI": "1",
            # AI_STUDIO_API_KEY (no GOOGLE_API_KEY) para evitar que VertexAiSessionService
            # lo use como express_mode_api_key y rompa la gestión de sesiones.
            "AI_STUDIO_API_KEY": GOOGLE_API_KEY,
            "INTERNAL_API_URL": "https://facilitador-api-81545989837.us-central1.run.app",
            "INTERNAL_API_KEY": "iJmM9M3VCPri2gm8pqH5w5bF1X1qipdyjAhHPz4zDJ6W2qoMzlrBfJ7sL7VoIrsT",
            "OPEN_NOTEBOOK_URL": "https://104.154.54.205",
            "OPEN_NOTEBOOK_API_KEY": "DBvFTreFB4p9pcH5tdKOAVXusJhEPyg1g1m6KzEjcFUE1QLkRaGPh2YxWOClTVsR",
            "OPEN_NOTEBOOK_NOTEBOOK_ID": "notebook:4blvxvmp0bb4cud5r004",
            "OPEN_NOTEBOOK_MODEL": "model:7zoi10k3sca4qvqacud4",
        },
    },
)

print("Agent deployed successfully!")
print()
print("Resource name:")
print(f"  {remote_agent.api_resource.name}")
print()
print("Next steps:")
print("  1. Set in facilitador-agente Cloud Run:")
print(f"     AGENT_ENGINE_RESOURCE_NAME={remote_agent.api_resource.name}")
print("  2. Redeploy facilitador-agente so agente.py picks up the env var")
