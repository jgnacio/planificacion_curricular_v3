import fitz

def extraer_unidades_y_tramos_corregido(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extracción de Estructura: Unidades y Tramos Oficiales ---")
    
    unidad_actual = ""
    buffer_unidad = []
    buffer_tramo = []
    
    for page_num in range(len(doc)):
        if page_num < 20: continue 
        
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            for line in b["lines"]:
                texto_linea = " ".join([s["text"].strip() for s in line["spans"] if s["text"].strip()])
                if not texto_linea: continue
                
                span = line["spans"][0]
                size = round(span["size"], 2)

                # 1. ACUMULACIÓN DE UNIDAD (Size 32.0)
                if 31.0 <= size <= 33.0:
                    buffer_unidad.append(texto_linea)
                    continue
                
                # 2. ACUMULACIÓN DE TRAMO (Size 24.0 e inicia con "Tramo")
                elif 23.0 <= size <= 25.0:
                    # Antes de procesar un tramo, debemos consolidar la unidad si hay algo en el buffer
                    if buffer_unidad:
                        unidad_actual = " ".join(buffer_unidad).strip()
                        print(f"\n[UNIDAD] {unidad_actual}")
                        buffer_unidad = []
                    
                    if texto_linea.startswith("Tramo") or buffer_tramo:
                        buffer_tramo.append(texto_linea)
                    continue
                
                # 3. CIERRE DE BUFFERS
                else:
                    # Si el buffer de unidad tiene algo y no vino un tramo (caso raro), lo cerramos
                    if buffer_unidad:
                        unidad_actual = " ".join(buffer_unidad).strip()
                        print(f"\n[UNIDAD] {unidad_actual}")
                        buffer_unidad = []

                    if buffer_tramo:
                        tramo_completo = " ".join(buffer_tramo).strip()
                        if tramo_completo.startswith("Tramo"):
                            print(f"   └── [TRAMO/GRADO] {tramo_completo}")
                        buffer_tramo = []

    doc.close()

# Ejecución
extraer_unidades_y_tramos_corregido("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")