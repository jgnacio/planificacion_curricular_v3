import re
from typing import List, Optional
from .constants import *
from .utils import truncar, obtener_padre_ce, limpiar_texto
from .models import CompetenciaEspecifica
from .database import Neo4jManager

class IngestionProcessor:
    def __init__(self, ciclo=""):
        self.ciclo_actual = ciclo
        # Memoria de Jerarquía
        self.espacio_actual = ""
        self.unidad_actual = ""
        self.tramo_actual = ""
        self.b_espacio = []
        self.b_unidad = []
        self.b_tramo = []
        
        # Memoria de CE
        self.ce_actual = None
        self.buffer_enunciado = []
        self.buffer_desarrollo = []
        self.bloqueo_tablas = False
        self.en_desarrollo_viñetas = False
        self.ultimo_id_impreso = ""
        self.ultimo_padre_impreso = ""

        # Neo4j
        self.db = Neo4jManager()

    def flush_espacio(self):
        if self.b_espacio:
            espacio_temp = " ".join(self.b_espacio).strip()
            if "guía de orientación para los talleres" in espacio_temp.lower():
                self.b_espacio = []
                return
            self.espacio_actual = espacio_temp
            self.unidad_actual = ""
            self.tramo_actual = ""
            print(f"\n[ESPACIO] {self.espacio_actual}")
            self.b_espacio = []
            self.ultimo_padre_impreso = ""

    def flush_unidad(self):
        if self.b_unidad:
            self.unidad_actual = " ".join(self.b_unidad).strip()
            self.tramo_actual = ""
            print(f"   [UNIDAD] {self.unidad_actual}")
            self.b_unidad = []
            self.ultimo_padre_impreso = ""

    def flush_tramo(self):
        if self.b_tramo:
            tramo_str = " ".join(self.b_tramo).strip()
            if tramo_str.startswith("Tramo"):
                self.tramo_actual = tramo_str
                print(f"      [TRAMO] {self.tramo_actual}")
            self.b_tramo = []
            self.ultimo_padre_impreso = ""

    def guardar_ce(self):
        if self.ce_actual:
            enunciado = limpiar_texto(" ".join(self.buffer_enunciado))
            desarrollo = limpiar_texto(" ".join(self.buffer_desarrollo))
            
            mcn = ""
            ejes = ""
            
            match_mcn = PATRON_MCN.search(desarrollo)
            if match_mcn:
                desarrollo = match_mcn.group(1).strip()
                mcn = match_mcn.group(3).strip().rstrip('.')
            
            match_ejes = PATRON_EJES.search(desarrollo)
            if match_ejes:
                desarrollo = match_ejes.group(1).strip()
                ejes = match_ejes.group(3).strip().rstrip('.')
            
            match_mcn_en = PATRON_MCN.search(enunciado)
            if match_mcn_en:
                enunciado = match_mcn_en.group(1).strip()
                mcn = match_mcn_en.group(3).strip().rstrip('.')
                
            match_ejes_en = PATRON_EJES.search(enunciado)
            if match_ejes_en:
                enunciado = match_ejes_en.group(1).strip()
                ejes = match_ejes_en.group(3).strip().rstrip('.')
            
            texto_limpio_val = re.sub(r'CE\s?\d+(?:\.\d+)?', '', enunciado + desarrollo).replace(',', '').strip()
            if len(texto_limpio_val) > 5:
                nivel_pertenencia = "TRAMO" if self.tramo_actual else ("UNIDAD" if self.unidad_actual else "ESPACIO")
                indent = "         " if self.tramo_actual else ("      " if self.unidad_actual else "   ")
                
                padre = obtener_padre_ce(self.ce_actual)
                if padre and padre != self.ultimo_padre_impreso and padre != self.ultimo_id_impreso:
                    print(f"\n{indent}[ID] {padre} (Nivel: {nivel_pertenencia})")
                    self.ultimo_id_impreso = padre
                    self.ultimo_padre_impreso = padre
                
                if self.ce_actual != self.ultimo_id_impreso:
                    print(f"\n{indent}[ID] {self.ce_actual} (Nivel: {nivel_pertenencia})")
                    self.ultimo_id_impreso = self.ce_actual
                
                sub_indent = indent + "   "
                if padre: print(f"{sub_indent}[PADRE ID] {padre}")
                if enunciado: print(f"{sub_indent}[ENUNCIADO] {truncar(enunciado)}")
                if desarrollo: print(f"{sub_indent}[DESARROLLO] {truncar(desarrollo)}")
                if ejes: print(f"{sub_indent}[EJES] {truncar(ejes)}")
                if mcn: print(f"{sub_indent}[MCN] {truncar(mcn)}")

                # Persistence to Neo4j
                ce_obj = CompetenciaEspecifica(
                    id=self.ce_actual,
                    enunciado=enunciado,
                    desarrollo=desarrollo,
                    ejes=ejes,
                    mcn=mcn,
                    padre=padre,
                    nivel_pertenencia=nivel_pertenencia
                )
                jerarquia = {
                    'ciclo': self.ciclo_actual,
                    'espacio': self.espacio_actual,
                    'unidad': self.unidad_actual,
                    'tramo': self.tramo_actual
                }
                self.db.save_competencia(ce_obj, jerarquia)
        
        self.ce_actual = None
        self.buffer_enunciado = []
        self.buffer_desarrollo = []
        self.en_desarrollo_viñetas = False

    def process_line(self, texto_linea, size, font_first, span_last):
        texto_lower = texto_linea.lower()
        
        # --- MÁQUINA DE JERARQUÍA ---
        if SIZE_ESPACIO_MIN <= size <= SIZE_ESPACIO_MAX:
            self.guardar_ce()
            self.flush_tramo()
            self.flush_unidad()
            self.b_espacio.append(texto_linea)
            return

        elif (SIZE_UNIDAD_MIN <= size <= SIZE_UNIDAD_MAX) and "Bold" in font_first:
            if "perfiles" in texto_lower or "página" in texto_lower: return
            self.guardar_ce()
            self.flush_espacio()
            self.flush_tramo()
            self.b_unidad.append(texto_linea)
            return

        elif SIZE_TRAMO_MIN <= size <= SIZE_TRAMO_MAX:
            if texto_linea.startswith("Tramo") or self.b_tramo:
                self.guardar_ce()
                self.flush_espacio()
                self.flush_unidad()
                self.b_tramo.append(texto_linea)
            self.bloqueo_tablas = False
            return

        if size < SIZE_TITLE_THRESHOLD:
            self.flush_espacio()
            self.flush_unidad()
            self.flush_tramo()

        # --- CONTROL ANTI-TABLAS ---
        if any(keyword in texto_lower for keyword in ["contenidos, criterios de logro", "contenidos específicos", "orientaciones"]):
            self.guardar_ce()
            self.bloqueo_tablas = True
            return

        if self.bloqueo_tablas: return

        # --- MÁQUINA DE COMPETENCIAS ---
        match_ce = PATRON_CE.match(texto_linea)
        es_negrita = "Bold" in span_last["font"] or span_last["flags"] & 2
        es_conciencia = "conciencia" in self.unidad_actual.lower() and "corporal" in self.unidad_actual.lower()
        
        if match_ce and (SIZE_CE_MIN <= size <= SIZE_CE_MAX):
            if texto_linea.count("CE") > 1: return 
                
            self.guardar_ce()
            self.ce_actual = match_ce.group(1).replace(" ", "").rstrip('.')
            resto = texto_linea[match_ce.end():].strip()
            self.en_desarrollo_viñetas = False
            
            if resto and resto != "," and not PATRON_CE.match(resto.replace(",", "").strip()):
                if es_conciencia:
                    if "•" in resto:
                        partes = resto.split("•", 1)
                        if partes[0].strip(): self.buffer_enunciado.append(partes[0].strip())
                        self.en_desarrollo_viñetas = True
                        self.buffer_desarrollo.append(partes[1].strip())
                    else:
                        self.buffer_enunciado.append(resto)
                else:
                    if es_negrita: self.buffer_enunciado.append(resto)
                    else: self.buffer_desarrollo.append(resto)
            return
        
        if self.ce_actual:
            if size > SIZE_CE_MAX:
                self.guardar_ce()
                return
                
            limpio = texto_linea.replace(",", "").strip()
            if not PATRON_CE.match(limpio): 
                if es_conciencia:
                    if "•" in texto_linea:
                        self.en_desarrollo_viñetas = True
                        self.buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                    elif self.en_desarrollo_viñetas:
                        self.buffer_desarrollo.append(texto_linea.replace("•", "").strip())
                    else:
                        self.buffer_enunciado.append(texto_linea)
                else:
                    if es_negrita: self.buffer_enunciado.append(texto_linea)
                    else: self.buffer_desarrollo.append(texto_linea)

    def close(self):
        if hasattr(self, 'db'):
            self.db.close()
