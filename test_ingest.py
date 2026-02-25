import fitz

def extraer_jerarquia_final(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extracción Curricular: Espacio > Unidad > Tramo (Resolución de Primer Nodo) ---")
    
    # Buffers
    b_espacio = []
    b_unidad = []
    b_tramo = []

    for page_num in range(len(doc)):
        if page_num < 15: continue 
        
        page = doc.load_page(page_num)
        dict_text = page.get_text("dict")
        
        for block in dict_text["blocks"]:
            if "lines" not in block: continue
            
            for line in block["lines"]:
                texto_linea = " ".join([s["text"].strip() for s in line["spans"] if s["text"].strip()])
                if not texto_linea: continue
                    
                span = line["spans"][0]
                size = round(span["size"], 2)
                font = span["font"]

                # 1. DETECCIÓN DE ESPACIOS (37.82)
                if 37.0 <= size <= 38.5:
                    # Si ya había una unidad o tramo, esto marca un cambio total de área
                    b_espacio.append(texto_linea)
                    continue

                # 2. DETECCIÓN DE UNIDADES (32.0)
                elif (31.0 <= size <= 33.0) and "Bold" in font:
                    if "Perfiles" in texto_linea: continue
                    
                    # ANTES de guardar la unidad, imprimimos el espacio que estaba esperando
                    if b_espacio:
                        print(f"\n[ESPACIO] {' '.join(b_espacio).strip()}")
                        b_espacio = []
                    
                    b_unidad.append(texto_linea)
                    continue

                # 3. DETECCIÓN DE TRAMOS (24.0)
                elif 23.0 <= size <= 25.0:
                    # ANTES de guardar el tramo, imprimimos la unidad que estaba esperando
                    if b_unidad:
                        print(f"   └── [UNIDAD] {' '.join(b_unidad).strip()}")
                        b_unidad = []
                    
                    if texto_linea.startswith("Tramo") or b_tramo:
                        b_tramo.append(texto_linea)
                    continue
                
                # 4. CIERRE DE TRAMOS (Cuando el tamaño ya no es 24)
                else:
                    if b_tramo:
                        tramo_f = " ".join(b_tramo).strip()
                        if tramo_f.startswith("Tramo"):
                            print(f"       └── [TRAMO] {tramo_f}")
                        b_tramo = []

    doc.close()

extraer_jerarquia_final("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")