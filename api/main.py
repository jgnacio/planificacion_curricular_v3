import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from api.database import Base, engine
import api.models.planificacion  # noqa: F401 — register ORM models
import api.models.alumno          # noqa: F401
from api.routes import curriculum, planificaciones, alumnos

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
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve PDFs as static files so Flutter can download and open them
_pdfs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "pdfs")
if os.path.isdir(_pdfs_dir):
    app.mount("/pdfs", StaticFiles(directory=_pdfs_dir), name="pdfs")

app.include_router(curriculum.router)
app.include_router(planificaciones.router)
app.include_router(alumnos.router)


@app.get("/health")
def health():
    return {"status": "ok"}
