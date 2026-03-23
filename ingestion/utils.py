import re

def normalizar_prefix(nombre: str) -> str:
    """
    Convierte un nombre de unidad a un prefijo normalizado para IDs de Neo4j.
    Elimina subtítulos entre paréntesis, colapsa espacios múltiples y caracteres
    especiales, garantizando que pass 1 y pass 2 generen el mismo prefix.
    """
    s = nombre.strip()
    s = re.sub(r'\(.*?\)', '', s)         # eliminar subtítulos entre paréntesis
    s = re.sub(r'\s+', ' ', s).strip()    # espacios múltiples → uno solo
    s = re.sub(r'[^\w\s]', '', s)         # eliminar puntos, guiones, etc.
    s = s.replace(' ', '_').upper()
    s = re.sub(r'_+', '_', s)             # underscores múltiples → uno solo
    return s.strip('_')

def truncar(texto, limite=45):
    """Truncates text to a limit and adds ellipsis if necessary."""
    return f"{texto[:limite]}..." if len(texto) > limite else texto

def obtener_padre_ce(codigo_ce):
    """Obtains the parent CE code from a child code."""
    if '.' in codigo_ce:
        return codigo_ce.rsplit('.', 1)[0]
    return None

def limpiar_texto(texto):
    """Cleans text by removing dashes and multiple spaces."""
    return re.sub(r'-\s+', '', texto).strip()
