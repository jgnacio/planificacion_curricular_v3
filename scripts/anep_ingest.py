import fitz  # PyMuPDF
from neo4j import GraphDatabase
import re

class ANEPKnowledgeGraph:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self):
        self.driver.close()

    def create_hierarchy(self, ciclo, espacio, unidad, contenido, criterio):
        """
        Inserta los nodos y relaciones en Neo4j asegurando que no haya duplicados.
        """
        query = """
        MERGE (c:Ciclo {nombre: $ciclo})
        MERGE (e:Espacio {nombre: $espacio})
        MERGE (u:UnidadCurricular {nombre: $unidad})
        MERGE (cont:Contenido {descripcion: $contenido})
        MERGE (crit:CriterioLogro {descripcion: $criterio})
        
        MERGE (c)-[:CONTIENE_ESPACIO]->(e)
        MERGE (e)-[:TIENE_ASIGNATURA]->(u)
        MERGE (u)-[:DESARROLLA_CONTENIDO]->(cont)
        MERGE (cont)-[:EVALUA_MEDIANTE]->(crit)
        """
        with self.driver.session() as session:
            session.run(query, 
                        ciclo=ciclo, 
                        espacio=espacio, 
                        unidad=unidad, 
                        contenido=contenido, 
                        criterio=criterio)
            print(f"Ingestado: {unidad} -> Contenido/Criterio enlazados")

def parse_pdf_and_ingest(pdf_path, db_client):
    doc = fitz.open(pdf_path)
    
    # Variables de estado (Máquina de estados simple)
    current_ciclo = "1er Ciclo" # Esto se puede inferir del nombre del archivo o portada
    current_espacio = None
    current_unidad = None
    current_contenido = None
    current_criterio = None

    # Expresiones regulares base (a iterar y ajustar según el formato real del PDF)
    # Ejemplo: Si los títulos dicen "Espacio Científico-Matemático"
    regex_espacio = re.compile(r"^Espacio\s+(.+)", re.IGNORECASE)
    regex_unidad = re.compile(r"^Unidad Curricular[:\s]+(.+)", re.IGNORECASE)
    regex_criterio = re.compile(r"^Criterio de logro[:\s]*(.+)", re.IGNORECASE)

    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        text = page.get_text("text")
        lines = text.split('\n')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 1. Detectar Espacio
            match_espacio = regex_espacio.match(line)
            if match_espacio:
                current_espacio = match_espacio.group(0).strip()
                continue
            
            # 2. Detectar Unidad Curricular
            match_unidad = regex_unidad.match(line)
            if match_unidad:
                current_unidad = match_unidad.group(1).strip()
                continue
            
            # 3. Detectar Contenidos (Este suele ser el más complejo, requiere ajustar)
            # A menudo los contenidos son listas con viñetas o tienen un formato específico
            if line.startswith("•") and current_unidad and not current_criterio:
                current_contenido = line.replace("•", "").strip()
                continue

            # 4. Detectar Criterio de Logro
            match_criterio = regex_criterio.match(line)
            if match_criterio and current_contenido:
                current_criterio = match_criterio.group(1).strip()
                
                # ¡Bingo! Tenemos la rama completa, disparamos la inyección a Neo4j
                if current_espacio and current_unidad:
                    db_client.create_hierarchy(
                        current_ciclo,
                        current_espacio,
                        current_unidad,
                        current_contenido,
                        current_criterio
                    )
                
                # Reseteamos el criterio para el siguiente contenido
                current_criterio = None

    doc.close()

if __name__ == "__main__":
    # Credenciales configuradas en el docker-compose
    uri = "bolt://localhost:7687"
    user = "neo4j"
    password = "anep_secreto_2026"
    
    db = ANEPKnowledgeGraph(uri, user, password)
    
    pdf_file = "Compilación Programas 1er Ciclo - 2024.pdf"
    print(f"Iniciando procesamiento de {pdf_file}...")
    
    parse_pdf_and_ingest(pdf_file, db)
    
    db.close()
    print("Proceso finalizado.")