from neo4j import GraphDatabase
import logging
import os

class Neo4jManager:
    def __init__(self, uri=None, user=None, password=None):
        env = os.getenv("APP_ENV", "dev").lower()

        if env == "dev":
            # Neo4j local del docker-compose (NEO4J_AUTH=none)
            self.uri = uri or "bolt://localhost:7687"
            auth = None
            print(f"[NEO4J] Modo DEV → {self.uri} (sin auth)")
        else:
            self.uri = uri or os.getenv("NEO4J_URI", "neo4j+s://91b545dd.databases.neo4j.io")
            self.user = user or os.getenv("NEO4J_USER", "91b545dd")
            self.password = password or os.getenv("NEO4J_PASSWORD", "ZosSVm3JRGcNkVBwYNFMSp5L8odcSpEhRv3VnbUlFhQ")
            auth = (self.user, self.password)
            print(f"[NEO4J] Modo PROD → {self.uri}")

        try:
            self.driver = GraphDatabase.driver(self.uri, auth=auth)
            self.driver.verify_connectivity()
            logging.info(f"Conectado exitosamente a: {self.uri}")
        except Exception as e:
            logging.error(f"Error crítico al conectar a Neo4j ({self.uri}): {e}")
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
        for label, key in [("Ciclo", "ciclo"), ("Espacio", "espacio"), ("Unidad", "unidad"), ("Tramo", "tramo")]:
            nombre = jer.get(key)
            if nombre:
                tx.run(f"MERGE (n:{label} {{nombre: $nombre}})", nombre=nombre)

        # 2. Relacionar jerarquía
        if jer.get('espacio') and jer.get('ciclo'):
            tx.run("MATCH (e:Espacio {nombre: $es}), (c:Ciclo {nombre: $ci}) "
                   "MERGE (e)-[:BELONGS_TO]->(c)", es=jer['espacio'], ci=jer['ciclo'])
                   
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
            "    c.nivel_pertenencia = $nivel"
        )
        tx.run(query_ce, 
               id=ce.id, 
               enunciado=ce.enunciado, 
               desarrollo=ce.desarrollo, 
               nivel=ce.nivel_pertenencia)

        import re
        # Convertir Ejes en Nodos Independientes
        if ce.ejes:
            for eje in [e.strip() for e in re.split(r',|;', ce.ejes) if e.strip()]:
                tx.run(
                    "MERGE (e:Eje {nombre: $nombre}) "
                    "WITH e MATCH (c:CompetenciaEspecifica {id: $ce_id}) "
                    "MERGE (c)-[:PERTENECE_A_EJE]->(e)",
                    nombre=eje, ce_id=ce.id
                )

        # Convertir MCN en Nodos Independientes
        if ce.mcn:
            for m in [m.strip() for m in re.split(r',|;', ce.mcn) if m.strip()]:
                tx.run(
                    "MERGE (node_mcn:CompetenciaMCN {nombre: $nombre}) "
                    "WITH node_mcn MATCH (c:CompetenciaEspecifica {id: $ce_id}) "
                    "MERGE (c)-[:CONTRIBUYE_A]->(node_mcn)",
                    nombre=m, ce_id=ce.id
                )

        # 4. Relacionar CE con su padre inmediato en la jerarquía
        for label, key in [("Tramo", "tramo"), ("Unidad", "unidad"), ("Espacio", "espacio"), ("Ciclo", "ciclo")]:
            nombre = jer.get(key)
            if nombre:
                tx.run(f"MATCH (c:CompetenciaEspecifica {{id: $ce_id}}), (p:{label} {{nombre: $p_nombre}}) "
                       "MERGE (c)-[:BELONGS_TO]->(p)", ce_id=ce.id, p_nombre=nombre)
                break # Solo al padre más específico

        # 5. Relacionar CE con su CE padre (si existe)
        if ce.padre:
            tx.run("MATCH (c:CompetenciaEspecifica {id: $ce_id}), (p:CompetenciaEspecifica {id: $p_id}) "
                   "MERGE (c)-[:CHILD_OF]->(p)", ce_id=ce.id, p_id=ce.padre)

    def _normalizar_grado(self, grado_bruto):
        """
        Filtro de hierro para unificar la nomenclatura de grados y evitar 
        nodos duplicados en Neo4j por culpa de los caracteres del PDF.
        """
        if not grado_bruto or grado_bruto.lower() == "desconocido":
            return "Desconocido"
            
        g = grado_bruto.lower()
        
        # 1. Si el "grado" detectado fue en realidad un Tramo genérico
        if "tramo" in g:
            if "1" in g: return "Tramo 1"
            if "2" in g: return "Tramo 2"
            if "3" in g: return "Tramo 3"
            if "4" in g: return "Tramo 4"
            if "5" in g: return "Tramo 5"
            if "6" in g: return "Tramo 6"
            return grado_bruto.strip().capitalize()
            
        # 2. Si es una combinación de grados (Ej: "Grados 5.º y 6.º")
        if "1" in g and "2" in g: return "Grados 1.º y 2.º"
        if "3" in g and "4" in g: return "Grados 3.º y 4.º"
        if "5" in g and "6" in g: return "Grados 5.º y 6.º"
        if "7" in g and "8" in g and "9" in g: return "Grados 7.º, 8.º y 9.º"
        
        # 3. Si es un grado individual (Atrapa cualquier número sin importar los caracteres raros)
        if "10" in g: return "10.mo grado"
        if "1" in g: return "1.er grado"
        if "2" in g: return "2.do grado"
        if "3" in g: return "3.er grado"
        if "4" in g: return "4.to grado"
        if "5" in g: return "5.to grado"
        if "6" in g: return "6.to grado"
        if "7" in g: return "7.mo grado"
        if "8" in g: return "8.vo grado"
        if "9" in g: return "9.no grado"
        
        return grado_bruto.strip().capitalize()

    def save_contenido_criterio(self, ce_id, contenido, criterio, grado=None, tramo=None, pagina=None, pdf_fuente=None):
        if not self.driver:
            return

        grado_limpio = self._normalizar_grado(grado) if grado else None

        with self.driver.session() as session:
            session.execute_write(self._save_contenido_criterio_tx, ce_id, contenido, criterio, grado_limpio, tramo, pagina, pdf_fuente)

    def _save_contenido_criterio_tx(self, tx, ce_id, contenido, criterio, grado, tramo, pagina, pdf_fuente):
        check = tx.run("MATCH (ce:CompetenciaEspecifica {id: $ce_id}) RETURN ce", ce_id=ce_id)
        if not check.single():
            print(f"  [⚠️ CE SIN DATOS] Creando stub para CE no encontrado en jerarquía: '{ce_id}'")

        query = (
            "MERGE (ce:CompetenciaEspecifica {id: $ce_id}) "
            "MERGE (c:Contenido {descripcion: $contenido}) "
            "ON CREATE SET c.pagina = $pagina, c.pdf_fuente = $pdf_fuente "
            "MERGE (cr:CriterioLogro {descripcion: $criterio}) "
            "MERGE (ce)-[:VINCULA_CON]->(c) "
            "MERGE (c)-[:EVALUADO_POR]->(cr)"
        )
        tx.run(query, ce_id=ce_id, contenido=contenido, criterio=criterio, pagina=pagina, pdf_fuente=pdf_fuente)

        if grado and grado != "Desconocido":
            tx.run(
                "MATCH (c:Contenido {descripcion: $contenido}) "
                "MERGE (g:Grado {nombre: $grado}) "
                "MERGE (c)-[:SE_ENSEÑA_EN]->(g)",
                contenido=contenido, grado=grado
            )

        if tramo and tramo != "Desconocido":
            tx.run(
                "MATCH (c:Contenido {descripcion: $contenido}) "
                "MERGE (t:Tramo {nombre: $tramo}) "
                "MERGE (c)-[:SE_ENSEÑA_EN]->(t)",
                contenido=contenido, tramo=tramo
            )

    def clear_database(self):
        if not self.driver:
            return
        with self.driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
            logging.info("Base de datos Neo4j limpiada correctamente.")

# ==========================================
# CONFIGURACIÓN DE BASE DE DATOS
# ==========================================
_env = os.getenv("APP_ENV", "dev").lower()
if _env == "dev":
    NEO4J_URI = "bolt://localhost:7687"
    NEO4J_USER = ""
    NEO4J_PASSWORD = ""
else:
    NEO4J_URI = os.getenv("NEO4J_URI", "neo4j+s://91b545dd.databases.neo4j.io")
    NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
    NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "")

# ==========================================
# DEFINICIÓN DE LAS CONSULTAS (TOOLS)
# ==========================================

def consultar_normativa_neo4j(tramo: str, unidad: str, tema: str) -> dict:
    """
    Busca en la base de datos de grafos (Neo4j) el marco normativo oficial de ANEP
    para un tramo, unidad curricular y tema/contenido específicos.

    Args:
        tramo (str): El tramo educativo (ej. "Tramo 1 | Niveles 3, 4 y 5 años" o "Tramo 1").
        unidad (str): La unidad curricular o materia (ej. "Educación Física").
        tema (str): El contenido específico o palabra clave del tema a enseñar.

    Returns:
        dict: Diccionario con el 'status' ('success' o 'error') y el 'report' 
              conteniendo los datos estructurados (CE, Criterio, MCN, Ejes).
    """
    
    # Consulta Cypher dinámica para atravesar el grafo y buscar coincidencias
    print(f"\n[🔧 TOOL consultar_normativa_neo4j] -> Iniciando búsqueda de normativa...")
    print(f"[🔍 PARÁMETROS] Tramo: '{tramo}' | Unidad: '{unidad}' | Tema: '{tema}'")
    
    cypher_query = """
    // Conectamos CE con Contenido y Criterio
    MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont:Contenido)-[:EVALUADO_POR]->(crit:CriterioLogro)
    
    // Relacionamos CE con el Tramo para filtrar
    MATCH (ce)-[:BELONGS_TO*1..3]->(t:Tramo)
    
    // Filtramos usando el prefijo único de CE para la Unidad
    // y los textos de Tramo y Tema
    WHERE ce.id STARTS WITH toUpper(replace($unidad, ' ', '_')) + '_'
      AND toLower(t.nombre) CONTAINS toLower($tramo)
      AND toLower(cont.descripcion) CONTAINS toLower($tema)
      
    // Buscamos MCN y Ejes de forma opcional. Usamos '--' para ignorar el nombre exacto de la relación por seguridad.
    OPTIONAL MATCH (ce)-[:CONTRIBUYE_A]->(mcn:CompetenciaMCN)
    OPTIONAL MATCH (ce)-[:PERTENECE_A_EJE]->(eje:Eje)
    
    RETURN
        ce.id AS ce_id,
        ce.enunciado AS ce_enunciado,
        ce.desarrollo AS ce_desarrollo,
        cont.descripcion AS contenido,
        crit.descripcion AS criterio,
        cont.pagina AS pagina,
        cont.pdf_fuente AS pdf_fuente,
        collect(DISTINCT mcn.nombre) AS mcns,
        collect(DISTINCT eje.nombre) AS ejes
    LIMIT 3
    """
    
    try:
        # Usando la clase Neo4jManager para consultar
        db_manager = Neo4jManager(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        if not db_manager.driver:
            return {
                "status": "error",
                "error_message": "Error interno: no se pudo conectar con la base de datos Neo4j."
            }

        with db_manager.driver.session() as session:
            result = session.run(cypher_query, unidad=unidad, tramo=tramo, tema=tema)
            records = list(result)
            
        db_manager.close()

        if not records:
            print(f"[⚠️ RESULTADO] No se encontró normativa en Neo4j para estos parámetros.")
            return {
                "status": "error",
                "error_message": f"No se encontró normativa en ANEP para Unidad: '{unidad}', Tramo: '{tramo}' y Tema: '{tema}'. Pídele al usuario que verifique los términos."
            }

        # Formatear el resultado para que el LLM lo entienda perfectamente
        report_lines = ["DATOS NORMATIVOS OFICIALES ENCONTRADOS:\n"]
        for idx, record in enumerate(records):
            report_lines.append(f"--- RESULTADO {idx + 1} ---")
            report_lines.append(f"COMPETENCIA ESPECÍFICA: [{record['ce_id']}] {record['ce_enunciado']}")
            report_lines.append(f"DESARROLLO CE: {record['ce_desarrollo']}")
            report_lines.append(f"CONTENIDO: {record['contenido']}")
            report_lines.append(f"CRITERIO DE LOGRO: {record['criterio']}")
            if record['mcns']:
                report_lines.append(f"MCN (COMPETENCIAS GENERALES): {', '.join(record['mcns'])}")
            if record['ejes']:
                report_lines.append(f"EJES TEMÁTICOS: {', '.join(record['ejes'])}")
            pagina = record.get('pagina')
            pdf_fuente = record.get('pdf_fuente')
            if pagina and pdf_fuente:
                report_lines.append(f"FUENTE_PDF: {pdf_fuente} | PAGINA: {pagina}")
                report_lines.append(f"BADGE_REF: [[REF:{pdf_fuente}:{pagina}]]")
            report_lines.append("")

        print(f"[✅ RESULTADO] Se encontraron {len(records)} registros normativos.")
        print("-" * 40)
        return {
            "status": "success",
            "report": "\\n".join(report_lines)
        }

    except Exception as e:
        print(f"[❌ ERROR] Excepción al consultar Neo4j: {str(e)}")
        return {
            "status": "error",
            "error_message": f"Error interno al conectar con la base de datos Neo4j: {str(e)}"
        }


def buscar_contenido_por_texto(texto: str, tramo: str = "") -> dict:
    """
    Busca contenidos curriculares en Neo4j usando búsqueda full-text semántica.
    Ideal para validar una actividad de planificación existente: dado el texto de
    una actividad (contenido + meta + plan), devuelve los nodos del programa oficial
    que mejor coinciden (Competencia, Contenido, Criterio de Logro, Tramo).

    Args:
        texto (str): Texto libre de la actividad a buscar (ej: "La práctica de escritura: selección del tema").
        tramo (str): Tramo educativo opcional para filtrar (ej: "Tramo 3", "Grados 3"). Si está vacío, busca en todos.

    Returns:
        dict: Diccionario con 'status' y 'resultados' (lista de matches con CE, contenido, criterio, tramo).
    """
    print(f"\n[🔧 TOOL buscar_contenido_por_texto] Texto: '{texto[:60]}...' | Tramo: '{tramo}'")

    cypher_query = """
    CALL db.index.fulltext.queryNodes("contenido_ft", $texto) YIELD node AS cont, score
    MATCH (ce:CompetenciaEspecifica)-[:VINCULA_CON]->(cont)-[:EVALUADO_POR]->(crit:CriterioLogro)
    MATCH (ce)-[:BELONGS_TO*1..3]->(t:Tramo)
    WHERE $tramo = "" OR toLower(t.nombre) CONTAINS toLower($tramo)
    MATCH (ce)-[:BELONGS_TO*1..3]->(u:Unidad)
    OPTIONAL MATCH (u)-[:BELONGS_TO]->(e:Espacio)
    RETURN
        ce.id          AS ce_id,
        ce.enunciado   AS ce_enunciado,
        cont.descripcion AS contenido,
        crit.descripcion AS criterio,
        t.nombre       AS tramo,
        u.nombre       AS unidad,
        e.nombre       AS espacio,
        cont.pagina    AS pagina,
        cont.pdf_fuente AS pdf_fuente,
        score
    ORDER BY score DESC
    LIMIT 5
    """

    try:
        db_manager = Neo4jManager(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        if not db_manager.driver:
            return {"status": "error", "error_message": "No se pudo conectar con Neo4j."}

        with db_manager.driver.session() as session:
            result = session.run(cypher_query, texto=texto, tramo=tramo)
            records = list(result)
        db_manager.close()

        if not records:
            print("[⚠️ RESULTADO] Sin matches en el índice full-text.")
            return {
                "status": "not_found",
                "error_message": f"No se encontraron contenidos que coincidan con: '{texto}'. Intenta reformular con términos del programa oficial."
            }

        resultados = []
        for r in records:
            resultados.append({
                "score":      round(r["score"], 2),
                "ce_id":      r["ce_id"],
                "enunciado":  r["ce_enunciado"],
                "contenido":  r["contenido"],
                "criterio":   r["criterio"],
                "tramo":      r["tramo"],
                "unidad":     r["unidad"],
                "espacio":    r["espacio"],
                "pagina":     r["pagina"],
                "pdf_fuente": r["pdf_fuente"],
            })

        print(f"[✅ RESULTADO] {len(resultados)} matches encontrados.")
        return {"status": "success", "resultados": resultados}

    except Exception as e:
        print(f"[❌ ERROR] {str(e)}")
        return {"status": "error", "error_message": str(e)}
