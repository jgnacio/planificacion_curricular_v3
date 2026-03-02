from ingestion.database import Neo4jManager
import logging

logging.basicConfig(level=logging.INFO)

QUERIES = [
    "CREATE CONSTRAINT FOR (c:CompetenciaEspecifica) REQUIRE c.id IS UNIQUE;",
    "CREATE CONSTRAINT FOR (m:CompetenciaMCN) REQUIRE m.nombre IS UNIQUE;",
    "CREATE CONSTRAINT FOR (e:EjeTematico) REQUIRE e.nombre IS UNIQUE;",
    "CREATE INDEX FOR (u:Unidad) ON (u.nombre);",
    "CREATE INDEX FOR (t:Tramo) ON (t.nombre);",
    "CREATE INDEX FOR (cont:Contenido) ON (cont.descripcion);"
]

def main():
    db = Neo4jManager()
    if not db.driver:
        logging.error("Failed to connect to Neo4j.")
        return
        
    try:
        with db.driver.session() as session:
            for query in QUERIES:
                try:
                    session.run(query)
                    logging.info(f"Successfully executed: {query}")
                except Exception as e:
                    # It might fail if constraint/index already exists, which is fine
                    logging.warning(f"Error executing {query}: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    main()
