import fitz  # PyMuPDF

def buscar_y_analizar_texto(pdf_path, texto_buscado):
    doc = fitz.open(pdf_path)
    encontrado = False
    
    print(f"--- Buscando: '{texto_buscado}' ---")
    
    for page_num in range(len(doc)):
        page = doc.load_page(page_num)
        # Buscamos las instancias del texto
        text_instances = page.search_for(texto_buscado)
        
        if text_instances:
            encontrado = True
            # Extraemos el diccionario de la página para obtener el formato exacto
            dict_text = page.get_text("dict")
            
            for block in dict_text["blocks"]:
                if "lines" in block:
                    for line in block["lines"]:
                        for span in line["spans"]:
                            # Si el texto buscado está contenido en este span
                            if texto_buscado.lower() in span["text"].lower():
                                print(f"\n[!] COINCIDENCIA ENCONTRADA (Página {page_num + 1}):")
                                print(f"    Texto exacto: '{span['text']}'")
                                print(f"    Size: {round(span['size'], 2)}")
                                print(f"    Fuente: {span['font']}")
                                print(f"    Color (RGB): {span['color']}")
                                print(f"    Coordenadas (Rect): {span['bbox']}")
                                print(f"    Flags (Bold/Italic): {span['flags']}")
                                
    if not encontrado:
        print("No se encontró el texto exacto. Intenta con una frase más corta.")
    
    doc.close()

# --- USO DEL SCRIPT ---
# 1. Pon aquí la ruta a tu PDF
archivo = "./pdfs/Compilación Programas 1er Ciclo - 2024.pdf"

# 2. Pon aquí una frase que veas en el PDF y quieras identificar
# Ejemplo: "Competencias específicas de la unidad curricular" 
# o algún contenido como "Numeración natural"
frase_test = "Tramo 2 | Grados" 

buscar_y_analizar_texto(archivo, frase_test)