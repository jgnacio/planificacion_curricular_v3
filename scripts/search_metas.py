import fitz
import re

def extraer_metas_aprendizaje(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extrayendo Metas de Aprendizaje por Tramo ---")
    
    # Buffers para mantener el contexto
    unidad_actual = ""
    tramo_actual = ""
    buffer_metas = []
    capturando_metas = False

    for page_num in range(20, len(doc)):
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            for line in b["lines"]:
                texto_linea = " ".join([s["text"].strip() for s in line["spans"] if s["text"].strip()])
                if not texto_linea: continue
                
                span = line["spans"][0]
                size = round(span["size"], 1)
                texto_lower = texto_linea.lower()

                # 1. ACTUALIZACIÓN DE CONTEXTO (Para saber a qué pertenecen las metas)
                if 31.0 <= size <= 33.0:
                    unidad_actual = texto_linea
                    capturando_metas = False # Reset al cambiar unidad
                    continue
                
                if 23.0 <= size <= 25.0 and "tramo" in texto_lower:
                    tramo_actual = texto_linea
                    capturando_metas = False
                    continue

                # 2. DETECCIÓN DE INICIO DE METAS
                if "metas de aprendizaje" in texto_lower:
                    capturando_metas = True
                    buffer_metas = []
                    continue

                # 3. DETECCIÓN DE FIN DE SECCIÓN
                # Si estamos capturando metas y aparece un título de tabla o una CE, cerramos
                if capturando_metas:
                    if "contenidos" in texto_lower or "criterios de logro" in texto_lower or size > 13.5:
                        if buffer_metas:
                            meta_completa = " ".join(buffer_metas).strip()
                            meta_completa = re.sub(r'-\s+', '', meta_completa) # Limpiar cortes
                            print(f"\n[UNIDAD] {unidad_actual}")
                            print(f"   [TRAMO] {tramo_actual}")
                            print(f"      [META] {meta_completa[:100]}...")
                        
                        capturando_metas = False
                        buffer_metas = []
                        continue

                    # 4. ACUMULACIÓN DE CONTENIDO
                    # Limpiamos las viñetas si existen para que el texto sea puro
                    linea_limpia = texto_linea.lstrip("• ").strip()
                    buffer_metas.append(linea_limpia)

    doc.close()

# Ejecución
extraer_metas_aprendizaje("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")