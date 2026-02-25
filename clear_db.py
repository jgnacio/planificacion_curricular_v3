from ingestion.database import Neo4jManager
import logging

logging.basicConfig(level=logging.INFO)

def main():
    db = Neo4jManager()
    try:
        db.clear_database()
    finally:
        db.close()

if __name__ == "__main__":
    main()
