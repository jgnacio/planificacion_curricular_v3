"""
Actualiza las variables de entorno de Cloud Run desde el .env local.
Solo sincroniza las variables MP_* y FRONT_URL.

Uso: .venv/bin/python3 scripts/update_cloudrun_env.py
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from dotenv import load_dotenv
load_dotenv()

SERVICE = "facilitador-api"
REGION = "us-central1"

VARS_TO_SYNC = [
    "MP_ACCESS_TOKEN",
    "MP_WEBHOOK_SECRET",
    "FRONT_URL",
]

values = {}
for var in VARS_TO_SYNC:
    val = os.getenv(var)
    if val:
        values[var] = val
    else:
        print(f"  ⚠ {var} no encontrado en .env — se omite")

if not values:
    print("ERROR: Ninguna variable encontrada en .env")
    sys.exit(1)

print(f"Actualizando {SERVICE} con: {', '.join(values.keys())}")

env_str = ",".join(f"{k}={v}" for k, v in values.items())
cmd = [
    "gcloud", "run", "services", "update", SERVICE,
    f"--region={REGION}",
    f"--update-env-vars={env_str}",
]

result = subprocess.run(cmd, capture_output=True, text=True)
if result.returncode == 0:
    print("✓ Cloud Run actualizado. Nueva revisión desplegada.")
else:
    print(f"ERROR: {result.stderr}")
    sys.exit(1)
