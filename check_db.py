from ingestion.database import Neo4jManager

def check_db():
    db = Neo4jManager()
    if not db.driver:
        print("No DB connection")
        return
        
    with db.driver.session() as session:
        # Check if criteria are saved as contenidos
        res = session.run("MATCH (c:Contenido) RETURN c.descripcion as desc LIMIT 20")
        print("Top 20 Contenidos:")
        for r in res:
            print(" -", r["desc"])
            
        print("\n----------------\n")
        res = session.run("MATCH (cr:CriterioLogro) RETURN cr.descripcion as desc LIMIT 10")
        print("Top 10 Criterios:")
        for r in res:
            print(" -", r["desc"])

if __name__ == "__main__":
    check_db()
