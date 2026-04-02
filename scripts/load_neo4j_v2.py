"""
Carga el JSON extraído por extract_curriculum_gemini.py en Neo4j.

Borra el grafo anterior y reconstruye con el schema correcto:

  (Ciclo)-[:TIENE_TRAMO]->(Tramo)-[:INCLUYE_GRADO]->(Grado)
  (Tramo)-[:TIENE_ESPACIO]->(Espacio)
  (Espacio)-[:TIENE_UNIDAD]->(UnidadCurricular)
  (UnidadCurricular)-[:DEFINE_CE]->(CompetenciaEspecifica)
  (CompetenciaEspecifica)-[:CONTRIBUYE_A]->(CompetenciaGeneral)
  (UnidadCurricular)-[:TIENE_EJE]->(Eje)
  (Eje)-[:TIENE_CONTENIDO]->(Contenido)
  (Contenido)-[:SE_EVALUA_CON]->(CriterioDeLogro)
  (Contenido)-[:TRABAJA_CE]->(CompetenciaEspecifica)

Uso:
    python scripts/load_neo4j_v2.py
    python scripts/load_neo4j_v2.py --json data/curriculum_tramo_4.json  # un tramo
    python scripts/load_neo4j_v2.py --dry-run  # valida el JSON sin tocar Neo4j
"""

import json
import argparse
from pathlib import Path
from neo4j import GraphDatabase

# ── Configuración ─────────────────────────────────────────────────────────────

NEO4J_URI      = "bolt://localhost:7687"
NEO4J_USER     = "neo4j"
NEO4J_PASSWORD = "anep_secreto_2026"
DEFAULT_JSON   = "data/curriculum_extracted.json"

# ── Setup del schema ──────────────────────────────────────────────────────────

CONSTRAINTS = [
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Ciclo)               REQUIRE n.nombre IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Tramo)               REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Grado)               REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Espacio)             REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:UnidadCurricular)    REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CompetenciaEspecifica) REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CompetenciaGeneral)  REQUIRE n.nombre IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Eje)                 REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Contenido)           REQUIRE n.id IS UNIQUE",
    "CREATE CONSTRAINT IF NOT EXISTS FOR (n:CriterioDeLogro)     REQUIRE n.id IS UNIQUE",
]


def setup_schema(session):
    for constraint in CONSTRAINTS:
        session.run(constraint)
    print("✅ Schema (constraints) creado")


def clear_graph(session):
    session.run("MATCH (n) DETACH DELETE n")
    print("🗑️  Grafo anterior borrado")


# ── Carga del grafo ───────────────────────────────────────────────────────────

def load_tramo(session, tramo_data: dict):
    ciclo_nombre = tramo_data["ciclo"]
    tramo_nombre = tramo_data["tramo"]
    tramo_id     = f"{ciclo_nombre}|{tramo_nombre}"

    # Ciclo y Tramo
    session.run("""
        MERGE (c:Ciclo {nombre: $ciclo})
        MERGE (t:Tramo {id: $tramo_id})
        SET t.nombre = $tramo_nombre, t.ciclo = $ciclo
        MERGE (c)-[:TIENE_TRAMO]->(t)
    """, ciclo=ciclo_nombre, tramo_id=tramo_id, tramo_nombre=tramo_nombre)

    # Grados
    for grado_nombre in tramo_data.get("grados", []):
        grado_id = f"{tramo_id}|{grado_nombre}"
        session.run("""
            MERGE (g:Grado {id: $grado_id})
            SET g.nombre = $grado_nombre, g.tramo = $tramo_nombre, g.ciclo = $ciclo
            WITH g
            MATCH (t:Tramo {id: $tramo_id})
            MERGE (t)-[:INCLUYE_GRADO]->(g)
        """, grado_id=grado_id, grado_nombre=grado_nombre,
             tramo_id=tramo_id, tramo_nombre=tramo_nombre, ciclo=ciclo_nombre)

    # Espacios → Unidades → CE → Ejes → Contenidos → Criterios
    for espacio_data in tramo_data.get("espacios", []):
        espacio_nombre = espacio_data["nombre"]
        espacio_id     = f"{tramo_id}|{espacio_nombre}"

        session.run("""
            MERGE (e:Espacio {id: $espacio_id})
            SET e.nombre = $espacio_nombre, e.tramo = $tramo_nombre
            WITH e
            MATCH (t:Tramo {id: $tramo_id})
            MERGE (t)-[:TIENE_ESPACIO]->(e)
        """, espacio_id=espacio_id, espacio_nombre=espacio_nombre,
             tramo_id=tramo_id, tramo_nombre=tramo_nombre)

        for unidad_data in espacio_data.get("unidades_curriculares", []):
            unidad_nombre = unidad_data["nombre"]
            unidad_id     = f"{espacio_id}|{unidad_nombre}"

            session.run("""
                MERGE (u:UnidadCurricular {id: $unidad_id})
                SET u.nombre = $unidad_nombre, u.espacio = $espacio_nombre,
                    u.tramo = $tramo_nombre, u.ciclo = $ciclo
                WITH u
                MATCH (e:Espacio {id: $espacio_id})
                MERGE (e)-[:TIENE_UNIDAD]->(u)
            """, unidad_id=unidad_id, unidad_nombre=unidad_nombre,
                 espacio_id=espacio_id, espacio_nombre=espacio_nombre,
                 tramo_nombre=tramo_nombre, ciclo=ciclo_nombre)

            # Competencias Específicas
            for ce in unidad_data.get("competencias_especificas", []):
                ce_id = f"{unidad_id}|{ce['codigo']}"
                session.run("""
                    MERGE (ce:CompetenciaEspecifica {id: $ce_id})
                    SET ce.codigo = $codigo, ce.descripcion = $descripcion,
                        ce.unidad = $unidad_nombre, ce.tramo = $tramo_nombre
                    WITH ce
                    MATCH (u:UnidadCurricular {id: $unidad_id})
                    MERGE (u)-[:DEFINE_CE]->(ce)
                """, ce_id=ce_id, codigo=ce["codigo"],
                     descripcion=ce.get("descripcion", ""),
                     unidad_id=unidad_id, unidad_nombre=unidad_nombre,
                     tramo_nombre=tramo_nombre)

                # Relación con Competencias Generales MCN
                for mcn_nombre in ce.get("contribuye_a_mcn", []):
                    session.run("""
                        MERGE (mcn:CompetenciaGeneral {nombre: $mcn_nombre})
                        WITH mcn
                        MATCH (ce:CompetenciaEspecifica {id: $ce_id})
                        MERGE (ce)-[:CONTRIBUYE_A]->(mcn)
                    """, mcn_nombre=mcn_nombre, ce_id=ce_id)

            # Ejes y Contenidos
            for eje_data in unidad_data.get("ejes", []):
                eje_nombre = eje_data.get("nombre", "Sin eje")
                eje_id     = f"{unidad_id}|{eje_nombre}"

                session.run("""
                    MERGE (eje:Eje {id: $eje_id})
                    SET eje.nombre = $eje_nombre, eje.unidad = $unidad_nombre,
                        eje.tramo = $tramo_nombre
                    WITH eje
                    MATCH (u:UnidadCurricular {id: $unidad_id})
                    MERGE (u)-[:TIENE_EJE]->(eje)
                """, eje_id=eje_id, eje_nombre=eje_nombre,
                     unidad_id=unidad_id, unidad_nombre=unidad_nombre,
                     tramo_nombre=tramo_nombre)

                for idx, contenido_data in enumerate(eje_data.get("contenidos", [])):
                    desc      = contenido_data.get("descripcion", "")
                    tipo      = contenido_data.get("tipo", "contenido")
                    grados    = contenido_data.get("grado", [])
                    contenido_id = f"{eje_id}|{idx}"

                    session.run("""
                        MERGE (cont:Contenido {id: $contenido_id})
                        SET cont.descripcion = $desc, cont.tipo = $tipo,
                            cont.grados = $grados, cont.eje = $eje_nombre,
                            cont.unidad = $unidad_nombre, cont.tramo = $tramo_nombre
                        WITH cont
                        MATCH (eje:Eje {id: $eje_id})
                        MERGE (eje)-[:TIENE_CONTENIDO]->(cont)
                    """, contenido_id=contenido_id, desc=desc, tipo=tipo,
                         grados=grados, eje_id=eje_id, eje_nombre=eje_nombre,
                         unidad_nombre=unidad_nombre, tramo_nombre=tramo_nombre)

                    # CE relacionadas al contenido
                    for ce_codigo in contenido_data.get("competencias_relacionadas", []):
                        ce_id = f"{unidad_id}|{ce_codigo}"
                        session.run("""
                            MATCH (cont:Contenido {id: $contenido_id})
                            MATCH (ce:CompetenciaEspecifica {id: $ce_id})
                            MERGE (cont)-[:TRABAJA_CE]->(ce)
                        """, contenido_id=contenido_id, ce_id=ce_id)

            # Criterios de logro — a nivel de UnidadCurricular
            for crit_idx, crit in enumerate(unidad_data.get("criterios_de_logro", [])):
                crit_desc = crit.get("descripcion", "")
                ce_eval   = crit.get("ce_evaluada")
                grados_crit = crit.get("grado", [])
                crit_id   = f"{unidad_id}|crit{crit_idx}"

                session.run("""
                    MERGE (crit:CriterioDeLogro {id: $crit_id})
                    SET crit.descripcion = $desc, crit.unidad = $unidad_nombre,
                        crit.tramo = $tramo_nombre, crit.grados = $grados
                    WITH crit
                    MATCH (u:UnidadCurricular {id: $unidad_id})
                    MERGE (u)-[:SE_EVALUA_CON]->(crit)
                """, crit_id=crit_id, desc=crit_desc, grados=grados_crit,
                     unidad_id=unidad_id, unidad_nombre=unidad_nombre,
                     tramo_nombre=tramo_nombre)

                if ce_eval:
                    ce_id = f"{unidad_id}|{ce_eval}"
                    session.run("""
                        MATCH (crit:CriterioDeLogro {id: $crit_id})
                        MATCH (ce:CompetenciaEspecifica {id: $ce_id})
                        MERGE (crit)-[:EVALUADO_POR_CE]->(ce)
                    """, crit_id=crit_id, ce_id=ce_id)


# ── Estadísticas ──────────────────────────────────────────────────────────────

def print_stats(session):
    labels = [
        "Ciclo", "Tramo", "Grado", "Espacio", "UnidadCurricular",
        "CompetenciaEspecifica", "CompetenciaGeneral", "Eje",
        "Contenido", "CriterioDeLogro",
    ]
    print("\n📊 Nodos en el grafo:")
    for label in labels:
        result = session.run(f"MATCH (n:{label}) RETURN count(n) AS total")
        total  = result.single()["total"]
        print(f"   {label:25s}: {total:>5}")


# ── Validación del JSON ───────────────────────────────────────────────────────

def validate_json(data: list) -> bool:
    ok = True
    required_top = {"ciclo", "tramo", "grados", "espacios"}

    for tramo_data in data:
        missing = required_top - tramo_data.keys()
        if missing:
            print(f"❌ Tramo '{tramo_data.get('tramo', '?')}' falta campos: {missing}")
            ok = False

        for espacio in tramo_data.get("espacios", []):
            if not espacio.get("nombre"):
                print(f"❌ Espacio sin nombre en {tramo_data.get('tramo')}")
                ok = False
            for unidad in espacio.get("unidades_curriculares", []):
                if not unidad.get("nombre"):
                    print(f"❌ Unidad sin nombre en {espacio.get('nombre')}")
                    ok = False
                if not unidad.get("ejes"):
                    print(f"⚠️  Unidad '{unidad.get('nombre')}' sin ejes")
    return ok


# ── Main ──────────────────────────────────────────────────────────────────────

def main(json_path: str, dry_run: bool):
    path = Path(json_path)
    if not path.exists():
        print(f"❌ No existe {path}")
        return

    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw)

    # El JSON puede ser una lista de tramos o un solo tramo
    if isinstance(data, dict):
        data = [data]

    print(f"📂 JSON cargado: {len(data)} tramo(s)")

    if not validate_json(data):
        print("\n⚠️  El JSON tiene problemas. Revisá la salida de Gemini.")
        if not dry_run:
            resp = input("¿Continuar de todas formas? (s/N): ")
            if resp.lower() != "s":
                return

    if dry_run:
        print("\n✅ Dry-run OK — JSON válido. No se tocó Neo4j.")
        return

    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))

    with driver.session() as session:
        setup_schema(session)
        clear_graph(session)

        for tramo_data in data:
            label = f"{tramo_data['ciclo']} — {tramo_data['tramo']}"
            print(f"\n⏳ Cargando {label}...")
            load_tramo(session, tramo_data)
            print(f"✅ {label} cargado")

        print_stats(session)

    driver.close()
    print("\n🎉 Grafo reconstruido exitosamente.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Cargar currículo EBI en Neo4j")
    parser.add_argument("--json",    default=DEFAULT_JSON, help="Path al JSON extraído")
    parser.add_argument("--dry-run", action="store_true",  help="Validar JSON sin cargar en Neo4j")
    args = parser.parse_args()
    main(args.json, args.dry_run)
