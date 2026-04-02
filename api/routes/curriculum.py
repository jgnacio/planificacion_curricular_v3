import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from fastapi import APIRouter
from neo4j import GraphDatabase

load_dotenv()

router = APIRouter(tags=["curriculum"])

# ──────────────────────────────────────────────
# Neo4j connection
# ──────────────────────────────────────────────

_env = os.getenv("APP_ENV", "dev").lower()
if _env == "dev":
    _NEO4J_URI = "bolt://localhost:7687"
    _NEO4J_AUTH = None
else:
    _NEO4J_URI = os.getenv("NEO4J_URI", "")
    _NEO4J_AUTH = (os.getenv("NEO4J_USER", ""), os.getenv("NEO4J_PASSWORD", ""))


def _get_driver():
    return GraphDatabase.driver(_NEO4J_URI, auth=_NEO4J_AUTH)


def _run(cypher: str, **params) -> list[dict]:
    driver = _get_driver()
    with driver.session() as session:
        result = session.run(cypher, **params)
        records = [dict(r) for r in result]
    driver.close()
    return records


# ──────────────────────────────────────────────
# Endpoints
# ──────────────────────────────────────────────

@router.get("/ciclos")
def get_ciclos():
    records = _run("MATCH (c:Ciclo) RETURN c.nombre AS name ORDER BY c.nombre")
    return [r["name"] for r in records]


@router.get("/espacios")
def get_espacios(ciclo: str):
    records = _run(
        "MATCH (e:Espacio)-[:BELONGS_TO]->(c:Ciclo {nombre: $ciclo}) "
        "RETURN e.nombre AS name ORDER BY e.nombre",
        ciclo=ciclo,
    )
    return [r["name"] for r in records]


@router.get("/unidades")
def get_unidades(espacio: str):
    records = _run(
        "MATCH (u:Unidad)-[:BELONGS_TO]->(e:Espacio {nombre: $espacio}) "
        "RETURN u.nombre AS name ORDER BY u.nombre",
        espacio=espacio,
    )
    return [r["name"] for r in records]


@router.get("/grados")
def get_grados(ciclo: str):
    records = _run(
        """
        MATCH (t:Tramo)-[*1..3]->(c:Ciclo {nombre: $ciclo})
        WITH collect(DISTINCT t.nombre) AS tramos
        OPTIONAL MATCH (g:Grado)<-[:SE_ENSEÑA_EN]-(cont:Contenido)<-[:VINCULA_CON]-
                        (ce:CompetenciaEspecifica)-[:BELONGS_TO*1..5]->(c2:Ciclo {nombre: $ciclo})
        WITH tramos, collect(DISTINCT g.nombre) AS grados
        RETURN tramos, grados
        """,
        ciclo=ciclo,
    )
    if not records:
        return []
    tramos = records[0].get("tramos") or []
    grados = records[0].get("grados") or []
    return sorted(set(tramos + grados))


@router.get("/contenidos")
def get_contenidos(unidad: str, grado: str = ""):
    prefix = unidad.replace(" ", "_").upper() + "_"
    if grado:
        records = _run(
            """
            MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido)
            WHERE ce.id STARTS WITH $prefix
              AND cont.descripcion <> toUpper(cont.descripcion)
            OPTIONAL MATCH (ce)-[:BELONGS_TO*1..3]->(t:Tramo {nombre: $grado})
            OPTIONAL MATCH (cont)-[:SE_ENSEÑA_EN]->(g:Grado {nombre: $grado})
            WITH cont, t, g
            WHERE t IS NOT NULL OR g IS NOT NULL
            RETURN DISTINCT cont.descripcion AS name ORDER BY cont.descripcion
            """,
            prefix=prefix,
            grado=grado,
        )
    else:
        records = _run(
            """
            MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido)
            WHERE ce.id STARTS WITH $prefix
              AND cont.descripcion <> toUpper(cont.descripcion)
            RETURN DISTINCT cont.descripcion AS name ORDER BY cont.descripcion
            """,
            prefix=prefix,
        )
    return [r["name"] for r in records]


@router.get("/contenido-details")
def get_contenido_details(contenido: str, unidad: str):
    prefix = unidad.replace(" ", "_").upper() + "_"
    records = _run(
        """
        MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido {descripcion: $contenido})
        WHERE ce.id STARTS WITH $prefix
        OPTIONAL MATCH (cont)-[:EVALUADO_POR]->(crit:CriterioLogro)
        OPTIONAL MATCH (ce)-[:CONTRIBUYE_A]->(mcn:CompetenciaMCN)
        OPTIONAL MATCH (ce)-[:PERTENECE_A_EJE]->(eje:Eje)
        RETURN
          ce.id            AS ce_id,
          ce.enunciado     AS ce_enunciado,
          ce.desarrollo    AS ce_desarrollo,
          collect(DISTINCT crit.descripcion) AS criterios,
          collect(DISTINCT mcn.nombre)       AS mcns,
          collect(DISTINCT eje.nombre)       AS ejes,
          cont.pagina      AS pagina,
          cont.pdf_fuente  AS pdf_fuente
        """,
        contenido=contenido,
        prefix=prefix,
    )
    return [
        {
            "ce_id": r["ce_id"],
            "ce_enunciado": r["ce_enunciado"],
            "ce_desarrollo": r["ce_desarrollo"],
            "criterios": r["criterios"] or [],
            "mcns": r["mcns"] or [],
            "ejes": r["ejes"] or [],
            "pagina": r["pagina"],
            "pdf_fuente": r["pdf_fuente"],
        }
        for r in records
    ]


@router.post("/buscar")
def buscar_contenido(body: dict):
    """Búsqueda full-text semántica — delega a la función del agente."""
    from ingestion.database import buscar_contenido_por_texto
    texto = body.get("texto", "")
    tramo = body.get("tramo", "")
    return buscar_contenido_por_texto(texto, tramo)


# ──────────────────────────────────────────────
# Structured curriculum (JSON file)
# ──────────────────────────────────────────────

_curriculum_cache: dict | None = None


@router.get("/curriculum/estructura")
def get_curriculum_estructura():
    """Returns the full structured curriculum from the parsed JSON."""
    import json

    global _curriculum_cache
    if _curriculum_cache is None:
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "curriculum_structure.json",
        )
        with open(json_path, encoding="utf-8") as f:
            _curriculum_cache = json.load(f)
    return _curriculum_cache
