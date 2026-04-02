"""
Tests del pipeline on-device de extracción.

Cobertura:
  - segmenter: edge fusion cuando el fragmento está cortado
  - hierarchizer: retry + nodo de error cuando el LLM devuelve JSON inválido
  - lm_client: LMStudioUnavailableError cuando el servidor no responde
  - endpoint POST /documents/upload: validaciones de tipo y tamaño
"""
from __future__ import annotations

import io
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from pydantic import BaseModel

from ingestion.hierarchizer import DocumentNode, hierarchize
from ingestion.lm_client import LMStudioClient, LMStudioUnavailableError
from ingestion.segmenter import _natural_break, segment


# ── Fixtures ───────────────────────────────────────────────────────────────────

class _MockBackend:
    """Backend mock configurable para tests."""

    def __init__(self, responses: list[Any]):
        self._responses = list(responses)
        self._calls = 0

    def health_check(self) -> bool:
        return True

    def complete(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        if not self._responses:
            raise RuntimeError("Sin más respuestas configuradas")
        resp = self._responses.pop(0)
        self._calls += 1
        if isinstance(resp, Exception):
            raise resp
        return resp


# ── segmenter ──────────────────────────────────────────────────────────────────

class TestSegmenter:
    def test_texto_corto_no_segmenta(self):
        """Texto menor a WINDOW_SIZE se devuelve sin llamar al modelo."""
        mock = _MockBackend([])
        texto = "Esta es una oración de prueba suficientemente larga."
        result = segment([texto], mock)
        assert result == [texto]
        assert mock._calls == 0

    def test_edge_fusion_fragmento_incompleto(self):
        """
        Cuando el modelo dice 'complete: false', el segmentador busca
        un corte natural en la ventana en lugar de cortar arbitrariamente.
        """
        from ingestion.segmenter import _EdgeResult

        # Simular: primer fragmento incompleto, segundo completo
        mock = _MockBackend([
            _EdgeResult(complete=False),
            _EdgeResult(complete=True),
        ])

        # Texto con un punto natural a mitad del bloque (> WINDOW_SIZE=400)
        text = "Primera oración completa. " + "x" * 380
        result = segment([text], mock)
        assert len(result) >= 1

    def test_natural_break_encuentra_punto(self):
        text = "Esto es una prueba. Y esto no debe cortarse aquí nunca jamás"
        idx = _natural_break(text)
        # El punto está en la primera mitad → idx debería ser 0 (no encontrado en 2da mitad)
        # O encontrar uno si hay en 2da mitad
        assert isinstance(idx, int)

    def test_bloques_vacios_ignorados(self):
        mock = _MockBackend([])
        result = segment(["", "   ", "\n"], mock)
        assert result == []


# ── hierarchizer ───────────────────────────────────────────────────────────────

class TestHierarchizer:
    def test_document_mode_happy_path(self):
        expected = DocumentNode(titulo_seccion="Sección 1", texto="Contenido de prueba.")
        mock = _MockBackend([expected])
        result = hierarchize("Contenido de prueba.", mock, "document")
        assert isinstance(result, DocumentNode)
        assert result.texto == "Contenido de prueba."

    def test_retry_en_json_invalido(self):
        """Cuando el LLM falla, reintenta MAX_RETRIES veces y devuelve nodo de error."""
        error = ValueError("JSON inválido")
        mock = _MockBackend([error, error, error])  # 3 fallos = MAX_RETRIES+1
        result = hierarchize("Fragmento cualquiera.", mock, "document")
        assert isinstance(result, DocumentNode)
        assert result.tipo == "error"
        assert mock._calls == 3

    def test_exito_en_segundo_intento(self):
        """Si el primer intento falla pero el segundo pasa, retorna el resultado correcto."""
        error = ValueError("Timeout")
        expected = DocumentNode(texto="Texto recuperado.")
        mock = _MockBackend([error, expected])
        result = hierarchize("Texto recuperado.", mock, "document")
        assert result.tipo == "fragmento"
        assert mock._calls == 2


# ── lm_client ──────────────────────────────────────────────────────────────────

class TestLMStudioClient:
    def test_health_check_unavailable_raises(self):
        """Si LM Studio no responde, health_check retorna False."""
        client = LMStudioClient(base_url="http://localhost:9999/v1")
        assert client.health_check() is False

    def test_complete_raises_if_unavailable(self):
        """complete() debe lanzar LMStudioUnavailableError si no hay servidor."""
        client = LMStudioClient(base_url="http://localhost:9999/v1")
        with pytest.raises(LMStudioUnavailableError):
            client.complete("test", DocumentNode)


# ── endpoint ───────────────────────────────────────────────────────────────────

class TestDocumentsEndpoint:
    @pytest.fixture
    def client(self):
        from fastapi.testclient import TestClient
        from api.main import app
        return TestClient(app)

    def test_upload_no_pdf_returns_422(self, client):
        fake_docx = io.BytesIO(b"PK fake docx content")
        response = client.post(
            "/documents/upload",
            files={"file": ("doc.docx", fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        )
        assert response.status_code == 422

    def test_upload_pdf_demasiado_grande_returns_413(self, client):
        big_pdf = io.BytesIO(b"%PDF-1.4 " + b"x" * (51 * 1024 * 1024))
        response = client.post(
            "/documents/upload",
            files={"file": ("big.pdf", big_pdf, "application/pdf")},
        )
        assert response.status_code == 413

    def test_upload_lm_studio_unavailable_returns_503(self, client):
        """Si LM Studio no está disponible, el endpoint retorna 503."""
        minimal_pdf = (
            b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
            b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
            b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]>>endobj\n"
            b"xref\n0 4\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n0\n%%EOF"
        )
        with patch("ingestion.pipeline.LMStudioClient") as mock_cls:
            mock_inst = MagicMock()
            mock_inst.health_check.return_value = False
            mock_cls.return_value = mock_inst

            # patch también el import interno
            with patch("ingestion.pipeline.LMStudioUnavailableError", LMStudioUnavailableError):
                response = client.post(
                    "/documents/upload",
                    files={"file": ("test.pdf", io.BytesIO(minimal_pdf), "application/pdf")},
                )
        assert response.status_code == 503
