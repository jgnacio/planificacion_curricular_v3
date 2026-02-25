import re

# Regex Patterns
PATRON_CE = re.compile(r"^(CE\s?\d+(?:\.\d+)*)\.?")
PATRON_MCN = re.compile(r'(?i)(.*?)(Contribuyen?\s+al\s+desarrollo\s+.*?MCN\s*:?\s*)(.*)')
PATRON_EJES = re.compile(r'(?i)(.*?)(Ejes\s+(?:temáticos|o\s+dominios\s+a\s+desarrollar)\s*:?\s*)(.*)')

# Font Size Thresholds
SIZE_ESPACIO_MIN = 37.0
SIZE_ESPACIO_MAX = 38.5
SIZE_UNIDAD_MIN = 31.0
SIZE_UNIDAD_MAX = 33.0
SIZE_TRAMO_MIN = 23.0
SIZE_TRAMO_MAX = 25.0
SIZE_CE_MIN = 10.0
SIZE_CE_MAX = 13.5
SIZE_TITLE_THRESHOLD = 23.0
