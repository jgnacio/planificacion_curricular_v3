from neo4j import GraphDatabase

def verify_neo4j():
    uri = "bolt://localhost:7687"
    driver = GraphDatabase.driver(uri, auth=None)
    
    with driver.session() as session:
        # Check node counts
        result = session.run("MATCH (n) RETURN labels(n)[0] as label, count(*) as count")
        print("Node counts:")
        for record in result:
            print(f"- {record['label']}: {record['count']}")
        
        # Check relationship counts
        result = session.run("MATCH ()-[r]->() RETURN type(r) as type, count(*) as count")
        print("\nRelationship counts:")
        for record in result:
            print(f"- {record['type']}: {record['count']}")

    driver.close()

if __name__ == "__main__":
    verify_neo4j()
