"""Eventos de analytics de conversión (trial/free/paywall).

Log JSON estructurado por ahora — sin proveedor externo. emit_event queda
como abstracción para poder enchufar Posthog/Amplitude más adelante sin
tocar los call sites.
"""
import logging

logger = logging.getLogger("events")


def emit_event(name: str, user_id: str, **props) -> None:
    logger.info(name, extra={"event": name, "user_id": user_id, **props})
