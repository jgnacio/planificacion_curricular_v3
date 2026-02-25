import re

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
