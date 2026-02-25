import fitz
import re

def extraer_ce_con_jerarquia(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extrayendo CE: Jerarquía Padre/Hijo y Detección Exacta de Enunciados ---")
    
    # Soporta CE1, CE 1, CE1.1, CE1.2.1
    patron_ce = re.compile(r"^(CE\s?\d+(?:\.\d+)*)\.?")
    patron_mcn = re.compile(r'(?i)(.*?)(Contribuyen?\s+al\s+desarrollo\s+.*?MCN\s*:?\s*)(.*)')
    patron_ejes = re.compile(r'(?i)(.*?)(Ejes\s+(?:temáticos|o\s+dominios\s+a\s+desarrollar)\s*:?\s*)(.*)')
    
    ce_actual = None
    buffer_enunciado = []
    buffer_desarrollo = []
    bloqueo_tablas = False

    def texto_es_valido(texto):
        texto_limpio = re.sub(r'CE\s?\d+(?:\.\d+)?', '', texto).replace(',', '').strip()
        return len(texto_limpio) > 5

    def truncar(texto, limite=50):
        """Mantiene la terminal limpia, ajustado a 35 para que sea legible"""
        return f"{texto[:limite]}..." if len(texto) > limite else texto

    def obtener_padre_ce(codigo_ce):
        """Calcula si es un sub-contenido y devuelve el ID del padre"""
        if '.' in codigo_ce:
            return codigo_ce.rsplit('.', 1)[0] # Ej: CE1.5 -> CE1
        return None

    def guardar_ce():
        nonlocal ce_actual, buffer_enunciado, buffer_desarrollo
        if ce_actual:
            enunciado = re.sub(r'-\s+', '', " ".join(buffer_enunciado).strip())
            desarrollo = re.sub(r'-\s+', '', " ".join(buffer_desarrollo).strip())
            
            mcn = ""
            ejes = ""
            
            # Separar MCN
            match_mcn = patron_mcn.search(desarrollo)
            if match_mcn:
                desarrollo = match_mcn.group(1).strip()
                mcn = match_mcn.group(3).strip().rstrip('.')
            
            # Separar Ejes
            match_ejes = patron_ejes.search(desarrollo)
            if match_ejes:
                desarrollo = match_ejes.group(1).strip()
                ejes = match_ejes.group(3).strip().rstrip('.')
            
            # Chequeo cruzado por si el PDF tiene errores de formato
            match_mcn_en = patron_mcn.search(enunciado)
            if match_mcn_en:
                enunciado = match_mcn_en.group(1).strip()
                mcn = match_mcn_en.group(3).strip().rstrip('.')
                
            match_ejes_en = patron_ejes.search(enunciado)
            if match_ejes_en:
                enunciado = match_ejes_en.group(1).strip()
                ejes = match_ejes_en.group(3).strip().rstrip('.')
            
            if texto_es_valido(enunciado + " " + desarrollo + " " + ejes + " " + mcn):
                print(f"\n[ID] {ce_actual}")
                
                # --- NUEVA LÓGICA DE JERARQUÍA ---
                padre = obtener_padre_ce(ce_actual)
                if padre:
                    print(f"   [PADRE] {padre} (Nodo Hijo)")
                
                if enunciado:
                    print(f"   [ENUNCIADO] {truncar(enunciado)}")
                if desarrollo:
                    print(f"   [DESARROLLO] {truncar(desarrollo)}")
                if ejes:
                    print(f"   [EJES] {truncar(ejes)}")
                if mcn:
                    print(f"   [MCN] {truncar(mcn)}")
        
        # Reset de la máquina de estados
        ce_actual = None
        buffer_enunciado = []
        buffer_desarrollo = []

    for page_num in range(20, len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            for line in b["lines"]:
                texto_linea = " ".join([s["text"].strip() for s in line["spans"] if s["text"].strip()])
                if not texto_linea: continue
                
                # Analizamos el primer span para el tamaño y el ÚLTIMO span para el formato del cuerpo
                span_first = line["spans"][0]
                span_last = line["spans"][-1]
                
                size = round(span_first["size"], 1)
                texto_lower = texto_linea.lower()
                
                # LÓGICA DE TRANSICIÓN: Determina si el texto después del código es negrita
                es_negrita_cuerpo = "Bold" in span_last["font"] or span_last["flags"] & 2

                # Control del Cerrojo Anti-Tablas
                if size >= 23.0:
                    guardar_ce()
                    bloqueo_tablas = False
                    continue

                if "contenidos, criterios de logro" in texto_lower or "contenidos específicos" in texto_lower or "orientaciones" in texto_lower:
                    guardar_ce()
                    bloqueo_tablas = True
                    continue

                if bloqueo_tablas: continue

                match_ce = patron_ce.match(texto_linea)
                
                # INICIO DE NUEVA COMPETENCIA
                if match_ce and (10.0 <= size <= 13.5):
                    if texto_linea.count("CE") > 1: continue 
                        
                    guardar_ce()
                    # Normalizamos el código para la base de datos (Ej: "CE 1.1." -> "CE1.1")
                    ce_actual = match_ce.group(1).replace(" ", "").rstrip('.')
                    
                    resto = texto_linea[match_ce.end():].strip()
                    if resto and resto != "," and not patron_ce.match(resto.replace(",", "").strip()):
                        if es_negrita_cuerpo:
                            buffer_enunciado.append(resto)
                        else:
                            # Si es CE1.5 (negrita) pero el resto es normal, viene directo aquí
                            buffer_desarrollo.append(resto)
                    continue
                
                # ACUMULACIÓN EN CE ACTUAL
                if ce_actual:
                    if size > 13.5:
                        guardar_ce()
                        continue
                        
                    limpio = texto_linea.replace(",", "").strip()
                    if not patron_ce.match(limpio): 
                        if es_negrita_cuerpo:
                            buffer_enunciado.append(texto_linea)
                        else:
                            buffer_desarrollo.append(texto_linea)

    guardar_ce()
    doc.close()

extraer_ce_con_jerarquia("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")