# Facilitador Docente EBI — planificacion_curricular_v3

Backend Python del Facilitador Docente EBI: herramienta de planificación curricular para docentes de Educación Básica Integrada (EBI/ANEP, Uruguay). Genera planificaciones semanales asistidas por IA, consulta el currículo oficial y gestiona alumnos.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              facilitador_docente (Next.js)                   │
│  UI web — Clerk auth, HeroUI                                │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / SSE
            ┌──────────▼──────────────────────┐
            │  facilitador-api (Cloud Run)     │
            │  api/main.py — Puerto 8080       │
            │                                  │
            │  • REST: alumnos, curriculum,    │
            │    planificaciones, grupos,       │
            │    secuencias, actividades,       │
            │    suscripciones, billing         │
            │  • SSE: /agente/chat/stream       │
            └──────┬─────────────┬─────────────┘
                   │             │
     ┌─────────────▼──┐   ┌──────▼────────────────────────┐
     │  Supabase/      │   │  Vertex AI Agent Platform      │
     │  SQLite (ebi.db)│   │  teacher_agent/ (ADK)          │
     │  alumnos +      │   │  deploy via deploy_agent.py    │
     │  planificaciones│   │  Sesiones persistentes         │
     └─────────────────┘   └──────────────┬────────────────┘
                                          │
                                   ┌──────▼────────┐
                                   │  Open Notebook │  ← opcional: RAG sobre PDFs ANEP
                                   └───────────────┘
```

### Dev vs Prod

| Modo | Switch | Comportamiento |
|------|--------|----------------|
| Dev | `AGENT_ENGINE_RESOURCE_NAME` vacío | ADK Runner local con `InMemorySessionService` embebido en FastAPI |
| Prod | `AGENT_ENGINE_RESOURCE_NAME=projects/...` | Vertex AI Agent Platform (sesiones persistentes en cloud) |

---

## Estructura del repositorio

```
planificacion_curricular_v3/
│
├── api/                           # FastAPI — puerto 8080 en prod (8001 en dev)
│   ├── main.py                    # Entrypoint único: todos los routers
│   ├── auth.py                    # Clerk JWT + X-Internal-Key auth dependency
│   ├── database.py                # SQLAlchemy engine + SessionLocal
│   ├── models/                    # ORM models (Alumno, Actividad, Grupo, etc.)
│   ├── schemas/                   # Pydantic schemas para request/response
│   └── routes/
│       ├── curriculum.py          # GET /curriculum/estructura
│       ├── alumnos.py             # CRUD alumnos
│       ├── students.py            # CRUD students (v2)
│       ├── groups.py              # CRUD grupos
│       ├── sequences.py           # CRUD secuencias de actividades
│       ├── activities.py          # CRUD actividades
│       ├── agente.py              # POST /agente/chat/stream (SSE → Agent Platform)
│       ├── agente_sessions.py     # GET/DELETE /agente/sessions (chat history)
│       ├── institutions.py        # Gestión de instituciones
│       ├── billing.py             # Facturación
│       ├── subscriptions.py       # Suscripciones individuales (MercadoPago)
│       ├── webhooks.py            # Webhooks MercadoPago
│       └── educational_centers.py # Centros educativos
│
├── teacher_agent/                 # Agente ADK (Google Agent Development Kit)
│   └── agent.py                   # root_agent — tools, output_schema, prompt
│
├── curriculum_extractor/          # Pipeline ADK para extraer currículo de PDFs → JSON
│
├── data/
│   └── curriculum_structure.json  # Currículo EBI parseado (636KB, fuente de verdad)
│
├── scripts/
│   ├── deploy_cloudrun.sh         # Deploy facilitador-api a Cloud Run
│   ├── update_cloudrun_env.sh     # Actualizar env vars en Cloud Run
│   ├── extract_curriculum_structure.py
│   ├── fix_mcn_competencias.py
│   ├── migrate_add_user_id.py
│   ├── migrate_supabase.sh
│   ├── seed_dev.py
│   └── gcloud-wrapper.sh
│
├── deploy_agent.py                # Deploy/update teacher_agent a Vertex AI Agent Platform
│
├── ebi.db                         # SQLite — datos locales (dev)
├── Dockerfile                     # Cloud Run: expone puerto 8080
├── pyproject.toml                 # Proyecto uv
└── uv.lock                        # Lockfile uv
```

---

## Tools del agente (`teacher_agent/agent.py`)

| Tool | Descripción |
|------|-------------|
| `consultar_curriculo_estructurado` | Datos estructurados desde `data/curriculum_structure.json`: CEs, contenidos, criterios de logro. Siempre se llama primero. |
| `consultar_curriculo_oficial` | RAG sobre PDFs ANEP via Open Notebook (orientaciones pedagógicas). Servicio opcional. |
| `listar_alumnos` | Lista alumnos del grupo via HTTP interno |
| `list_groups` | Lista grupos del usuario |
| `list_projects` | Lista proyectos integradores de un grupo |
| `create_sequence` | Crea una secuencia de actividades dentro de un proyecto |
| `create_activity` | Guarda una actividad en la base de datos |
| `update_activity` | Actualiza una actividad existente |
| `delete_activity` | Elimina una actividad |
| `list_activities` | Lista actividades de un proyecto o secuencia |
| `buscar_en_internet` | DuckDuckGo: extrae contenido real de hasta 5 páginas web |

El agente usa `output_schema=FacilitadorResponse` — toda respuesta es JSON con campos `type`, `text`, `curriculum_match`, `planificacion`, `secuencia` y `refs`.

---

## Endpoints de la API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/curriculum/estructura` | Currículo completo como JSON |
| `GET` | `/alumnos/` | Listar alumnos del usuario |
| `POST` | `/alumnos/` | Crear alumno |
| `PUT` | `/alumnos/{id}` | Actualizar alumno |
| `DELETE` | `/alumnos/{id}` | Eliminar alumno |
| `GET/POST` | `/groups/` | Grupos del usuario |
| `GET/POST` | `/sequences/` | Secuencias de actividades |
| `GET/POST/PUT/DELETE` | `/activities/` | Actividades |
| `POST` | `/agente/chat/stream` | Chat con el agente via SSE |
| `GET` | `/agente/sessions/` | Historial de sesiones de chat |
| `DELETE` | `/agente/sessions/{id}` | Eliminar sesión de chat |
| `GET` | `/pdfs/{filename}` | Servir PDFs del currículo oficial |

### Autenticación

Todos los endpoints (excepto `/health`) requieren una de estas dos formas:

- **JWT Clerk** — `Authorization: Bearer <token>`: extrae el `sub` como `user_id`
- **X-Internal-Key** — header `X-Internal-Key: <secret>` + query param `?user_id=...`: para llamadas internas del agente a su propia API

---

## Setup y ejecución

### Prerequisitos

- Python 3.11+ y [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ y pnpm (para el frontend en `../facilitador_docente/`)
- Docker (opcional, para Open Notebook)
- Cuenta Google Cloud con Vertex AI habilitado (o API Key de AI Studio para dev)

### Variables de entorno (`.env`)

```env
# ── Agente IA ──────────────────────────────────────
GOOGLE_API_KEY=...                        # Dev (AI Studio)
GOOGLE_CLOUD_PROJECT=...                  # Proyecto GCP
GOOGLE_CLOUD_LOCATION=us-central1

# ── API interna ────────────────────────────────────
INTERNAL_API_URL=http://localhost:8001    # URL que usa el agente para llamarse a sí mismo
INTERNAL_API_KEY=...                      # Clave compartida para auth interna

# ── Auth Clerk ─────────────────────────────────────
CLERK_JWKS_URL=https://<clerk-domain>/.well-known/jwks.json

# ── Open Notebook (opcional) ───────────────────────
OPEN_NOTEBOOK_URL=http://localhost:5055
OPEN_NOTEBOOK_API_KEY=...
OPEN_NOTEBOOK_NOTEBOOK_ID=notebook:...
OPEN_NOTEBOOK_MODEL=model:...

# ── Prod: Vertex AI Agent Platform ─────────────────
AGENT_ENGINE_RESOURCE_NAME=              # Vacío = dev local; set = Agent Platform en prod
```

### Instalación

```bash
uv sync
```

### Ejecutar en desarrollo

```bash
# Backend — FastAPI en puerto 8001
./start.sh

# Frontend (otra terminal, en ../facilitador_docente/)
pnpm install && pnpm dev
```

---

## Currículo EBI

`data/curriculum_structure.json` es generado por el pipeline de extracción:

```bash
# Opción A — Parser determinístico (regex/string sobre PDFs)
python scripts/extract_curriculum_structure.py

# Opción B — Pipeline ADK (más preciso para tablas complejas)
python -m curriculum_extractor
```

Jerarquía extraída: **Tramos → Espacios → Materias → Competencias Específicas (CEs) → Contenidos (por grado) → Criterios de logro (por grado)**

El agente lee este archivo directamente en memoria con `consultar_curriculo_estructurado`. Solo cubre 2do ciclo (Tramo 3: 3° y 4°; Tramo 4: 5° y 6°).

---

## Deploy

### API (Cloud Run)

```bash
bash scripts/deploy_cloudrun.sh
```

Despliega `facilitador-api` a Cloud Run usando `api/main.py`. Requiere `AGENT_ENGINE_RESOURCE_NAME` en `.env` para que el agente apunte al Agent Platform correcto.

### Agente (Vertex AI Agent Platform)

```bash
uv run python deploy_agent.py
```

- Si `AGENT_ENGINE_RESOURCE_NAME` está en `.env` → **actualiza** el engine existente (sesiones preservadas)
- Si no está → **crea** un engine nuevo e imprime el resource name para agregar al `.env`

El engine activo: `projects/81545989837/locations/us-central1/reasoningEngines/8214550876916809728`

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI, SQLAlchemy, SQLite / Supabase |
| Agente IA | Google ADK, Gemini (`gemini-3.5-flash`) |
| Agent Platform | Vertex AI Agent Platform (Reasoning Engine) |
| Auth | Clerk JWKS + JWT RS256 |
| RAG (opcional) | Open Notebook + SurrealDB |
| Currículo | Pipeline ADK + parser determinístico sobre PDFs ANEP |
| Package manager | uv |
| Deploy | Docker + Cloud Run (API) + Vertex AI Agent Platform (agente) |
| Frontend | Next.js — ver `../facilitador_docente/` |
