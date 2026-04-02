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

    def save_document_node(self, node, doc_id: str, fecha_upload: str) -> None:
        """
        Persiste un nodo DocumentoDocente en Neo4j.

        Acepta CurriculumNode o DocumentNode del hierarchizer.
        Usa MERGE sobre (doc_id, texto) para evitar duplicados.
        """
        if not self.driver:
            return
        with self.driver.session() as session:
            session.execute_write(self._save_document_node_tx, node, doc_id, fecha_upload)

    def _save_document_node_tx(self, tx, node, doc_id: str, fecha_upload: str) -> None:
        from ingestion.hierarchizer import CurriculumNode

        texto = node.texto or ""
        if not texto.strip():
            return

        if isinstance(node, CurriculumNode):
            titulo = node.eje or node.unidad or node.espacio or "Sin título"
            props = {
                "doc_id": doc_id,
                "titulo_seccion": titulo,
                "texto": texto,
                "fecha_upload": fecha_upload,
                "fuente": "curriculum_ondevice",
                "ciclo": node.ciclo,
                "espacio": node.espacio,
                "unidad": node.unidad,
                "eje": node.eje,
                "tipo": node.tipo,
            }
        else:
            props = {
                "doc_id": doc_id,
                "titulo_seccion": node.titulo_seccion,
                "texto": texto,
                "fecha_upload": fecha_upload,
                "fuente": "docente",
                "tipo": node.tipo,
            }

        tx.run(
            """
            MERGE (d:DocumentoDocente {doc_id: $doc_id, texto: $texto})
            SET d += $props
            """,
            doc_id=doc_id,
            texto=texto,
            props=props,
        )

    def ensure_fulltext_index(self) -> None:
        """
        Crea o recrea el índice full-text que incluye Contenido y DocumentoDocente.
        Llamar una vez al iniciar la app o después de cargar datos nuevos.
        """
        if not self.driver:
            return
        with self.driver.session() as session:
            # Eliminar índice previo si existe (puede no tener DocumentoDocente)
            try:
                session.run("DROP INDEX contenido_ft IF EXISTS")
            except Exception:
                pass
            session.run(
                """
                CREATE FULLTEXT INDEX contenido_ft IF NOT EXISTS
                FOR (n:Contenido|DocumentoDocente)
                ON EACH [n.descripcion, n.texto]
                """
            )
            logging.info("Índice full-text 'contenido_ft' creado/actualizado.")

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

def listar_contenidos(tramo: str, unidad: str) -> dict:
    """
    Devuelve TODOS los contenidos curriculares disponibles para un tramo y unidad,
    agrupados por eje. Usá esta tool PRIMERO para mostrar las opciones disponibles
    al docente antes de que elija un contenido específico.

    Use this tool when the user specifies a tramo and unidad and you need to show
    all available content options. Returns grouped content by eje.

    Args:
        tramo: El tramo educativo (ej. "Tramo 4")
        unidad: La unidad curricular (ej. "Matemática", "Lengua Española")

    Returns:
        dict con 'status' y 'ejes' (lista de ejes, cada uno con lista de 'contenidos')
    """
    print(f"\n[TOOL listar_contenidos] Tramo: '{tramo}' | Unidad: '{unidad}'")

    cypher_query = """
    MATCH (tr:Tramo)-[:TIENE_ESPACIO]->(:Espacio)-[:TIENE_UNIDAD]->(uc:UnidadCurricular)
    WHERE toLower(tr.nombre) CONTAINS toLower($tramo)
      AND toLower(uc.nombre) CONTAINS toLower($unidad)
    MATCH (uc)-[:TIENE_EJE]->(eje:Eje)-[:TIENE_CONTENIDO]->(cont:Contenido)
    RETURN eje.nombre AS eje,
           collect({descripcion: cont.descripcion, tipo: cont.tipo, grados: cont.grados}) AS contenidos,
           tr.nombre AS tramo,
           uc.nombre AS unidad_nombre
    ORDER BY eje.nombre
    """

    try:
        db_manager = Neo4jManager(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        if not db_manager.driver:
            return {
                "status": "error",
                "error_message": "Error interno: no se pudo conectar con la base de datos Neo4j."
            }

        with db_manager.driver.session() as session:
            result = session.run(cypher_query, tramo=tramo, unidad=unidad)
            records = list(result)

        db_manager.close()

        if not records:
            return {
                "status": "not_found",
                "error_message": "No se encontró el tramo/unidad. Verificá los nombres."
            }

        ejes = []
        total_contenidos = 0
        tramo_nombre = records[0]["tramo"]
        unidad_nombre = records[0]["unidad_nombre"]

        for record in records:
            contenidos = record["contenidos"]
            total_contenidos += len(contenidos)
            ejes.append({
                "eje": record["eje"],
                "contenidos": [
                    {
                        "descripcion": c["descripcion"],
                        "tipo": c["tipo"],
                        "grados": c["grados"],
                    }
                    for c in contenidos
                ]
            })

        print(f"[OK] {total_contenidos} contenidos encontrados en {len(ejes)} ejes.")
        return {
            "status": "success",
            "tramo": tramo_nombre,
            "unidad": unidad_nombre,
            "total_contenidos": total_contenidos,
            "ejes": ejes,
        }

    except Exception as e:
        print(f"[ERROR] Excepcion al consultar Neo4j: {str(e)}")
        return {
            "status": "error",
            "error_message": f"Error interno al conectar con la base de datos Neo4j: {str(e)}"
        }


def consultar_detalle_contenido(tramo: str, unidad: str, contenido: str) -> dict:
    """
    Obtiene el detalle normativo completo para UN contenido específico: Competencia
    Específica, Criterios de Logro vinculados y Competencias Generales (MCN).
    Llamá esta tool DESPUÉS de que el docente elige un contenido de la lista.

    Use this tool to get the full curriculum detail for a specific content item
    that the teacher has already selected.

    Args:
        tramo: El tramo educativo (ej. "Tramo 4")
        unidad: La unidad curricular (ej. "Matemática")
        contenido: Descripción del contenido elegido (búsqueda por CONTAINS)

    Returns:
        dict con 'status' y 'detalle' con CE, criterios de logro y MCNs
    """
    print(f"\n[TOOL consultar_detalle_contenido] Tramo: '{tramo}' | Unidad: '{unidad}' | Contenido: '{contenido}'")

    cypher_query = """
    MATCH (tr:Tramo)-[:TIENE_ESPACIO]->(:Espacio)-[:TIENE_UNIDAD]->(uc:UnidadCurricular)
    WHERE toLower(tr.nombre) CONTAINS toLower($tramo)
      AND toLower(uc.nombre) CONTAINS toLower($unidad)
    MATCH (uc)-[:TIENE_EJE]->(eje:Eje)-[:TIENE_CONTENIDO]->(cont:Contenido)
    WHERE toLower(cont.descripcion) CONTAINS toLower($contenido)
    OPTIONAL MATCH (cont)-[:TRABAJA_CE]->(ce:CompetenciaEspecifica)
    OPTIONAL MATCH (ce)<-[:EVALUADO_POR_CE]-(crit:CriterioDeLogro)
    OPTIONAL MATCH (ce)-[:CONTRIBUYE_A]->(mcn:CompetenciaGeneral)
    RETURN
      cont.descripcion     AS contenido,
      cont.tipo            AS tipo,
      cont.grados          AS grados,
      eje.nombre           AS eje,
      tr.nombre            AS tramo,
      uc.nombre            AS unidad,
      ce.codigo            AS ce_codigo,
      ce.descripcion       AS ce_descripcion,
      collect(DISTINCT crit.descripcion) AS criterios,
      collect(DISTINCT mcn.nombre)       AS mcns
    ORDER BY ce.codigo
    LIMIT 10
    """

    try:
        db_manager = Neo4jManager(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        if not db_manager.driver:
            return {
                "status": "error",
                "error_message": "Error interno: no se pudo conectar con la base de datos Neo4j."
            }

        with db_manager.driver.session() as session:
            result = session.run(cypher_query, tramo=tramo, unidad=unidad, contenido=contenido)
            records = list(result)

        db_manager.close()

        if not records:
            return {
                "status": "not_found",
                "error_message": "No se encontró el contenido. Intentá con palabras clave del nombre exacto."
            }

        first = records[0]
        print(f"[OK] Detalle encontrado para '{first['contenido']}' — {len(records)} CE(s).")
        return {
            "status": "success",
            "contenido": first["contenido"],
            "tipo": first["tipo"],
            "grados": first["grados"],
            "eje": first["eje"],
            "tramo": first["tramo"],
            "unidad": first["unidad"],
            "competencias": [
                {
                    "ce_codigo": r["ce_codigo"],
                    "ce_descripcion": r["ce_descripcion"],
                    "criterios_de_logro": [c for c in r["criterios"] if c],
                    "mcns": [m for m in r["mcns"] if m],
                }
                for r in records if r["ce_codigo"]
            ],
        }

    except Exception as e:
        print(f"[ERROR] Excepcion al consultar Neo4j: {str(e)}")
        return {
            "status": "error",
            "error_message": f"Error interno al conectar con la base de datos Neo4j: {str(e)}"
        }


def buscar_contenido_por_texto(texto: str, tramo: str) -> dict:
    """
    Busca contenidos curriculares en Neo4j usando búsqueda full-text semántica.
    Ideal para validar una actividad de planificación existente: dado el texto de
    una actividad (contenido + meta + plan), devuelve los nodos del programa oficial
    que mejor coinciden (Competencia, Contenido, Criterio de Logro, Tramo).

    Use this tool when the user asks to validate an existing activity or wants to
    find curriculum content by free text description.

    Args:
        texto (str): Texto libre de la actividad a buscar (ej: "escritura selección del tema").
        tramo (str): Tramo educativo para filtrar (ej: "Tramo 3"). Usar "" para buscar en todos.

    Returns:
        dict: Diccionario con 'status' y 'resultados' (lista de matches con CE, contenido, criterio, tramo).
    """
    print(f"\n[TOOL buscar_contenido_por_texto] Texto: '{texto[:60]}' | Tramo: '{tramo}'")

    cypher_fulltext = """
    CALL db.index.fulltext.queryNodes("contenido_ft", $texto) YIELD node AS cont, score
    WHERE cont:Contenido
    MATCH (eje:Eje)-[:TIENE_CONTENIDO]->(cont)
    MATCH (uc:UnidadCurricular)-[:TIENE_EJE]->(eje)
    MATCH (tr:Tramo)-[:TIENE_ESPACIO]->(:Espacio)-[:TIENE_UNIDAD]->(uc)
    WHERE $tramo = "" OR toLower(tr.nombre) CONTAINS toLower($tramo)
    OPTIONAL MATCH (uc)-[:DEFINE_CE]->(ce:CompetenciaEspecifica)
    OPTIONAL MATCH (cont)-[:TRABAJA_CE]->(ce2:CompetenciaEspecifica)
    WITH cont, score, eje, uc, tr,
         coalesce(ce2, ce) AS ce_match
    OPTIONAL MATCH (ce_match)-[:CONTRIBUYE_A]->(cg:CompetenciaGeneral)
    OPTIONAL MATCH (uc)-[:SE_EVALUA_CON]->(crit:CriterioDeLogro)
    RETURN
      ce_match.codigo      AS ce_id,
      ce_match.descripcion AS ce_enunciado,
      cont.descripcion     AS contenido,
      crit.descripcion     AS criterio,
      tr.nombre            AS tramo,
      uc.nombre            AS unidad,
      uc.espacio           AS espacio,
      cont.pagina          AS pagina,
      cont.pdf_fuente      AS pdf_fuente,
      score
    ORDER BY score DESC
    LIMIT 5
    """

    cypher_fallback = """
    MATCH (tr:Tramo)-[:TIENE_ESPACIO]->(:Espacio)-[:TIENE_UNIDAD]->(uc:UnidadCurricular)
          -[:TIENE_EJE]->(:Eje)-[:TIENE_CONTENIDO]->(cont:Contenido)
    WHERE toLower(cont.descripcion) CONTAINS toLower($texto)
      AND ($tramo = "" OR toLower(tr.nombre) CONTAINS toLower($tramo))
    OPTIONAL MATCH (cont)-[:TRABAJA_CE]->(ce:CompetenciaEspecifica)
    OPTIONAL MATCH (ce)-[:CONTRIBUYE_A]->(cg:CompetenciaGeneral)
    OPTIONAL MATCH (uc)-[:SE_EVALUA_CON]->(crit:CriterioDeLogro)
    RETURN
      ce.codigo          AS ce_id,
      ce.descripcion     AS ce_enunciado,
      cont.descripcion   AS contenido,
      crit.descripcion   AS criterio,
      tr.nombre          AS tramo,
      uc.nombre          AS unidad,
      uc.espacio         AS espacio,
      cont.pagina        AS pagina,
      cont.pdf_fuente    AS pdf_fuente,
      1.0                AS score
    ORDER BY cont.descripcion
    LIMIT 5
    """

    try:
        db_manager = Neo4jManager(uri=NEO4J_URI, user=NEO4J_USER, password=NEO4J_PASSWORD)
        if not db_manager.driver:
            return {"status": "error", "error_message": "No se pudo conectar con Neo4j."}

        with db_manager.driver.session() as session:
            try:
                result = session.run(cypher_fulltext, texto=texto, tramo=tramo)
                records = list(result)
                used_fulltext = True
            except Exception as ft_err:
                # Fulltext index missing or query error — use CONTAINS fallback
                print(f"[WARN] Fulltext query failed ({ft_err}), usando CONTAINS fallback.")
                result = session.run(cypher_fallback, texto=texto, tramo=tramo)
                records = list(result)
                used_fulltext = False

        db_manager.close()

        if not records:
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

        print(f"[OK] {len(resultados)} matches encontrados (fulltext={used_fulltext}).")
        return {"status": "success", "resultados": resultados}

    except Exception as e:
        print(f"[ERROR] {str(e)}")
        return {"status": "error", "error_message": str(e)}
