import fitz
import re

def procesar_programa_fix_titulos_largos(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extracción Total: Jerarquía Consolidada y Nodos Específicos ---")
    
    patron_ce = re.compile(r"^(CE\s?\d+(?:\.\d+)*)\.?")
    patron_mcn = re.compile(r'(?i)(.*?)(Contribuyen?\s+al\s+desarrollo\s+.*?MCN\s*:?\s*)(.*)')
    patron_ejes = re.compile(r'(?i)(.*?)(Ejes\s+(?:temáticos|o\s+dominios\s+a\s+desarrollar)\s*:?\s*)(.*)')
    
    # Memoria de Jerarquía
    espacio_actual = ""
    unidad_actual = ""
    tramo_actual = ""
    b_espacio = []
    b_unidad = []
    b_tramo = []
    
    # Memoria de CE
    ce_actual = None
    buffer_enunciado = []
    buffer_desarrollo = []
    bloqueo_tablas = False
    en_desarrollo_viñetas = False

    def truncar(texto, limite=45):
        return f"{texto[:limite]}..." if len(texto) > limite else texto

    def obtener_padre_ce(codigo_ce):
        if '.' in codigo_ce:
            return codigo_ce.rsplit('.', 1)[0]
        return None

    # --- SISTEMA DE VACIADO EN CASCADA CORREGIDO ---
    def flush_espacio():
        nonlocal espacio_actual, b_espacio, unidad_actual, tramo_actual
        if b_espacio:
            espacio_actual = " ".join(b_espacio).strip()
            # Al consolidar un nuevo Espacio, borramos la memoria de las unidades y tramos viejos
            unidad_actual = ""
            tramo_actual = ""
            print(f"\n[ESPACIO] {espacio_actual}")
            b_espacio = []

    def flush_unidad():
        nonlocal unidad_actual, b_unidad, tramo_actual
        if b_unidad:
            unidad_actual = " ".join(b_unidad).strip()
            # Al consolidar una nueva Unidad, borramos la memoria del tramo viejo
            tramo_actual = ""
            print(f"   [UNIDAD] {unidad_actual}")
            b_unidad = []

    def flush_tramo():
        nonlocal tramo_actual, b_tramo
        if b_tramo:
            tramo_str = " ".join(b_tramo).strip()
            if tramo_str.startswith("Tramo"):
                tramo_actual = tramo_str
                print(f"      [TRAMO] {tramo_actual}")
            b_tramo = []

    def guardar_ce():
        nonlocal ce_actual, buffer_enunciado, buffer_desarrollo, en_desarrollo_viñetas
        if ce_actual:
            enunciado = re.sub(r'-\s+', '', " ".join(buffer_enunciado).strip())
            desarrollo = re.sub(r'-\s+', '', " ".join(buffer_desarrollo).strip())
            
            mcn = ""
            ejes = ""
            
            match_mcn = patron_mcn.search(desarrollo)
            if match_mcn:
                desarrollo = match_mcn.group(1).strip()
                mcn = match_mcn.group(3).strip().rstrip('.')
            
            match_ejes = patron_ejes.search(desarrollo)
            if match_ejes:
                desarrollo = match_ejes.group(1).strip()
                ejes = match_ejes.group(3).strip().rstrip('.')
            
            match_mcn_en = patron_mcn.search(enunciado)
            if match_mcn_en:
                enunciado = match_mcn_en.group(1).strip()
                mcn = match_mcn_en.group(3).strip().rstrip('.')
                
            match_ejes_en = patron_ejes.search(enunciado)
            if match_ejes_en:
                enunciado = match_ejes_en.group(1).strip()
                ejes = match_ejes_en.group(3).strip().rstrip('.')
            
            texto_limpio_val = re.sub(r'CE\s?\d+(?:\.\d+)?', '', enunciado + desarrollo).replace(',', '').strip()
            if len(texto_limpio_val) > 5:
                nivel_pertenencia = "TRAMO" if tramo_actual else ("UNIDAD" if unidad_actual else "ESPACIO")
                indent = "         " if tramo_actual else ("      " if unidad_actual else "   ")
                
                print(f"\n{indent}[ID] {ce_actual} (Nivel: {nivel_pertenencia})")
                
                sub_indent = indent + "   "
                padre = obtener_padre_ce(ce_actual)
                if padre: print(f"{sub_indent}[PADRE] {padre} (Nodo Hijo)")
                if enunciado: print(f"{sub_indent}[ENUNCIADO] {truncar(enunciado)}")
                if desarrollo: print(f"{sub_indent}[DESARROLLO] {truncar(desarrollo)}")
                if ejes: print(f"{sub_indent}[EJES] {truncar(ejes)}")
                if mcn: print(f"{sub_indent}[MCN] {truncar(mcn)}")
        
        ce_actual = None
        buffer_enunciado = []
        buffer_desarrollo = []
        en_desarrollo_viñetas = False

    for page_num in range(20, len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            for line in b["lines"]:
                texto_linea = " ".join([s["text"].strip() for s in line["spans"] if s["text"].strip()])
                if not texto_linea: continue
                
                span_first = line["spans"][0]
                span_last = line["spans"][-1]
                size = round(span_first["size"], 1)
                texto_lower = texto_linea.lower()
                font_first = span_first["font"]
                
                # --- MÁQUINA DE JERARQUÍA CORREGIDA ---
                if 37.0 <= size <= 38.5:
                    guardar_ce()
                    # Si detectamos un Espacio, consolidamos lo anterior, PERO NO vaciamos el espacio mismo
                    flush_tramo()
                    flush_unidad()
                    b_espacio.append(texto_linea)
                    continue

                elif (31.0 <= size <= 33.0) and "Bold" in font_first:
                    if "perfiles" in texto_lower or "página" in texto_lower: continue
                    guardar_ce()
                    # Si detectamos una Unidad, el Espacio ya terminó. Lo consolidamos.
                    flush_espacio()
                    flush_tramo()
                    b_unidad.append(texto_linea)
                    continue

                elif 23.0 <= size <= 25.0:
                    if texto_linea.startswith("Tramo") or b_tramo:
                        guardar_ce()
                        # Si detectamos un Tramo, la Unidad y el Espacio ya terminaron.
                        flush_espacio()
                        flush_unidad()
                        b_tramo.append(texto_linea)
                    bloqueo_tablas = False
                    continue

                # Cuando el texto baja al cuerpo normal (< 23), significa que los títulos ya terminaron.
                # Aquí consolidamos todo lo que haya quedado en los buffers.
                if size < 23.0:
                    flush_espacio()
                    flush_unidad()
                    flush_tramo()

                # --- CONTROL ANTI-TABLAS ---
                if "contenidos, criterios de logro" in texto_lower or "contenidos específicos" in texto_lower or "orientaciones" in texto_lower:
                    guardar_ce()
                    bloqueo_tablas = True
                    continue

                if bloqueo_tablas: continue

                # --- MÁQUINA DE COMPETENCIAS ---
                match_ce = patron_ce.match(texto_linea)
                es_negrita = "Bold" in span_last["font"] or span_last["flags"] & 2
                es_conciencia = "conciencia" in unidad_actual.lower() and "corporal" in unidad_actual.lower()
                
                # INICIO DE CE
                if match_ce and (10.0 <= size <= 13.5):
                    if texto_linea.count("CE") > 1: continue 
                        
                    guardar_ce()
                    ce_actual = match_ce.group(1).replace(" ", "").rstrip('.')
                    resto = texto_linea[match_ce.end():].strip()
                    en_desarrollo_viñetas = False
                    
                    if resto and resto != "," and not patron_ce.match(resto.replace(",", "").strip()):
                        if es_conciencia:
                            if "•" in resto:
                                partes = resto.split("•", 1)
                                if partes[0].strip(): buffer_enunciado.append(partes[0].strip())
                                en_desarrollo_viñetas = True
                                buffer_desarrollo.append(partes[1].strip())
                            else:
                                buffer_enunciado.append(resto)
                        else:
                            if es_negrita: buffer_enunciado.append(resto)
                            else: buffer_desarrollo.append(resto)
                    continue
                
                # ACUMULACIÓN EN CE ACTUAL
                if ce_actual:
                    if size > 13.5:
                        guardar_ce()
                        continue
                        
                    limpio = texto_linea.replace(",", "").strip()
                    if not patron_ce.match(limpio): 
                        if es_conciencia:
                            if "•" in texto_linea:
                                en_desarrollo_viñetas = True
                                buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                            elif en_desarrollo_viñetas:
                                buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                            else:
                                buffer_enunciado.append(texto_linea)
                        else:
                            if es_negrita: buffer_enunciado.append(texto_linea)
                            else: buffer_desarrollo.append(texto_linea)

    guardar_ce()
    doc.close()

procesar_programa_fix_titulos_largos("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")