import os
import re
import fitz
from typing import List, Optional
from .constants import *
from .utils import truncar, obtener_padre_ce, limpiar_texto, normalizar_prefix
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
            unidad_bruta = " ".join(self.b_unidad).strip()
            # Eliminar subtítulos entre paréntesis para unificar variantes del mismo nombre
            self.unidad_actual = re.sub(r'\s*\(.*?\)', '', unidad_bruta).strip()
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

                unidad_prefix = normalizar_prefix(self.unidad_actual)
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
            if not hasattr(self, 'tramo_por_pagina'):
                self.tramo_por_pagina = {}
            if self.unidad_actual:
                self.unidad_por_pagina[page_num] = self.unidad_actual
            if self.tramo_actual:
                self.tramo_por_pagina[page_num] = self.tramo_actual

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
            if not self.espacio_actual and page_num is not None:
                if not hasattr(self, '_paginas_sin_jerarquia'):
                    self._paginas_sin_jerarquia = set()
                if page_num not in self._paginas_sin_jerarquia:
                    self._paginas_sin_jerarquia.add(page_num)
                    print(f"  [⚠️ SIN JERARQUÍA] Página {page_num + 1}: texto sin Espacio detectado (size={size}, font='{font_first}'): '{texto_linea[:60]}'")

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

                # Detectar columnas por header en lugar de asumir índices fijos
                col_cont = 1
                col_crit = 2
                seccion_actual = ""
                for r_idx in range(min(3, len(rows))):
                    for c_idx, celda in enumerate(rows[r_idx]):
                        if not celda: continue
                        texto = str(celda).replace('\n', ' ').strip().lower()
                        if "contenidos" in texto and "estructurante" not in texto:
                            col_cont = c_idx
                        if "criterio" in texto:
                            col_crit = c_idx

                for row in rows:
                    if len(row) < 2: continue

                    # Aplanar para detectar CEs y criterio, pero preservar el bloque de contenido
                    celdas_planas = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                    fila_completa = " ".join(celdas_planas)
                    comp_vinculadas = re.findall(r"CE\s?\d+(?:\.\d+)*", fila_completa)
                    criterio = celdas_planas[col_crit] if col_crit < len(celdas_planas) else ""

                    if col_cont >= len(row) or not row[col_cont]:
                        continue

                    unidad_para_pagina = getattr(self, 'unidad_por_pagina', {}).get(page_num, "")
                    tramo_para_pagina = getattr(self, 'tramo_por_pagina', {}).get(page_num, "")
                    unidad_prefix = normalizar_prefix(unidad_para_pagina)

                    # Preservar saltos de línea para atomizar el bloque de contenido
                    contenido_raw = str(row[col_cont]).strip()
                    lineas = [l.strip() for l in contenido_raw.split('\n') if l.strip()]

                    seccion_path = seccion_actual
                    items_guardados = 0
                    item_buffer = []

                    def _flush_item(buf, seccion, ces, crit, unidad_pfx, tramo_pag, pag_num=None, pdf_src=None):
                        if not buf: return 0
                        item = ' '.join(buf).strip()
                        if len(item) < 5: return 0
                        contenido_final = f"{seccion}: {item}" if seccion else item
                        guardados = 0
                        if ces:
                            for ce_id in ces:
                                ce_id_unique = f"{unidad_pfx}_{ce_id.replace(' ', '')}" if unidad_pfx else ce_id.replace(' ', '')
                                print(f"  -> {ce_id_unique} | {contenido_final[:60]}...")
                                self.db.save_contenido_criterio(ce_id_unique, contenido_final, crit, tramo=tramo_pag, pagina=pag_num, pdf_fuente=pdf_src)
                                guardados += 1
                        else:
                            ce_id_unique = f"{unidad_pfx}_SIN_CE" if unidad_pfx else "SIN_CE"
                            print(f"  -> [SIN CE] {ce_id_unique} | {contenido_final[:60]}...")
                            self.db.save_contenido_criterio(ce_id_unique, contenido_final, crit, tramo=tramo_pag, pagina=pag_num, pdf_fuente=pdf_src)
                            guardados += 1
                        return guardados

                    for linea in lineas:
                        if not linea or len(linea) < 3: continue
                        if "Contenidos" in linea or "Criterios" in linea: continue

                        es_header = linea == linea.upper() and linea != linea.lower() and not linea.startswith('•')
                        es_bullet = linea.startswith('•') or linea.startswith('-') or linea.startswith('*')

                        _pdf_src = os.path.basename(pdf_path)
                        _pag = page_num + 1
                        if es_header:
                            items_guardados += _flush_item(item_buffer, seccion_path, comp_vinculadas, criterio, unidad_prefix, tramo_para_pagina, pag_num=_pag, pdf_src=_pdf_src)
                            item_buffer = []
                            print(f"  [🔍 SECCIÓN] Página {_pag}: '{linea}'")
                            seccion_path = linea
                        elif es_bullet:
                            items_guardados += _flush_item(item_buffer, seccion_path, comp_vinculadas, criterio, unidad_prefix, tramo_para_pagina, pag_num=_pag, pdf_src=_pdf_src)
                            item_buffer = [re.sub(r'^[•\-\*]\s*', '', linea).strip()]
                        else:
                            # Línea de continuación del ítem anterior
                            item_buffer.append(linea)

                    # Flush del último ítem
                    items_guardados += _flush_item(item_buffer, seccion_path, comp_vinculadas, criterio, unidad_prefix, tramo_para_pagina, pag_num=page_num + 1, pdf_src=os.path.basename(pdf_path))

                    if items_guardados == 0 and any(len(l) > 5 for l in lineas):
                        # Fallback: guardar el bloque completo si no se extrajo ningún ítem atómico
                        contenido_bloque = celdas_planas[col_cont]
                        if contenido_bloque and len(contenido_bloque) >= 3:
                            ce_id_unique = f"{unidad_prefix}_{comp_vinculadas[0].replace(' ', '')}" if comp_vinculadas else f"{unidad_prefix}_SIN_CE"
                            self.db.save_contenido_criterio(ce_id_unique, contenido_bloque, criterio, tramo=tramo_para_pagina, pagina=page_num + 1, pdf_fuente=os.path.basename(pdf_path))

                    seccion_actual = seccion_path  # propagar sección entre filas

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
                            unidad_bruta = texto.replace('\n', ' ').strip()
                            unidad_actual = re.sub(r'\s*\(.*?\)', '', unidad_bruta).strip()
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
                        
                        # --- CÁLCULO DE SPAN ---
                        # Frontera máxima: la columna CE o Criterio (lo que esté más a la izquierda)
                        limite_derecha = len(rows[r_idx_header])
                        if col_crit != -1 and col_crit > col_cont: limite_derecha = min(limite_derecha, col_crit)
                        if col_ce != -1 and col_ce > col_cont: limite_derecha = min(limite_derecha, col_ce)

                        cols_entre = limite_derecha - col_cont  # cuántas columnas de contenido hay

                        if cols_entre >= 3:
                            # Tabla jerárquica: macro / sub-sección / ítem (ej: Lengua Española 2do Ciclo)
                            span_contenidos = cols_entre
                        else:
                            # Tabla simple o con columnas vacías de relleno
                            span_contenidos = 1
                            for i in range(col_cont + 1, limite_derecha):
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

                    unidad_prefix = normalizar_prefix(unidad_actual)
                    if unidad_prefix == "DESCONOCIDA" and hasattr(self, 'unidad_por_pagina'):
                        unidad_para_pagina = self.unidad_por_pagina.get(page_num, "")
                        if unidad_para_pagina:
                            unidad_prefix = normalizar_prefix(unidad_para_pagina)

                    print(f"\n[PÁGINA {page_num + 1}] TABLA DETECTADA {'(CONTINUACIÓN DE LA ANTERIOR)' if es_continuacion else ''}")
                    print(f"   [CONTEXTO] Unidad: {unidad_actual[:25]}... | Grado: {grado_actual}")
                    
                    contenidos_extraidos = []

                    if t_span >= 3:
                        # Guardar cada ítem de contenido de forma atómica (una fila = un nodo Contenido)
                        for r_idx in range(start_row, len(rows)):
                            fila = rows[r_idx]
                            if t_col_cont + 2 >= len(fila): continue

                            c0 = str(fila[t_col_cont]).replace('\n', ' ').strip() if fila[t_col_cont] else ""
                            c1 = str(fila[t_col_cont+1]).replace('\n', ' ').strip() if fila[t_col_cont+1] else ""
                            c2 = str(fila[t_col_cont+2]).replace('\n', ' ').strip() if fila[t_col_cont+2] else ""

                            # Actualizar sección y sub-sección en memoria
                            if c0 and c0.lower() not in ("none", "") and not c0.startswith("Contenidos"):
                                memoria_macro = c0
                            if c1 and c1.lower() not in ("none", ""):
                                memoria_tema = c1

                            # c2 es el ítem atómico; si está vacío, es una fila de sección, saltar
                            if not c2 or c2.lower() == "none" or len(c2) < 3: continue

                            # Construir label jerárquico: "MACRO - Sub-sección: ítem"
                            partes = [p for p in [memoria_macro, memoria_tema] if p]
                            prefijo = " - ".join(partes)
                            item_limpio = re.sub(r'^[•\-\*]\s*', '', c2)
                            contenido_final = f"{prefijo}: {item_limpio}" if prefijo else item_limpio

                            # CEs y criterio de esta fila específica
                            ces_fila = []
                            if t_col_ce != -1 and t_col_ce < len(fila) and fila[t_col_ce]:
                                ces_fila = re.findall(r"CE\s?\d+(?:\.\d+)*", str(fila[t_col_ce]))

                            criterio_fila = ""
                            if t_col_crit != -1 and t_col_crit < len(fila) and fila[t_col_crit]:
                                crit_raw = str(fila[t_col_crit]).replace('\n', ' ').strip()
                                if crit_raw.lower() != "none":
                                    criterio_fila = crit_raw

                            contenidos_extraidos.append(contenido_final)

                            if ces_fila:
                                for ce_id in ces_fila:
                                    ce_id_unique = f"{unidad_prefix}_{ce_id.replace(' ', '')}" if unidad_prefix else ce_id.replace(' ', '')
                                    print(f"  -> {ce_id_unique} | {contenido_final[:60]}...")
                                    self.db.save_contenido_criterio(ce_id_unique, contenido_final, criterio_fila, grado=grado_actual, tramo=self.tramo_actual, pagina=page_num + 1, pdf_fuente=os.path.basename(pdf_path))
                            else:
                                ce_id_unique = f"{unidad_prefix}_SIN_CE" if unidad_prefix else "SIN_CE"
                                print(f"  -> [SIN CE] {ce_id_unique} | {contenido_final[:60]}...")
                                self.db.save_contenido_criterio(ce_id_unique, contenido_final, criterio_fila, grado=grado_actual, tramo=self.tramo_actual, pagina=page_num + 1, pdf_fuente=os.path.basename(pdf_path))

                    else:
                        seccion_actual = ""
                        for r_idx in range(start_row, len(rows)):
                            fila = rows[r_idx]
                            if t_col_cont < len(fila) and fila[t_col_cont]:
                                contenido = str(fila[t_col_cont]).replace('\n', ' ').strip()
                                if len(contenido) < 5 or "Contenidos" in contenido or contenido.lower() == "none": continue
                                if contenido == contenido.upper() and contenido != contenido.lower():
                                    print(f"  [🔍 SECCIÓN] Página {page_num + 1}, fila {r_idx}: '{contenido}'")
                                    seccion_actual = contenido
                                    continue
                                contenido = re.sub(r'^[•\-\*]\s*', '', contenido)
                                if seccion_actual:
                                    contenido = f"{seccion_actual}: {contenido}"
                                
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
                                    self.db.save_contenido_criterio(ce_id_unique, contenido, criterio, grado=grado_actual, tramo=self.tramo_actual, pagina=page_num + 1, pdf_fuente=os.path.basename(pdf_path))

                    print(f"   [CONTENIDOS EXTRAÍDOS ({len(contenidos_extraidos)})]:")
                    for cont in contenidos_extraidos[:3]:
                        print(f"      - {cont[:90]}...")
                    if len(contenidos_extraidos) > 3:
                        print(f"      ... (y {len(contenidos_extraidos) - 3} más)")

        doc.close()

    def close(self):
        if hasattr(self, 'db'):
            self.db.close()