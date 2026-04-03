# Facilitador Docente EBI — planificacion_curricular_v3

Herramienta de planificación curricular para docentes de Educación Básica Integrada (EBI/ANEP, Uruguay). Permite generar planificaciones semanales asistidas por IA, consultar el currículo oficial y gestionar alumnos.

---

## Arquitectura

```
┌─────────────────────────────────────────────────────────┐
│              facilitador_docente (Next.js 16)            │
│  Puerto 3000 — UI web (Clerk auth, HeroUI, dark mode)   │
└──────────────────────┬──────────────────────────────────┘
                       │ HTTP
         ┌─────────────┴──────────────┐
         │                            │
┌────────▼────────┐        ┌──────────▼──────────┐
│   ADK server    │        │   FastAPI REST API   │
│   Puerto 8000   │        │    Puerto 8001        │
│  teacher_agent/ │        │       api/            │
└────────┬────────┘        └──────────┬────────────┘
         │                            │
         │ RAG (HTTP)          SQLite (ebi.db)
         │
┌────────▼────────────────────────────┐
│         Open Notebook               │
│  Puerto 8502 — RAG sobre PDFs       │
│  Puerto 5055 — REST API             │
│  + SurrealDB (puerto 8000 interno)  │
└─────────────────────────────────────┘
```

### Flujo de datos

1. El docente interactúa con el **frontend Next.js**
2. El chat va al **ADK server** (`teacher_agent/agent.py`)
3. El agente consulta:
   - **Open Notebook** (RAG sobre PDFs del currículo oficial) via `consultar_curriculo_oficial`
   - **curriculum_structure.json** (parser determinístico) via `consultar_curriculo_estructurado`
   - **SQLite** (alumnos y planificaciones propias del docente)
   - **DuckDuckGo** para búsquedas en internet
4. La API REST (`api/`) sirve datos de alumnos, planificaciones y la estructura del currículo al frontend

---

## Estructura del repositorio

```
planificacion_curricular_v3/
│
├── api/                          # FastAPI REST — puerto 8001
│   ├── main.py                   # App entry point, middleware, router registration
│   ├── database.py               # SQLAlchemy engine + SessionLocal (SQLite)
│   ├── models/                   # ORM models (Alumno, Planificacion)
│   ├── schemas/                  # Pydantic schemas para request/response
│   └── routes/
│       ├── curriculum.py         # GET /curriculum/estructura (curriculum_structure.json)
│       ├── planificaciones.py    # CRUD planificaciones
│       ├── alumnos.py            # CRUD alumnos
│       └── agente.py             # POST /agente/chat (ADK runner interno)
│
├── teacher_agent/                # Agente ADK (Google Agent Development Kit)
│   ├── agent.py                  # root_agent con todas las tools
│   └── __init__.py
│
├── facilitador_docente/          # Frontend Next.js 16 (App Router)
│   ├── app/
│   │   ├── page.tsx              # Página principal
│   │   ├── layout.tsx            # Layout con Clerk auth
│   │   ├── providers.tsx         # HeroUIProvider + NextThemesProvider (dark mode)
│   │   ├── api-actions.ts        # Server actions — todas las llamadas HTTP al backend
│   │   └── components/
│   │       ├── AppShell.tsx      # Shell con navegación por tabs
│   │       └── tabs/
│   │           ├── AsistenteTab.tsx      # Chat con el agente
│   │           ├── PlanificacionesTab.tsx # Lista y gestión de planificaciones
│   │           ├── ProgramaTab.tsx        # Explorador del currículo estructurado
│   │           ├── AlumnosTab.tsx         # Gestión de alumnos
│   │           └── DashboardTab.tsx       # Dashboard principal
│   ├── lib/utils.ts              # Utilidades (cn, etc.)
│   └── proxy.ts                  # Middleware Clerk auth
│
├── data/
│   └── curriculum_structure.json # Currículo EBI parseado (636KB, fuente de verdad)
│
├── pdfs/                         # PDFs fuente del currículo oficial ANEP
│   ├── Compilación Programas 1er Ciclo - 2024.pdf
│   └── Compilación Programas 2do Ciclo.pdf
│
├── scripts/
│   ├── extract_curriculum_structure.py  # Parser determinístico PDF → curriculum_structure.json
│   └── gcloud-wrapper.sh                # Wrapper gcloud para Open Notebook en Docker
│
├── marketing/posts/              # Posts para redes sociales (LinkedIn, Threads)
├── mobile_app/                   # App Flutter (fase 2 — no activa)
│
├── ebi.db                        # SQLite — alumnos y planificaciones
├── requirements.txt              # Dependencias Python del backend
├── open-notebook-docker-compose.yml  # Docker: Open Notebook + SurrealDB
├── start_all.sh                  # Levanta ADK server + FastAPI en paralelo
├── start_adk.sh                  # Solo ADK server
└── start_api.sh                  # Solo FastAPI
```

---

## Tools del agente (`teacher_agent/agent.py`)

| Tool | Descripción |
|------|-------------|
| `listar_alumnos` | Lista alumnos del grupo, filtra por nivel/grado |
| `listar_planificaciones` | Lista planificaciones guardadas |
| `crear_planificacion` | Crea una planificación nueva en SQLite |
| `actualizar_planificacion` | Actualiza nombre/descripción de una planificación |
| `eliminar_planificacion` | Elimina una planificación |
| `consultar_curriculo_oficial` | RAG sobre PDFs via Open Notebook (orientaciones pedagógicas) |
| `consultar_curriculo_estructurado` | Datos estructurados: CEs, contenidos, criterios desde JSON |
| `buscar_en_internet` | Búsqueda DuckDuckGo para recursos externos |

---

## Endpoints de la API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/health` | Health check |
| `GET` | `/curriculum/estructura` | Currículo completo como JSON |
| `GET` | `/planificaciones/` | Listar planificaciones |
| `POST` | `/planificaciones/` | Crear planificación |
| `GET` | `/planificaciones/{id}` | Obtener planificación |
| `DELETE` | `/planificaciones/{id}` | Eliminar planificación |
| `GET` | `/alumnos/` | Listar alumnos |
| `POST` | `/alumnos/` | Crear alumno |
| `POST` | `/agente/chat` | Chat directo con el agente (alternativa al ADK server) |
| `GET` | `/pdfs/{filename}` | Servir PDFs como archivos estáticos |

---

## Setup y ejecución

### Prerequisitos

- Python 3.11+
- Node.js 20+ y pnpm
- Docker (para Open Notebook + SurrealDB)
- Cuenta Google Cloud con Vertex AI habilitado

### Variables de entorno (`.env`)

```env
GOOGLE_API_KEY=...
GOOGLE_GENAI_USE_VERTEXAI=1
GOOGLE_CLOUD_PROJECT=...
APP_ENV=dev
```

### Frontend (`facilitador_docente/`)

```env
# facilitador_docente/.env.local
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=...
CLERK_SECRET_KEY=...
API_URL=http://localhost:8001
ADK_URL=http://localhost:8000
```

### Pasos de instalación

```bash
# 1. Backend Python
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
cd facilitador_docente
pnpm install

# 3. Open Notebook (Docker)
docker compose -f open-notebook-docker-compose.yml up -d
```

### Ejecutar

```bash
# Backend completo (ADK + FastAPI)
./start_all.sh

# Frontend (otra terminal)
cd facilitador_docente
pnpm dev
```

---

## Datos del currículo

`data/curriculum_structure.json` es generado por el parser determinístico:

```bash
python scripts/extract_curriculum_structure.py
```

El parser extrae la jerarquía completa desde los PDFs en `pdfs/`:
- Tramos → Espacios → Materias → Competencias Específicas (CEs) → Contenidos → Criterios de logro

Este archivo es la **fuente de verdad** para el explorador de currículo y el agente.

---

## Stack tecnológico

| Capa | Tecnología |
|------|-----------|
| Frontend | Next.js 16, HeroUI v3, Tailwind CSS v4, Clerk auth |
| Backend | FastAPI, SQLAlchemy, SQLite |
| Agente IA | Google ADK, Gemini 2.5 Flash (Vertex AI) |
| RAG | Open Notebook + SurrealDB |
| Currículo | Parser determinístico (regex/string) sobre PDFs ANEP |
| Mobile (fase 2) | Flutter |
