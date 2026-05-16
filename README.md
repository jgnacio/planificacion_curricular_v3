# Facilitador Docente EBI — planificacion_curricular_v3

Backend Python del Facilitador Docente EBI: herramienta de planificación curricular para docentes de Educación Básica Integrada (EBI/ANEP, Uruguay). Genera planificaciones semanales asistidas por IA, consulta el currículo oficial y gestiona alumnos.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│              facilitador_docente (Next.js 16)                │
│  Puerto 3000 — UI web (Clerk auth, HeroUI, dark mode)       │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP / SSE
            ┌──────────▼──────────┐
            │  FastAPI REST API    │
            │  api/main.py        │
            │  Puerto 8001        │
            │                     │
            │  ┌───────────────┐  │
            │  │  ADK Runner   │  │  ← embebido en el proceso FastAPI
            │  │  (dev local)  │  │    InMemorySessionService
            │  │               │  │    teacher_agent/agent.py
            │  └───────┬───────┘  │
            └──────────┼──────────┘
                       │
          ┌────────────┼────────────────────┐
          │            │                    │
  curriculum_          │              SQLite (ebi.db)
  structure.json       │              alumnos + planificaciones
  (JSON, 636KB)        │
                  ┌────▼──────────┐
                  │  Open Notebook │  ← opcional: RAG sobre PDFs ANEP
                  │  Puerto 5055   │    (docker compose)
                  └───────────────┘
```

### Dev vs Prod

| Modo | Switch | Comportamiento |
|------|--------|----------------|
| Dev | `AGENT_ENGINE_RESOURCE_NAME` vacío | ADK Runner local con `InMemorySessionService` embebido en FastAPI |
| Prod | `AGENT_ENGINE_RESOURCE_NAME=projects/...` | Vertex AI Agent Engine (sesiones persistentes en cloud) |

En prod el Dockerfile despliega en Cloud Run (puerto 8080) y el agente se delega a Agent Engine. En dev todo corre en un solo proceso `uvicorn`.

---

## Estructura del repositorio

```
planificacion_curricular_v3/
│
├── api/                           # FastAPI REST — puerto 8001
│   ├── main.py                    # App unificada: agente + datos + curriculum
│   ├── main_agent.py              # App solo-agente (para deploy agente separado)
│   ├── main_data.py               # App solo-datos (curriculum + planificaciones + alumnos)
│   ├── auth.py                    # Clerk JWT + X-Internal-Key auth dependency
│   ├── database.py                # SQLAlchemy engine + SessionLocal (SQLite)
│   ├── models/                    # ORM models (Alumno, Planificacion)
│   ├── schemas/                   # Pydantic schemas para request/response
│   └── routes/
│       ├── curriculum.py          # GET /curriculum/estructura
│       ├── planificaciones.py     # CRUD planificaciones
│       ├── alumnos.py             # CRUD alumnos
│       └── agente.py              # POST /agente/chat  +  POST /agente/chat/stream (SSE)
│
├── teacher_agent/                 # Agente ADK (Google Agent Development Kit)
│   ├── agent.py                   # root_agent con tools, response schema, prompt
│   └── requirements.txt
│
├── curriculum_extractor/          # Pipeline ADK para extraer currículo de PDFs → JSON
│   ├── agent/
│   │   ├── extractor_agent.py     # ADK agent para parsear tablas PDF
│   │   └── tools.py
│   ├── pdf_reader.py              # Extrae tablas crudas de los PDFs ANEP
│   ├── mcn_extractor.py           # Extrae competencias MCN
│   ├── section_finder.py          # Ubica secciones dentro del PDF
│   ├── merger.py                  # Combina resultados del agente + determinístico
│   ├── schemas.py                 # Pydantic schemas del extractor
│   └── run.py                     # Entrypoint: python -m curriculum_extractor
│
├── data/
│   └── curriculum_structure.json  # Currículo EBI parseado (636KB, fuente de verdad)
│
├── scripts/
│   ├── extract_curriculum_structure.py   # Parser determinístico PDF → JSON
│   ├── fix_mcn_competencias.py           # Patch MCN en el JSON
│   ├── migrate_add_user_id.py            # Migración SQLite
│   ├── deploy_cloudrun.sh                # Deploy FastAPI a Cloud Run
│   ├── deploy_agente_cloudrun.sh         # Deploy Agent Engine a Vertex AI
│   ├── update_cloudrun_env.sh            # Actualizar env vars en Cloud Run
│   └── gcloud-wrapper.sh                 # Wrapper gcloud para Open Notebook en Docker
│
├── marketing/posts/               # Posts para redes sociales (LinkedIn, Threads)
│
├── ebi.db                         # SQLite — alumnos y planificaciones
├── Dockerfile                     # Cloud Run: expone puerto 8080, copia api/ + teacher_agent/ + data/
├── pyproject.toml                 # Proyecto uv
├── uv.lock                        # Lockfile uv
├── requirements.txt               # Deps curriculum_extractor (PyMuPDF, pdfplumber…)
├── requirements-extractor.txt     # Deps extractor con ADK
├── start_all.sh                   # Levanta FastAPI (uv run uvicorn api.main:app)
├── start_adk.sh                   # Solo ADK server (dev alternativo)
└── start_api.sh                   # Solo FastAPI data API
```

---

## Tools del agente (`teacher_agent/agent.py`)

| Tool | Descripción |
|------|-------------|
| `consultar_curriculo_estructurado` | Datos estructurados desde `data/curriculum_structure.json`: CEs, contenidos, criterios de logro. Siempre se llama primero. |
| `consultar_curriculo_oficial` | RAG sobre PDFs ANEP via Open Notebook (orientaciones pedagógicas). Servicio opcional. |
| `listar_alumnos` | Lista alumnos del grupo (filtra por nivel/grado) via HTTP interno |
| `listar_planificaciones` | Lista planificaciones guardadas via HTTP interno |
| `crear_planificacion` | Guarda nueva planificación en SQLite |
| `actualizar_planificacion` | Actualiza campos de una planificación existente |
| `eliminar_planificacion` | Elimina una planificación por ID |
| `buscar_en_internet` | DuckDuckGo: extrae contenido real de hasta 5 páginas web |

El agente usa `output_schema=FacilitadorResponse` — toda respuesta es JSON con campos `type`, `text`, `curriculum_match`, `planificacion`, `secuencia` y `refs`.

---

## Endpoints de la API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/curriculum/estructura` | Currículo completo como JSON |
| `GET` | `/planificaciones/` | Listar planificaciones del usuario |
| `POST` | `/planificaciones/` | Crear planificación |
| `GET` | `/planificaciones/{id}` | Obtener planificación |
| `PUT` | `/planificaciones/{id}` | Actualizar planificación |
| `DELETE` | `/planificaciones/{id}` | Eliminar planificación |
| `GET` | `/alumnos/` | Listar alumnos del usuario |
| `POST` | `/alumnos/` | Crear alumno |
| `PUT` | `/alumnos/{id}` | Actualizar alumno |
| `DELETE` | `/alumnos/{id}` | Eliminar alumno |
| `POST` | `/agente/chat` | Chat con el agente (respuesta única JSON) |
| `POST` | `/agente/chat/stream` | Chat con el agente via SSE (tool labels + tokens + done) |
| `GET` | `/pdfs/{filename}` | Servir PDFs del currículo oficial como estáticos |

### Autenticación

Todos los endpoints (excepto `/health`) requieren una de estas dos formas:

- **JWT Clerk** — `Authorization: Bearer <token>`: extrae el `sub` como `user_id`
- **X-Internal-Key** — header `X-Internal-Key: <secret>` + query param `?user_id=...`: para llamadas internas del agente a su propia API

---

## Setup y ejecución

### Prerequisitos

- Python 3.11+ y [`uv`](https://docs.astral.sh/uv/)
- Node.js 20+ y pnpm (para el frontend)
- Docker (opcional, para Open Notebook)
- Cuenta Google Cloud con Vertex AI habilitado (o API Key de AI Studio para dev)

### Variables de entorno (`.env`)

```env
# ── Agente IA ──────────────────────────────────────
GOOGLE_API_KEY=...                        # Dev (AI Studio)
GOOGLE_GENAI_USE_VERTEXAI=0               # 1 para usar Vertex AI
GOOGLE_CLOUD_PROJECT=...                  # Requerido si USE_VERTEXAI=1
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

# ── Prod: Vertex AI Agent Engine ───────────────────
AGENT_ENGINE_RESOURCE_NAME=              # Vacío = dev local; set = Agent Engine en prod
```

### Instalación

```bash
# Backend Python (uv)
uv sync

# Open Notebook (opcional — para RAG sobre PDFs)
# docker compose -f open-notebook-docker-compose.yml up -d
```

### Ejecutar en desarrollo

```bash
# Backend — un solo proceso FastAPI en puerto 8001
./start_all.sh

# Frontend (otra terminal, en facilitador_docente/)
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

## Deploy (Cloud Run)

```bash
# FastAPI + agente embebido
bash scripts/deploy_cloudrun.sh

# Agente en Vertex AI Agent Engine (prod escalable)
bash scripts/deploy_agente_cloudrun.sh
```

El `Dockerfile` copia `api/`, `teacher_agent/` y `data/` al contenedor y expone el puerto 8080.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Backend | FastAPI, SQLAlchemy, SQLite |
| Agente IA | Google ADK, Gemini (`gemini-3.1-pro-preview`) |
| Auth | Clerk JWKS + JWT RS256 |
| RAG (opcional) | Open Notebook + SurrealDB |
| Currículo | Pipeline ADK + parser determinístico sobre PDFs ANEP |
| Package manager | uv |
| Deploy | Docker + Cloud Run (Google Cloud) |
| Frontend | Next.js 16 — ver `facilitador_docente/` |
