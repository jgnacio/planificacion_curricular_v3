"""
Deploy teacher_agent to Vertex AI Agent Platform.

Run from planificacion_curricular_v3/:
    uv run python deploy_agent.py

Comportamiento:
- Si AGENT_ENGINE_RESOURCE_NAME está en .env → ACTUALIZA ese engine (sesiones preservadas)
- Si no está → CREA un engine nuevo y muestra el resource name para guardarlo

Al crear un engine nuevo:
  1. Copiar el resource name impreso
  2. Agregar AGENT_ENGINE_RESOURCE_NAME=<resource_name> al .env
  3. Actualizar la env var en Cloud Run facilitador-api con el comando mostrado
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

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY", "")

import vertexai
from vertexai import agent_engines
from teacher_agent.agent import root_agent

PROJECT = "facilitador-docente"
LOCATION = "us-central1"
EXISTING_RESOURCE_NAME = os.getenv("AGENT_ENGINE_RESOURCE_NAME", "")

AGENT_CONFIG = {
    "staging_bucket": "gs://facilitador-docente-agent-staging",
    "display_name": "facilitador-docente-agent",
    "description": "Facilitador Docente EBI — ADK agent para planificación curricular ANEP",
    "requirements": [
        "google-adk==1.33.0",
        "google-cloud-aiplatform[agent_engines]==1.153.1",
        "cloudpickle",
        "pydantic",
        "httpx",
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
        "TAVILY_API_KEY": TAVILY_API_KEY,
        "OPEN_NOTEBOOK_URL": "https://104.154.54.205",
        "OPEN_NOTEBOOK_API_KEY": "DBvFTreFB4p9pcH5tdKOAVXusJhEPyg1g1m6KzEjcFUE1QLkRaGPh2YxWOClTVsR",
        "OPEN_NOTEBOOK_NOTEBOOK_ID": "notebook:4blvxvmp0bb4cud5r004",
        "OPEN_NOTEBOOK_MODEL": "model:7zoi10k3sca4qvqacud4",
    },
}

vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=AGENT_CONFIG["staging_bucket"])

print(f"  Project : {PROJECT}")
print(f"  Location: {LOCATION}")
print()

if EXISTING_RESOURCE_NAME:
    print(f"Updating existing agent: {EXISTING_RESOURCE_NAME}")
    print("Sessions will be preserved.")
    print()
    remote_agent = agent_engines.get(EXISTING_RESOURCE_NAME)
    remote_agent.update(
        agent_engine=root_agent,
        display_name=AGENT_CONFIG["display_name"],
        description=AGENT_CONFIG["description"],
        requirements=AGENT_CONFIG["requirements"],
        extra_packages=AGENT_CONFIG["extra_packages"],
        env_vars=AGENT_CONFIG["env_vars"],
    )
    resource_name = remote_agent.gca_resource.name
    print()
    print("Agent updated successfully!")
    print(f"  Resource name: {resource_name}")
    print()
    print("Sessions from previous deployments are preserved.")
    print("No changes needed to Cloud Run env vars.")
else:
    print("No AGENT_ENGINE_RESOURCE_NAME found — creating new agent...")
    print()
    client = vertexai.Client(project=PROJECT, location=LOCATION)
    remote_agent = client.agent_engines.create(agent=root_agent, config=AGENT_CONFIG)
    resource_name = remote_agent.gca_resource.name
    print()
    print("Agent created successfully!")
    print()
    print("Resource name:")
    print(f"  {resource_name}")
    print()
    print("Next steps:")
    print("  1. Add to .env:")
    print(f"     AGENT_ENGINE_RESOURCE_NAME={resource_name}")
    print("  2. Set in Cloud Run facilitador-api:")
    print(f"     gcloud run services update facilitador-api --region us-central1 \\")
    print(f"       --update-env-vars AGENT_ENGINE_RESOURCE_NAME={resource_name}")
    print("  3. Future deploys will update this engine — sessions preserved.")
