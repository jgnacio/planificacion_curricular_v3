import fitz
import re

def extraer_tablas_planificacion(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Extracción de Tablas: Contenidos y Criterios ---")

    for page_num in range(20, len(doc)):
        page = doc.load_page(page_num)
        
        # 1. Buscamos las tablas en la página
        tabs = page.find_tables()
        
        if not tabs:
            continue

        for i, table in enumerate(tabs):
            # Obtenemos los datos de la tabla como una lista de listas
            rows = table.extract()
            
            # Limpieza básica de cabeceras (saltamos si la fila parece el encabezado)
            for row in rows:
                # Una tabla de planificación válida tiene al menos 2 o 3 columnas
                if len(row) < 2: continue
                
                # Limpiamos el texto de cada celda
                celdas = [str(c).replace('\n', ' ').strip() if c else "" for c in row]
                
                # Identificamos si la primera celda contiene códigos CE (vínculo)
                comp_vinculadas = re.findall(r"CE\s?\d+(?:\.\d+)*", celdas[0])
                
                if comp_vinculadas:
                    # En la mayoría de las materias de ANEP:
                    # Col 0: CEs | Col 1: Contenido | Col 2: Criterio
                    if len(celdas) >= 3:
                        ce_ids = ", ".join(comp_vinculadas)
                        contenido = celdas[1]
                        criterio = celdas[2]
                        
                        # Evitamos los encabezados literales
                        if "Contenidos" in contenido or "Criterios" in criterio:
                            continue
                            
                        print(f"\n[VÍNCULO DETECTADO]")
                        print(f"   CEs: {ce_ids}")
                        print(f"   CONTENIDO: {contenido[:60]}...")
                        print(f"   CRITERIO: {criterio[:60]}...")
                    
                    # Caso especial: Algunas tablas solo tienen 2 columnas (CEs y Contenido/Criterio mezclado)
                    elif len(celdas) == 2:
                        print(f"\n[TABLA 2 COL] CEs: {comp_vinculadas} | Info: {celdas[1][:90]}...")

    doc.close()

# Ejecución
extraer_tablas_planificacion("./pdfs/Compilación Programas 2do Ciclo.pdf")