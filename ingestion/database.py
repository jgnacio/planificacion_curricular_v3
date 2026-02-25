from neo4j import GraphDatabase
import logging

class Neo4jManager:
    def __init__(self, uri="bolt://localhost:7687", user="neo4j", password=None):
        auth = None
        if user and password:
            auth = (user, password)
        elif password is None:
            # Often if NEO4J_AUTH=none, we don't need auth, but the driver might expect something or it might be ignored
            auth = None
            
        try:
            self.driver = GraphDatabase.driver(uri, auth=auth)
            # Test connection
            self.driver.verify_connectivity()
            logging.info("Conectado a Neo4j exitosamente.")
        except Exception as e:
            logging.error(f"Error al conectar a Neo4j: {e}")
            self.driver = None

    def close(self):
        if self.driver:
            self.driver.close()

    def get_or_create_node(self, tx, label, nombre):
        if not nombre:
            return None
        query = (
            f"MERGE (n:{label} {{nombre: $nombre}}) "
            "RETURN n"
        )
        result = tx.run(query, nombre=nombre)
        return result.single()[0]

    def create_relationship(self, tx, start_node_id, start_label, end_node_id, end_label, rel_type):
        query = (
            f"MATCH (a:{start_label}), (b:{end_label}) "
            f"WHERE id(a) = $start_id AND id(b) = $end_id "
            f"MERGE (a)-[:{rel_type}]->(b)"
        )
        tx.run(query, start_id=start_node_id, end_id=end_node_id)

    def save_competencia(self, ce_data, jerarquia):
        """
        ce_data: CompetenciaEspecifica object
        jerarquia: dict with 'espacio', 'unidad', 'tramo' names
        """
        if not self.driver:
            return

        with self.driver.session() as session:
            session.execute_write(self._save_tx, ce_data, jerarquia)

    def _save_tx(self, tx, ce, jer):
        # 1. Crear/Obtener nodos de jerarquía
        for label, key in [("Espacio", "espacio"), ("Unidad", "unidad"), ("Tramo", "tramo")]:
            nombre = jer.get(key)
            if nombre:
                tx.run(f"MERGE (n:{label} {{nombre: $nombre}})", nombre=nombre)

        # 2. Relacionar jerarquía
        if jer.get('unidad') and jer.get('espacio'):
            tx.run("MATCH (u:Unidad {nombre: $un}), (e:Espacio {nombre: $es}) "
                   "MERGE (u)-[:BELONGS_TO]->(e)", un=jer['unidad'], es=jer['espacio'])
        
        if jer.get('tramo'):
            if jer.get('unidad'):
                tx.run("MATCH (t:Tramo {nombre: $tr}), (u:Unidad {nombre: $un}) "
                       "MERGE (t)-[:BELONGS_TO]->(u)", tr=jer['tramo'], un=jer['unidad'])
            elif jer.get('espacio'):
                tx.run("MATCH (t:Tramo {nombre: $tr}), (e:Espacio {nombre: $es}) "
                       "MERGE (t)-[:BELONGS_TO]->(e)", tr=jer['tramo'], es=jer['espacio'])

        # 3. Crear nodo de Competencia
        query_ce = (
            "MERGE (c:CompetenciaEspecifica {id: $id}) "
            "SET c.enunciado = $enunciado, "
            "    c.desarrollo = $desarrollo, "
            "    c.ejes = $ejes, "
            "    c.mcn = $mcn, "
            "    c.nivel_pertenencia = $nivel"
        )
        tx.run(query_ce, 
               id=ce.id, 
               enunciado=ce.enunciado, 
               desarrollo=ce.desarrollo, 
               ejes=ce.ejes, 
               mcn=ce.mcn,
               nivel=ce.nivel_pertenencia)

        # 4. Relacionar CE con su padre inmediato en la jerarquía
        for label, key in [("Tramo", "tramo"), ("Unidad", "unidad"), ("Espacio", "espacio")]:
            nombre = jer.get(key)
            if nombre:
                tx.run(f"MATCH (c:CompetenciaEspecifica {{id: $ce_id}}), (p:{label} {{nombre: $p_nombre}}) "
                       "MERGE (c)-[:BELONGS_TO]->(p)", ce_id=ce.id, p_nombre=nombre)
                break # Solo al padre más específico

        # 5. Relacionar CE con su CE padre (si existe)
        if ce.padre:
            tx.run("MATCH (c:CompetenciaEspecifica {id: $ce_id}), (p:CompetenciaEspecifica {id: $p_id}) "
                   "MERGE (c)-[:CHILD_OF]->(p)", ce_id=ce.id, p_id=ce.padre)

    def clear_database(self):
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logging.info("Base de datos Neo4j limpiada correctamente.")
