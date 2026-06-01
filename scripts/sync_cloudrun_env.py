"""
Compara el .env local con las variables de Cloud Run y permite sincronizarlas.

Uso: .venv/bin/python3 scripts/sync_cloudrun_env.py
"""
import json
import os
import subprocess
import sys

SERVICE = "facilitador-api"
REGION  = "us-central1"

# Colores ANSI
GREEN  = "\033[92m"
YELLOW = "\033[93m"
RED    = "\033[91m"
CYAN   = "\033[96m"
BOLD   = "\033[1m"
DIM    = "\033[2m"
RESET  = "\033[0m"

# Variables que NUNCA se suben (solo locales / gestionadas por GCP)
SKIP = {
    "GOOGLE_API_KEY",       # Solo para deploy del agente
    "GOOGLE_APPLICATION_CREDENTIALS",
}


def load_env(path=".env") -> dict[str, str]:
    env = {}
    if not os.path.exists(path):
        print(f"{RED}ERROR: No se encontró {path}{RESET}")
        sys.exit(1)
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, val = line.partition("=")
            env[key.strip()] = val.strip().strip('"').strip("'")
    return env


def load_cloudrun() -> dict[str, str]:
    result = subprocess.run(
        ["gcloud", "run", "services", "describe", SERVICE,
         f"--region={REGION}", "--format=json"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print(f"{RED}ERROR al leer Cloud Run: {result.stderr}{RESET}")
        sys.exit(1)
    data = json.loads(result.stdout)
    env_list = (
        data.get("spec", {})
            .get("template", {})
            .get("spec", {})
            .get("containers", [{}])[0]
            .get("env", [])
    )
    return {e["name"]: e.get("value", "") for e in env_list}


def mask(val: str) -> str:
    if len(val) <= 8:
        return "***"
    return val[:6] + "..." + val[-4:]


local  = load_env()
remote = load_cloudrun()

# Filtrar las que se saltean
local_filtered = {k: v for k, v in local.items() if k not in SKIP}

all_keys = sorted(set(local_filtered) | set(remote))

to_update: dict[str, str] = {}

print(f"\n{BOLD}{'Variable':<35} {'Local':<25} {'Cloud Run':<25} Estado{RESET}")
print("─" * 100)

for key in all_keys:
    local_val  = local_filtered.get(key)
    remote_val = remote.get(key)

    local_display  = mask(local_val)  if local_val  else f"{DIM}(no existe){RESET}"
    remote_display = mask(remote_val) if remote_val else f"{DIM}(no existe){RESET}"

    if local_val is None:
        # Solo en Cloud Run
        status = f"{DIM}solo en Cloud Run{RESET}"
        color  = DIM
    elif remote_val is None:
        # Nueva — solo en local
        status = f"{YELLOW}✦ nueva{RESET}"
        color  = YELLOW
        to_update[key] = local_val
    elif local_val != remote_val:
        # Diferente
        status = f"{CYAN}~ distinta{RESET}"
        color  = CYAN
        to_update[key] = local_val
    else:
        # Igual
        status = f"{GREEN}✓ igual{RESET}"
        color  = GREEN

    print(f"{color}{key:<35}{RESET} {local_display:<25} {remote_display:<25} {status}")

print("─" * 100)
print(f"\n{BOLD}Leyenda:{RESET}  {GREEN}✓ igual{RESET}   {CYAN}~ distinta (se actualizaría){RESET}   {YELLOW}✦ nueva (se agregaría){RESET}   {DIM}solo en Cloud Run (no se toca){RESET}\n")

if not to_update:
    print(f"{GREEN}✓ Cloud Run ya está sincronizado con el .env local.{RESET}")
    sys.exit(0)

print(f"{BOLD}Variables a actualizar ({len(to_update)}):{RESET} {', '.join(to_update.keys())}\n")
answer = input("¿Actualizar Cloud Run ahora? [s/N]: ").strip().lower()

if answer not in ("s", "si", "sí", "y", "yes"):
    print("Cancelado.")
    sys.exit(0)

env_str = ",".join(f"{k}={v}" for k, v in to_update.items())
result = subprocess.run(
    ["gcloud", "run", "services", "update", SERVICE,
     f"--region={REGION}", f"--update-env-vars={env_str}"],
    capture_output=True, text=True,
)

if result.returncode == 0:
    print(f"\n{GREEN}✓ Cloud Run actualizado. Nueva revisión desplegada.{RESET}")
else:
    print(f"\n{RED}ERROR: {result.stderr}{RESET}")
    sys.exit(1)
