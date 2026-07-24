import logging
import sys

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:%(name)s:%(message)s",
    stream=sys.stdout,
)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from api.database import Base, engine
import api.models.alumno               # noqa: F401
import api.models.planificacion        # noqa: F401
import api.models.user_profile         # noqa: F401
import api.models.institution          # noqa: F401
import api.models.billing              # noqa: F401
import api.models.educational_center   # noqa: F401
import api.models.group                # noqa: F401
import api.models.integrative_project  # noqa: F401
import api.models.activity_sequence    # noqa: F401
import api.models.activity             # noqa: F401
import api.models.chat_session         # noqa: F401
import api.models.student_report       # noqa: F401
import api.models.descripcion_fundada  # noqa: F401
from api.routes import curriculum, alumnos
from api.routes import agente
from api.routes import agente_sessions
from api.routes import access, institutions, billing, subscriptions, webhooks, educational_centers, students
from api.routes import groups, sequences, activities
from api.routes import student_reports
from api.routes import descripciones_fundadas
from api.routes import curriculo_search
from api.routes import curriculo_pdf

# Create SQLite tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="EBI Planificación Docente API",
    description="API para la app móvil del Facilitador Docente EBI/ANEP",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(curriculum.router)
app.include_router(alumnos.router)
app.include_router(agente.router)
app.include_router(agente_sessions.router)
app.include_router(access.router)
app.include_router(institutions.router)
app.include_router(billing.router)
app.include_router(subscriptions.router)
app.include_router(webhooks.router)
app.include_router(educational_centers.router)
app.include_router(students.router)
app.include_router(groups.router)
app.include_router(sequences.router)
app.include_router(activities.router)
app.include_router(student_reports.router)
app.include_router(descripciones_fundadas.router)
app.include_router(curriculo_search.router)
app.include_router(curriculo_pdf.router)


def _custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    schema.setdefault("components", {})["securitySchemes"] = {
        "BearerAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    schema["security"] = [{"BearerAuth": []}]
    app.openapi_schema = schema
    return schema

app.openapi = _custom_openapi


@app.get("/health")
def health():
    return {"status": "ok"}
