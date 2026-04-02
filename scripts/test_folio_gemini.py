import os                                                       
from folio import run
from folio.adapters.json_adapter import JSONAdapter                                                
   
os.environ["APP_ENV"] = "prod"                                                                     
os.environ["GOOGLE_CLOUD_API_KEY"] = "tu-key"                   
                                                                                                     
storage = JSONAdapter("data/folio_ciclo2_test.json")                                               
result = run(                                                                                      
    "pdfs/Compilación Programas 2do Ciclo.pdf",                                                    
    storage=storage,                                                                               
)
print(f"Nodos: {result.nodos_creados}")                                                            
print(f"Fragmentos: {result.fragmentos_procesados}")                                               
if result.errores:                                                                                 
    print("Errores:")                                                                              
    for e in result.errores:                                                                       
        print(f"  - {e}")   