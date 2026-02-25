from ingestion.pdf_parser import PDFParser
from ingestion.extractor import IngestionProcessor

def main():
    pdf_path = "./pdfs/Compilación Programas 1er Ciclo - 2024.pdf"
    processor = IngestionProcessor()
    
    print(f"--- Extracción Total: Jerarquía Consolidada y Nodos Específicos ---")
    
    try:
        with PDFParser(pdf_path) as parser:
            for page_num, blocks in parser.iterate_pages(start_page=18):
                for b in blocks:
                    if "lines" not in b:
                        continue
                    
                    for line in b["lines"]:
                        spans = line["spans"]
                        if not spans:
                            continue
                            
                        texto_linea = " ".join([s["text"].strip() for s in spans if s["text"].strip()])
                        if not texto_linea:
                            continue
                        
                        span_first = spans[0]
                        span_last = spans[-1]
                        size = round(span_first["size"], 1)
                        font_first = span_first["font"]
                        
                        processor.process_line(texto_linea, size, font_first, span_last)

        processor.guardar_ce()
    finally:
        processor.close()

if __name__ == "__main__":
    main()
