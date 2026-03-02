import sys
import os

# Add current directory to path
sys.path.append(os.getcwd())

from ingestion.extractor import IngestionProcessor

def test_ce_hierarchy_repetition():
    processor = IngestionProcessor()
    
    print("Testing Case: Sub-CE (CE1.1) appearing multiple times where parent (CE1) has no statement.")
    
    # Simulate hierarchical context
    processor.unidad_actual = "Danza"
    processor.tramo_actual = "Tramo 1 | Niveles 3, 4 y 5 años"
    
    # Case: CE1 with enunciado (optional, but let's test if it works normally)
    print("\n--- Should print TR1, CE1, CE1.1 ---")
    processor.process_line("CE1.", 12, "Bold", {"font": "Bold", "flags": 2})
    processor.process_line("Competencia sensoperceptiva", 12, "Bold", {"font": "Bold", "flags": 2})
    
    processor.process_line("CE1.1.", 12, "Bold", {"font": "Bold", "flags": 2})
    processor.process_line("Autoconciencia corporal: reconoce su respiración...", 12, "Regular", {"font": "Regular", "flags": 0})
    processor.guardar_ce()

    # Case: CE1 repeated (no statement), then CE1.2
    print("\n--- Should print CE1.2 (Not repeating CE1) ---")
    processor.process_line("CE1.", 12, "Bold", {"font": "Bold", "flags": 2}) # Parent appears again in PDF
    
    processor.process_line("CE1.2.", 12, "Bold", {"font": "Bold", "flags": 2})
    processor.process_line("Se vincula directamente con su entorno...", 12, "Regular", {"font": "Regular", "flags": 0})
    processor.guardar_ce()

    # Case: CE1 repeated (no statement), then CE1.3
    print("\n--- Should print CE1.3 (Not repeating CE1) ---")
    processor.process_line("CE1.", 12, "Bold", {"font": "Bold", "flags": 2})
    
    processor.process_line("CE1.3.", 12, "Bold", {"font": "Bold", "flags": 2})
    processor.process_line("Evoca imágenes...", 12, "Regular", {"font": "Regular", "flags": 0})
    processor.guardar_ce()

    # Case: Hierarchy change
    print("\n--- Should print NEW TRAMO and CE1 (Resetting tracker) ---")
    processor.b_tramo.append("Tramo 2 | Grados 1.º y 2.º")
    processor.flush_tramo()
    
    processor.process_line("CE1.", 12, "Bold", {"font": "Bold", "flags": 2})
    processor.process_line("Nueva competencia", 12, "Regular", {"font": "Regular", "flags": 0})
    processor.guardar_ce()

if __name__ == "__main__":
    test_ce_hierarchy_repetition()
