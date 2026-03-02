import fitz
import re

def extraer_contenidos_inteligente(pdf_path):
    doc = fitz.open(pdf_path)
    print("--- Extracción Dinámica: Rastreo, Fusión y Memoria Multijpágina ---")

    # 1. Variables de Memoria de Jerarquía
    espacio_actual = "Desconocido"
    unidad_actual = "Desconocida"
    tramo_actual = "Desconocido"
    grado_actual = "Desconocido"
    
    # 2. Variables de Memoria de Tabla (Para cruzar páginas)
    tabla_activa = False
    t_col_ce, t_col_cont, t_col_crit = -1, -1, -1
    t_span = 1
    memoria_macro = ""
    memoria_tema = ""
    
    # Regex súper flexible para lidiar con los superíndices rotos de los PDFs (Ej: "5.to", "5. to", "5º", "5 .to")
    patron_grado = re.compile(
        r"((?:[1-6]\s*(?:\.\s*)?(?:er|to|mo|vo|no|do|º|°|a)?|primer|segundo|tercer|cuarto|quinto|sexto)\s+grado|grados\s+[1-6].*?y.*?[1-6].*?|tramo\s+[1-6])", 
        re.IGNORECASE
    )
    
    for page_num in range(19, len(doc)): # Ajusta inicio según tu PDF
        page = doc.load_page(page_num)
        
        blocks = page.get_text("dict")["blocks"]
        elementos = []
        
        # Recolección
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
        
        # Procesamiento Top-Down
        for elem in elementos:
            if elem["tipo"] == "texto":
                texto = elem["texto"]
                size = elem["size"]
                texto_lower = texto.lower()
                
                # ACTUALIZAR JERARQUÍA (Si hay título nuevo, se rompe la memoria de la tabla)
                if 35.0 <= size <= 40.0:
                    espacio_actual = texto.replace('\n', ' ').strip()
                    tabla_activa = False 
                elif 30.0 <= size <= 34.0 and "Bold" in elem["font"]:
                    if "perfil" not in texto_lower and "página" not in texto_lower:
                        unidad_actual = texto.replace('\n', ' ').strip()
                        grado_actual = "Desconocido"
                        tabla_activa = False
                elif 23.0 <= size <= 26.0 and "tramo" in texto_lower:
                    tramo_actual = texto.replace('\n', ' ').strip()
                    tabla_activa = False
                
                # --- CAPTURAR GRADO PRE-TABLA ---
                match_grado = patron_grado.search(texto)
                if match_grado:
                    if "contenido" in texto_lower or "evaluación" in texto_lower or size > 12.5 or "Bold" in elem["font"]:
                        grado_bruto = match_grado.group(1).strip()
                        
                        # Normalizaciones
                        normalizaciones = {"Primer": "1.er", "Segundo": "2.do", "Tercer": "3.er", "Cuarto": "4.to", "Quinto": "5.to", "Sexto": "6.to"}
                        for letra, num in normalizaciones.items():
                            if letra.lower() in grado_bruto.lower():
                                grado_bruto = re.sub(letra, num, grado_bruto, flags=re.IGNORECASE)
                        
                        if "tramo" in grado_bruto.lower():
                            grado_bruto = grado_bruto.capitalize()
                            # Solo guardamos "Tramo" si no teníamos ya un Grado específico memorizado
                            if "grado" not in grado_actual.lower():
                                grado_actual = grado_bruto
                        else:
                            # Limpiar espacios raros del superíndice (ej: "5. to grado" -> "5.to grado")
                            grado_actual = re.sub(r'([1-6])\s*\.\s*(er|to|mo|vo|no|do)', r'\1.\2', grado_bruto, flags=re.IGNORECASE)
                    
            elif elem["tipo"] == "tabla":
                rows = elem["tabla"].extract()
                if not rows: continue
                
                col_ce, col_cont, col_crit = -1, -1, -1
                r_idx_header = -1 
                
                # Buscar encabezados solo en las primeras 3 filas (Búsqueda más flexible)
                for r_idx in range(min(3, len(rows))):
                    for c_idx, celda in enumerate(rows[r_idx]):
                        if celda:
                            texto_celda = str(celda).replace('\n', ' ').strip()
                            texto_celda_lower = texto_celda.lower()
                            
                            # Rescatar grado desde la cabecera
                            match_g = patron_grado.search(texto_celda)
                            if match_g: 
                                g_temp = match_g.group(1).strip()
                                if "tramo" in g_temp.lower():
                                    if "grado" not in grado_actual.lower():
                                        grado_actual = g_temp.capitalize()
                                else:
                                    grado_actual = re.sub(r'([1-6])\s*\.\s*(er|to|mo|vo|no|do)', r'\1.\2', g_temp, flags=re.IGNORECASE)
                            
                            # Palabras clave más cortas para evitar fallos por saltos de línea
                            if "competencia" in texto_celda_lower and col_ce == -1: col_ce = c_idx
                            if "criterio" in texto_celda_lower and col_crit == -1: col_crit = c_idx
                            if "contenidos específicos" in texto_celda_lower and col_cont == -1: 
                                col_cont = c_idx
                                r_idx_header = r_idx

                es_continuacion = False
                start_row = 0

                # =========================================================
                # LÓGICA DE CONTINUACIÓN MULTI-PÁGINA CON CORTAFUEGOS
                # =========================================================
                if col_cont != -1:
                    # TABLA NUEVA (Tiene encabezados de Contenidos)
                    tabla_activa = True
                    start_row = r_idx_header + 1
                    
                    # --- CORTAFUEGOS HORIZONTAL ---
                    # Calcula cuántas columnas abarca, pero frena si choca con Criterios o CEs
                    span_contenidos = 1
                    limite_derecha = len(rows[r_idx_header])
                    if col_crit != -1 and col_crit > col_cont: limite_derecha = min(limite_derecha, col_crit)
                    if col_ce != -1 and col_ce > col_cont: limite_derecha = min(limite_derecha, col_ce)

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
                    # ------------------------------
                            
                    # Guardar estructura en memoria global
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
                    # Tabla inservible, saltamos
                    continue

                # Continúa tu código normal de extracción...
                unidad_prefix = unidad_actual.replace(" ", "_").upper()
                print(f"\n[PÁGINA {page_num + 1}] TABLA DETECTADA {'(CONTINUACIÓN DE LA ANTERIOR)' if es_continuacion else ''}")
                print(f"   [CONTEXTO] Unidad: {unidad_actual[:25]}... | Grado: {grado_actual}")
                
                contenidos_extraidos = []

                # =================================================================
                # CASO A: TABLAS COMPLEJAS (3 SUB-COLUMNAS)
                # =================================================================
                if t_span >= 3:
                    bloques_fusionados = {} 
                    
                    for r_idx in range(start_row, len(rows)):
                        fila = rows[r_idx]
                        if t_col_cont + 2 >= len(fila): continue # Fila rota o mal detectada
                        
                        c0 = str(fila[t_col_cont]).replace('\n', ' ').strip() if fila[t_col_cont] else ""
                        c1 = str(fila[t_col_cont+1]).replace('\n', ' ').strip() if fila[t_col_cont+1] else ""
                        c2 = str(fila[t_col_cont+2]).replace('\n', ' ').strip() if fila[t_col_cont+2] else ""
                        
                        # Forward Fill (Utiliza la memoria si la celda viene vacía)
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
                            # self.db.save_contenido_criterio(...)

                # =================================================================
                # CASO B: TABLAS ESTÁNDAR (1 COLUMNA)
                # =================================================================
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
                                # self.db.save_contenido_criterio(...)

                print(f"   [CONTENIDOS EXTRAÍDOS ({len(contenidos_extraidos)})]:")
                for cont in contenidos_extraidos[:3]:
                    print(f"      - {cont[:90]}...")
                if len(contenidos_extraidos) > 3:
                    print(f"      ... (y {len(contenidos_extraidos) - 3} más)")

# Ejecución
extraer_contenidos_inteligente("../pdfs/Compilación Programas 2do Ciclo.pdf")