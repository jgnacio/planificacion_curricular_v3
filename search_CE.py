import fitz
import re

def extraer_con_deteccion_flexible(pdf_path):
    doc = fitz.open(pdf_path)
    print(f"--- Analizando: {pdf_path} ---")

    unidad_actual = "Desconocida"
    en_seccion_interes = False
    
    # Patrón para detectar CE (Competencia Específica)
    patron_ce = re.compile(r"^(CE\s?\d+)")

    for page_num in range(len(doc)):
        # Empezamos después de los índices
        if page_num < 20: continue 
        
        page = doc.load_page(page_num)
        blocks = page.get_text("dict")["blocks"]
        
        for b in blocks:
            if "lines" not in b: continue
            
            # Unimos el texto del bloque
            texto_bloque = " ".join(["".join([s["text"] for s in l["spans"]]) for l in b["lines"]]).strip()
            if not texto_bloque: continue

            # Extraemos formato del primer span
            span = b["lines"][0]["spans"][0]
            size = round(span["size"], 2)
            font = span["font"]

            # 1. Detectar UNIDAD CURRICULAR (Size 32.0 aprox)
            if 31.0 <= size <= 33.0:
                unidad_actual = texto_bloque
                en_seccion_interes = False # Resetear al cambiar de unidad
                print(f"\n[UC] {unidad_actual}")
                continue

            # 2. Detectar TÍTULOS DE SECCIÓN (Size 14.0)
            if 13.5 <= size <= 14.5:
                # Si el título menciona competencias, activamos el radar
                if "competencias" in texto_bloque.lower() and "específicas" in texto_bloque.lower():
                    en_seccion_interes = True
                    print(f"   (Entrando en sección: Competencias)")
                
                # Si el título menciona contenidos, también nos interesa
                elif "contenidos" in texto_bloque.lower():
                    en_seccion_interes = True
                    print(f"   (Entrando en sección: Contenidos)")
                
                # Si es otro título de tamaño 14 (como "Orientaciones"), apagamos el radar
                else:
                    en_seccion_interes = False
                continue

            # 3. CAPTURA DE DATOS (Size 10.0 a 12.0)
            if 10.0 <= size <= 12.5 and en_seccion_interes:
                # Si es una competencia (empieza con CE)
                if patron_ce.match(texto_bloque):
                    print(f"      [CE] {texto_bloque[:100]}...")
                
                # Si es un contenido (suele empezar con viñeta •)
                elif texto_bloque.startswith("•"):
                    print(f"      [CONTENIDO] {texto_bloque[:100]}...")

    doc.close()

# Ejecutar
extraer_con_deteccion_flexible("./pdfs/Compilación Programas 1er Ciclo - 2024.pdf")