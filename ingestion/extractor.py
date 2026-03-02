import re
import fitz
from typing import List, Optional
from .constants import *
from .utils import truncar, obtener_padre_ce, limpiar_texto
from .models import CompetenciaEspecifica
from .database import Neo4jManager

# ==========================================
# FUNCIÓN DE NORMALIZACIÓN (NUEVA)
# ==========================================
def normalizar_tramo(tramo_bruto):
    """
    Limpia las inconsistencias tipográficas de los PDFs de ANEP 
    para garantizar que Neo4j no duplique los nodos de 'Tramo'.
    """
    tramo_lower = tramo_bruto.lower()
    
    if "tramo 1" in tramo_lower:
        return "Tramo 1 | Niveles 3, 4 y 5 años"
    elif "tramo 2" in tramo_lower:
        return "Tramo 2 | Grados 1.º y 2.º"
    elif "tramo 3" in tramo_lower:
        return "Tramo 3 | Grados 3.º y 4.º"
    elif "tramo 4" in tramo_lower:
        return "Tramo 4 | Grados 5.º y 6.º"
    elif "tramo 5" in tramo_lower:
        return "Tramo 5 | Grados 7.º, 8.º y 9.º"
    elif "tramo 6" in tramo_lower:
        return "Tramo 6 | Grado 10.º"
    
    # Fallback por si llega algo rarísimo
    return tramo_bruto.strip()


class IngestionProcessor:
    def __init__(self, ciclo=""):
        self.ciclo_actual = ciclo
        # Memoria de Jerarquía
        self.espacio_actual = ""
        self.unidad_actual = ""
        self.tramo_actual = ""
        self.b_espacio = []
        self.b_unidad = []
        self.b_tramo = []
        
        # Memoria de CE
        self.ce_actual = None
        self.buffer_enunciado = []
        self.buffer_desarrollo = []
        self.bloqueo_tablas = False
        self.en_desarrollo_viñetas = False
        self.ultimo_id_impreso = ""
        self.ultimo_padre_impreso = ""

        # Neo4j
        self.db = Neo4jManager()

    def flush_espacio(self):
        if self.b_espacio:
            espacio_temp = " ".join(self.b_espacio).strip()
            if "guía de orientación para los talleres" in espacio_temp.lower():
                self.b_espacio = []
                return
            self.espacio_actual = espacio_temp
            self.unidad_actual = ""
            self.tramo_actual = ""
            print(f"\n[ESPACIO] {self.espacio_actual}")
            self.b_espacio = []
            self.ultimo_padre_impreso = ""

    def flush_unidad(self):
        if self.b_unidad:
            self.unidad_actual = " ".join(self.b_unidad).strip()
            self.tramo_actual = ""
            print(f"   [UNIDAD] {self.unidad_actual}")
            self.b_unidad = []
            self.ultimo_padre_impreso = ""

    def flush_tramo(self):
        if self.b_tramo:
            tramo_str = " ".join(self.b_tramo).strip()
            if tramo_str.lower().startswith("tramo"):
                # APLICAMOS NORMALIZADOR AQUÍ
                self.tramo_actual = normalizar_tramo(tramo_str)
                print(f"      [TRAMO] {self.tramo_actual}")
            self.b_tramo = []
            self.ultimo_padre_impreso = ""

    def guardar_ce(self):
        if self.ce_actual:
            enunciado = limpiar_texto(" ".join(self.buffer_enunciado))
            desarrollo = limpiar_texto(" ".join(self.buffer_desarrollo))
            
            mcn = ""
            ejes = ""
            
            match_mcn = PATRON_MCN.search(desarrollo)
            if match_mcn:
                desarrollo = match_mcn.group(1).strip()
                mcn = match_mcn.group(3).strip().rstrip('.')
            
            match_ejes = PATRON_EJES.search(desarrollo)
            if match_ejes:
                desarrollo = match_ejes.group(1).strip()
                ejes = match_ejes.group(3).strip().rstrip('.')
            
            match_mcn_en = PATRON_MCN.search(enunciado)
            if match_mcn_en:
                enunciado = match_mcn_en.group(1).strip()
                mcn = match_mcn_en.group(3).strip().rstrip('.')
                
            match_ejes_en = PATRON_EJES.search(enunciado)
            if match_ejes_en:
                enunciado = match_ejes_en.group(1).strip()
                ejes = match_ejes_en.group(3).strip().rstrip('.')
            
            texto_limpio_val = re.sub(r'CE\s?\d+(?:\.\d+)?', '', enunciado + desarrollo).replace(',', '').strip()
            if len(texto_limpio_val) > 5:
                nivel_pertenencia = "TRAMO" if self.tramo_actual else ("UNIDAD" if self.unidad_actual else "ESPACIO")
                indent = "         " if self.tramo_actual else ("      " if self.unidad_actual else "   ")
                
                padre = obtener_padre_ce(self.ce_actual)
                if padre and padre != self.ultimo_padre_impreso and padre != self.ultimo_id_impreso:
                    print(f"\n{indent}[ID] {padre} (Nivel: {nivel_pertenencia})")
                    self.ultimo_id_impreso = padre
                    self.ultimo_padre_impreso = padre
                
                if self.ce_actual != self.ultimo_id_impreso:
                    print(f"\n{indent}[ID] {self.ce_actual} (Nivel: {nivel_pertenencia})")
                    self.ultimo_id_impreso = self.ce_actual
                
                sub_indent = indent + "   "
                if padre: print(f"{sub_indent}[PADRE ID] {padre}")
                if enunciado: print(f"{sub_indent}[ENUNCIADO] {truncar(enunciado)}")
                if desarrollo: print(f"{sub_indent}[DESARROLLO] {truncar(desarrollo)}")
                if ejes: print(f"{sub_indent}[EJES] {truncar(ejes)}")
                if mcn: print(f"{sub_indent}[MCN] {truncar(mcn)}")

                unidad_prefix = self.unidad_actual.replace(" ", "_").upper()
                ce_id_unique = f"{unidad_prefix}_{self.ce_actual}"
                padre_unique = f"{unidad_prefix}_{padre}" if padre else None

                ce_obj = CompetenciaEspecifica(
                    id=ce_id_unique,
                    enunciado=enunciado,
                    desarrollo=desarrollo,
                    ejes=ejes,
                    mcn=mcn,
                    padre=padre_unique,
                    nivel_pertenencia=nivel_pertenencia
                )
                jerarquia = {
                    'ciclo': self.ciclo_actual,
                    'espacio': self.espacio_actual,
                    'unidad': self.unidad_actual,
                    'tramo': self.tramo_actual
                }
                self.db.save_competencia(ce_obj, jerarquia)
        
        self.ce_actual = None
        self.buffer_enunciado = []
        self.buffer_desarrollo = []
        self.en_desarrollo_viñetas = False

    def process_line(self, texto_linea, size, font_first, span_last, page_num=None):
        if page_num is not None:
            if not hasattr(self, 'unidad_por_pagina'):
                self.unidad_por_pagina = {}
            if self.unidad_actual:
                self.unidad_por_pagina[page_num] = self.unidad_actual

        texto_lower = texto_linea.lower()
        
        if SIZE_ESPACIO_MIN <= size <= SIZE_ESPACIO_MAX:
            self.guardar_ce()
            self.flush_tramo()
            self.flush_unidad()
            self.b_espacio.append(texto_linea)
            return

        elif (SIZE_UNIDAD_MIN <= size <= SIZE_UNIDAD_MAX) and "Bold" in font_first:
            if "perfiles" in texto_lower or "página" in texto_lower: return
            self.guardar_ce()
            self.flush_espacio()
            self.flush_tramo()
            self.b_unidad.append(texto_linea)
            return

        elif SIZE_TRAMO_MIN <= size <= SIZE_TRAMO_MAX:
            if texto_linea.startswith("Tramo") or self.b_tramo:
                self.guardar_ce()
                self.flush_espacio()
                self.flush_unidad()
                self.b_tramo.append(texto_linea)
            self.bloqueo_tablas = False
            return

        if size < SIZE_TITLE_THRESHOLD:
            self.flush_espacio()
            self.flush_unidad()
            self.flush_tramo()

        if any(keyword in texto_lower for keyword in ["contenidos, criterios de logro", "contenidos específicos", "orientaciones"]):
            self.guardar_ce()
            self.bloqueo_tablas = True
            return

        if self.bloqueo_tablas: return

        match_ce = PATRON_CE.match(texto_linea)
        es_negrita = "Bold" in span_last["font"] or span_last["flags"] & 2
        es_conciencia = "conciencia" in self.unidad_actual.lower() and "corporal" in self.unidad_actual.lower()
        
        if match_ce and (SIZE_CE_MIN <= size <= SIZE_CE_MAX):
            if texto_linea.count("CE") > 1: return 
                
            self.guardar_ce()
            self.ce_actual = match_ce.group(1).replace(" ", "").rstrip('.')
            resto = texto_linea[match_ce.end():].strip()
            self.en_desarrollo_viñetas = False
            
            if resto and resto != "," and not PATRON_CE.match(resto.replace(",", "").strip()):
                if es_conciencia:
                    if "•" in resto:
                        partes = resto.split("•", 1)
                        if partes[0].strip(): self.buffer_enunciado.append(partes[0].strip())
                        self.en_desarrollo_viñetas = True
                        self.buffer_desarrollo.append(partes[1].strip())
                    else:
                        self.buffer_enunciado.append(resto)
                else:
                    if es_negrita: self.buffer_enunciado.append(resto)
                    else: self.buffer_desarrollo.append(resto)
            return
        
        if self.ce_actual:
            if size > SIZE_CE_MAX:
                self.guardar_ce()
                return
                
            limpio = texto_linea.replace(",", "").strip()
            if not PATRON_CE.match(limpio): 
                if es_conciencia:
                    if "•" in texto_linea:
                        self.en_desarrollo_viñetas = True
                        self.buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                    elif self.en_desarrollo_viñetas:
                        self.buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                    else:
                        self.buffer_enunciado.append(texto_linea)
                else:
                    if es_negrita: self.buffer_enunciado.append(texto_linea)
                    else: self.buffer_desarrollo.append(texto_linea)

    def extract_tables(self, pdf_path):
        if "2do" in pdf_path.lower():
            self._extract_tables_inteligente(pdf_path)
        else:
            self._extract_tables_basico(pdf_path)

    def _extract_tables_basico(self, pdf_path):
        print(f"\n--- Extracción de Tablas Estándar (Contenidos y Criterios) para {pdf_path} ---")
        doc = fitz.open(pdf_path)
        
        for page_num in range(20, len(doc)):
            page = doc.load_page(page_num)
            tabs = page.find_tables()
            
            if not tabs:
                continue

            for table in tabs:
                rows = table.extract()
                for row in rows:
                    if len(row) < 2: continue
                    
                    celdas = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                    comp_vinculadas = re.findall(r"CE\s?\d+(?:\.\d+)*", celdas[0])
                    
                    if comp_vinculadas:
                        if len(celdas) >= 3:
                            contenido = celdas[1]
                            criterio = celdas[2]
                            
                            if "Contenidos" in contenido or "Criterios" in criterio:
                                continue
                                
                            unidad_para_pagina = getattr(self, 'unidad_por_pagina', {}).get(page_num, "")
                            unidad_prefix = unidad_para_pagina.replace(" ", "_").upper()

                            for ce_id in comp_vinculadas:
                                ce_id_clean = ce_id.replace(" ", "")
                                ce_id_unique = f"{unidad_prefix}_{ce_id_clean}" if unidad_prefix else ce_id_clean
                                print(f"  -> Salvando relación: {ce_id_unique} | Contenido: {contenido[:30]}... | Criterio: {criterio[:30]}...")
                                self.db.save_contenido_criterio(ce_id_unique, contenido, criterio)
                                
                        elif len(celdas) == 2:
                            pass

        doc.close()

    def _extract_tables_inteligente(self, pdf_path):
        doc = fitz.open(pdf_path)
        print(f"\n--- Extracción Dinámica: Rastreo, Fusión y Memoria Multijpágina (2do Ciclo) para {pdf_path} ---")

        espacio_actual = "Desconocido"
        unidad_actual = "Desconocida"
        tramo_actual = "Desconocido"
        grado_actual = "Desconocido"
        
        tabla_activa = False
        t_col_ce, t_col_cont, t_col_crit = -1, -1, -1
        t_span = 1
        memoria_macro = ""
        memoria_tema = ""
        
        patron_grado = re.compile(
            r"((?:[1-6]\s*(?:\.\s*)?(?:er|to|mo|vo|no|do|º|°|a)?|primer|segundo|tercer|cuarto|quinto|sexto)\s+grado|grados\s+[1-6].*?y.*?[1-6].*?|tramo\s+[1-6])", 
            re.IGNORECASE
        )
        
        for page_num in range(19, len(doc)):
            page = doc.load_page(page_num)
            
            blocks = page.get_text("dict")["blocks"]
            elementos = []
            
            for b in blocks:
                if "lines" in b:
                    bbox = b["bbox"]
                    texto = " ".join([s["text"] for l in b["lines"] for s in l["spans"]]).strip()
                    if not texto: continue
                    size = round(b["lines"][0]["spans"][0]["size"], 1) if b["lines"] and b["lines"][0]["spans"] else 12.0
                    font = b["lines"][0]["spans"][0]["font"] if b["lines"] and b["lines"][0]["spans"] else ""
                    elementos.append({"tipo": "texto", "y0": bbox[1], "texto": texto, "size": size, "font": font})
            
            tabs = page.find_tables()
            for tab in tabs:
                elementos.append({"tipo": "tabla", "y0": tab.bbox[1], "tabla": tab})
                
            elementos.sort(key=lambda x: x["y0"])
            
            for elem in elementos:
                if elem["tipo"] == "texto":
                    texto = elem["texto"]
                    size = elem["size"]
                    texto_lower = texto.lower()
                    
                    if 35.0 <= size <= 40.0:
                        espacio_actual = texto.replace('\n', ' ').strip()
                        tabla_activa = False 
                    elif 30.0 <= size <= 34.0 and "Bold" in elem["font"]:
                        if "perfil" not in texto_lower and "página" not in texto_lower:
                            unidad_actual = texto.replace('\n', ' ').strip()
                            grado_actual = "Desconocido"
                            tabla_activa = False
                    elif 23.0 <= size <= 26.0 and "tramo" in texto_lower:
                        tramo_bruto = texto.replace('\n', ' ').strip()
                        # APLICAMOS NORMALIZADOR AQUÍ TAMBIÉN
                        self.tramo_actual = normalizar_tramo(tramo_bruto)
                        tabla_activa = False
                    
                    match_grado = patron_grado.search(texto)
                    if match_grado:
                        if "contenido" in texto_lower or "evaluación" in texto_lower or size > 12.5 or "Bold" in elem["font"]:
                            grado_bruto = match_grado.group(1).strip()
                            
                            normalizaciones = {"Primer": "1.er", "Segundo": "2.do", "Tercer": "3.er", "Cuarto": "4.to", "Quinto": "5.to", "Sexto": "6.to"}
                            for letra, num in normalizaciones.items():
                                if letra.lower() in grado_bruto.lower():
                                    grado_bruto = re.sub(letra, num, grado_bruto, flags=re.IGNORECASE)
                            
                            if "tramo" in grado_bruto.lower():
                                grado_bruto = grado_bruto.capitalize()
                                if "grado" not in grado_actual.lower():
                                    grado_actual = grado_bruto
                            else:
                                grado_actual = re.sub(r'([1-6])\s*\.\s*(er|to|mo|vo|no|do)', r'\1.\2', grado_bruto, flags=re.IGNORECASE)
                        
                elif elem["tipo"] == "tabla":
                    rows = elem["tabla"].extract()
                    if not rows: continue
                    
                    col_ce, col_cont, col_crit = -1, -1, -1
                    r_idx_header = -1 
                    
                    # 1. Escaneo de columnas más flexible
                    for r_idx in range(min(3, len(rows))):
                        for c_idx, celda in enumerate(rows[r_idx]):
                            if celda:
                                texto_celda = str(celda).replace('\n', ' ').strip()
                                texto_celda_lower = texto_celda.lower()
                                
                                match_g = patron_grado.search(texto_celda)
                                if match_g: 
                                    g_temp = match_g.group(1).strip()
                                    if "tramo" in g_temp.lower():
                                        if "grado" not in grado_actual.lower():
                                            grado_actual = g_temp.capitalize()
                                    else:
                                        grado_actual = re.sub(r'([1-6])\s*\.\s*(er|to|mo|vo|no|do)', r'\1.\2', g_temp, flags=re.IGNORECASE)
                                
                                # Usamos palabras clave más cortas para evitar fallos por saltos de línea
                                if "competencia" in texto_celda_lower and col_ce == -1: col_ce = c_idx
                                if "criterio" in texto_celda_lower and col_crit == -1: col_crit = c_idx
                                if "contenidos específicos" in texto_celda_lower and col_cont == -1: 
                                    col_cont = c_idx
                                    r_idx_header = r_idx

                    es_continuacion = False
                    start_row = 0

                    if col_cont != -1:
                        tabla_activa = True
                        start_row = r_idx_header + 1
                        
                        # --- NUEVO CÁLCULO DE SPAN CON "CORTAFUEGOS" ---
                        span_contenidos = 1
                        
                        # Definimos la frontera máxima permitida para no comernos los Criterios
                        limite_derecha = len(rows[r_idx_header])
                        if col_crit != -1 and col_crit > col_cont: limite_derecha = min(limite_derecha, col_crit)
                        if col_ce != -1 and col_ce > col_cont: limite_derecha = min(limite_derecha, col_ce)

                        for i in range(col_cont + 1, limite_derecha):
                            # Verificamos si la columna está realmente vacía analizando las primeras 3 filas
                            es_vacia = True
                            for r in range(min(3, len(rows))):
                                if i < len(rows[r]) and rows[r][i]:
                                    val = str(rows[r][i]).replace('\n', ' ').strip().lower()
                                    if val and val != "none" and "profundización" not in val:
                                        es_vacia = False
                                        break
                            if es_vacia:
                                span_contenidos += 1
                            else:
                                break
                        # -----------------------------------------------
                                
                        t_col_cont = col_cont
                        t_col_ce = col_ce
                        t_col_crit = col_crit
                        t_span = span_contenidos
                        memoria_macro = ""
                        memoria_tema = ""
                        
                    elif tabla_activa and t_col_cont != -1:
                        # ES UNA CONTINUACIÓN (No tiene encabezados de Contenido, usa memoria)
                        
                        # --- CORTAFUEGOS VERTICAL ---
                        # Revisamos el texto de la primera fila para detectar si es una tabla intrusa
                        texto_fila_0 = " ".join([str(c).replace('\n', ' ') for c in rows[0] if c]).lower()
                        
                        if "criterio de logro" in texto_fila_0 or "criterios de logro" in texto_fila_0 or "orientaciones" in texto_fila_0:
                            tabla_activa = False
                            continue # Abortamos y saltamos esta tabla intrusa
                        # ----------------------------

                        es_continuacion = True
                        start_row = 0
                    else:
                        continue

                    unidad_prefix = unidad_actual.replace(" ", "_").upper()
                    if unidad_prefix == "DESCONOCIDA" and hasattr(self, 'unidad_por_pagina'):
                        unidad_para_pagina = self.unidad_por_pagina.get(page_num, "")
                        if unidad_para_pagina:
                            unidad_prefix = unidad_para_pagina.replace(" ", "_").upper()

                    print(f"\n[PÁGINA {page_num + 1}] TABLA DETECTADA {'(CONTINUACIÓN DE LA ANTERIOR)' if es_continuacion else ''}")
                    print(f"   [CONTEXTO] Unidad: {unidad_actual[:25]}... | Grado: {grado_actual}")
                    
                    contenidos_extraidos = []

                    if t_span >= 3:
                        bloques_fusionados = {} 
                        
                        for r_idx in range(start_row, len(rows)):
                            fila = rows[r_idx]
                            if t_col_cont + 2 >= len(fila): continue
                            
                            c0 = str(fila[t_col_cont]).replace('\n', ' ').strip() if fila[t_col_cont] else ""
                            c1 = str(fila[t_col_cont+1]).replace('\n', ' ').strip() if fila[t_col_cont+1] else ""
                            c2 = str(fila[t_col_cont+2]).replace('\n', ' ').strip() if fila[t_col_cont+2] else ""
                            
                            if c0 and c0.lower() != "none": memoria_macro = c0
                            if c1 and c1.lower() != "none": memoria_tema = c1
                            
                            if not c2 or c2.lower() == "none": continue 
                            
                            clave = (memoria_macro, memoria_tema)
                            if clave not in bloques_fusionados:
                                bloques_fusionados[clave] = {'textos': [], 'ces': set(), 'criterio': ""}
                                
                            c2_clean = re.sub(r'^[•\-\*]\s*', '', c2)
                            bloques_fusionados[clave]['textos'].append(c2_clean)
                            
                            if t_col_ce != -1 and t_col_ce < len(fila) and fila[t_col_ce]:
                                ces = re.findall(r"CE\s?\d+(?:\.\d+)*", str(fila[t_col_ce]))
                                bloques_fusionados[clave]['ces'].update(ces)
                                
                            if t_col_crit != -1 and t_col_crit < len(fila) and fila[t_col_crit]:
                                crit = str(fila[t_col_crit]).replace('\n', ' ').strip()
                                if crit and crit.lower() != "none":
                                    bloques_fusionados[clave]['criterio'] = crit

                        for (macro, tema), data in bloques_fusionados.items():
                            texto_unido = " ".join(data['textos'])
                            contenido_final = f"{macro} - {tema} : {texto_unido}"
                            criterio_final = data['criterio']
                            contenidos_extraidos.append(contenido_final)
                            
                            for ce_id in data['ces']:
                                ce_id_clean = ce_id.replace(" ", "")
                                ce_id_unique = f"{unidad_prefix}_{ce_id_clean}" if unidad_prefix else ce_id_clean
                                print(f"  -> Salvando relación: {ce_id_unique} | Contenido: {contenido_final[:30]}... | Criterio: {criterio_final[:30]}...")
                                
                                # GUARDADO CON GRADO
                                self.db.save_contenido_criterio(ce_id_unique, contenido_final, criterio_final, grado=grado_actual)

                    else:
                        for r_idx in range(start_row, len(rows)):
                            fila = rows[r_idx]
                            if t_col_cont < len(fila) and fila[t_col_cont]:
                                contenido = str(fila[t_col_cont]).replace('\n', ' ').strip()
                                if len(contenido) < 5 or "Contenidos" in contenido or contenido.lower() == "none": continue
                                contenido = re.sub(r'^[•\-\*]\s*', '', contenido)
                                
                                criterio = ""
                                if t_col_crit != -1 and t_col_crit < len(fila) and fila[t_col_crit]:
                                    criterio = str(fila[t_col_crit]).replace('\n', ' ').strip()
                                    if criterio.lower() == "none": criterio = ""
                                    
                                ces_vinculadas = []
                                if t_col_ce != -1 and t_col_ce < len(fila) and fila[t_col_ce]:
                                    ces_vinculadas = re.findall(r"CE\s?\d+(?:\.\d+)*", str(fila[t_col_ce]))
                                if not ces_vinculadas and fila[0]:
                                    ces_vinculadas = re.findall(r"CE\s?\d+(?:\.\d+)*", str(fila[0]))

                                contenidos_extraidos.append(contenido)

                                for ce_id in ces_vinculadas:
                                    ce_id_clean = ce_id.replace(" ", "")
                                    ce_id_unique = f"{unidad_prefix}_{ce_id_clean}" if unidad_prefix else ce_id_clean
                                    print(f"  -> Salvando relación: {ce_id_unique} | Contenido: {contenido[:30]}... | Criterio: {criterio[:30]}...")
                                    
                                    # GUARDADO CON GRADO
                                    self.db.save_contenido_criterio(ce_id_unique, contenido, criterio, grado=grado_actual)

                    print(f"   [CONTENIDOS EXTRAÍDOS ({len(contenidos_extraidos)})]:")
                    for cont in contenidos_extraidos[:3]:
                        print(f"      - {cont[:90]}...")
                    if len(contenidos_extraidos) > 3:
                        print(f"      ... (y {len(contenidos_extraidos) - 3} más)")

        doc.close()

    def close(self):
        if hasattr(self, 'db'):
            self.db.close()