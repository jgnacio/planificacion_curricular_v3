import glob
from pathlib import Path
from ingestion.pdf_parser import PDFParser
from ingestion.extractor import IngestionProcessor

def extract_ciclo(filename: str) -> str:
    name_lower = filename.lower()
    if "1er ciclo" in name_lower:
        return "1er Ciclo"
    elif "2do ciclo" in name_lower:
        return "2do Ciclo"
    return "Ciclo no identificado"

def main():
    pdfs_dir = Path("./pdfs")
    pdf_paths = list(pdfs_dir.glob("*.pdf"))
    
    print(f"--- Extracción Total: Jerarquía Consolidada y Nodos Específicos ---")
    print(f"Encontrados {len(pdf_paths)} PDFs para procesar.")
    
    for pdf_path in pdf_paths:
        ciclo = extract_ciclo(pdf_path.name)
        print(f"\n=======================================================")
        print(f"Procesando: {pdf_path.name} (Ciclo: {ciclo})")
        print(f"=======================================================\n")
        
        processor = IngestionProcessor(ciclo=ciclo)
        
        try:
            with PDFParser(str(pdf_path)) as parser:
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
