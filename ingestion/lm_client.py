"""
LLM Backend abstraction para el pipeline de extracción on-device.

Dev:  LMStudioClient  → LM Studio en localhost:1234 (OpenAI-compatible)
Prod: GeminiBackend   → Gemini API vía google-genai
"""
from __future__ import annotations

import json
import os
from typing import Protocol, runtime_checkable

from pydantic import BaseModel


class LMStudioUnavailableError(Exception):
    pass


@runtime_checkable
class LLMBackend(Protocol):
    def complete(self, prompt: str, response_model: type[BaseModel]) -> BaseModel: ...
    def health_check(self) -> bool: ...


# ── Dev: LM Studio ────────────────────────────────────────────────────────────

class LMStudioClient:
    """Cliente para LM Studio (OpenAI-compatible API en localhost:1234)."""

    def __init__(
        self,
        base_url: str = "http://localhost:1234/v1",
        model: str = "local-model",
    ):
        from openai import OpenAI
        self.model = model
        self._client = OpenAI(base_url=base_url, api_key="lm-studio")

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def complete(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        if not self.health_check():
            raise LMStudioUnavailableError(
                "LM Studio no disponible en localhost:1234. "
                "Asegurate de que esté corriendo con los modelos cargados."
            )
        response = self._client.chat.completions.create(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            response_format={
                "type": "json_schema",
                "json_schema": {
                    "name": response_model.__name__,
                    "schema": response_model.model_json_schema(),
                    "strict": True,
                },
            },
        )
        raw = response.choices[0].message.content or "{}"
        return response_model.model_validate_json(raw)


# ── Prod: Gemini ───────────────────────────────────────────────────────────────

class GeminiBackend:
    """Cliente para Gemini API (producción). Requiere GOOGLE_CLOUD_API_KEY."""

    MODEL = "gemini-3.1-pro-preview"

    def __init__(self, api_key: str | None = None):
        from google import genai
        from google.genai import types as genai_types
        self._genai = genai
        self._types = genai_types
        key = api_key or os.environ.get("GOOGLE_CLOUD_API_KEY")
        if not key:
            raise ValueError("GOOGLE_CLOUD_API_KEY no configurada para GeminiBackend")
        self._client = genai.Client(vertexai=True, api_key=key)

    def health_check(self) -> bool:
        try:
            self._client.models.list()
            return True
        except Exception:
            return False

    def complete(self, prompt: str, response_model: type[BaseModel]) -> BaseModel:
        response = self._client.models.generate_content(
            model=self.MODEL,
            contents=prompt,
            config=self._types.GenerateContentConfig(
                response_mime_type="application/json",
                temperature=0,
            ),
        )
        raw = response.text.strip()
        if raw.startswith("```"):
            raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
        return response_model.model_validate_json(raw)


def get_backend(env: str | None = None) -> LLMBackend:
    """Factory: retorna el backend correcto según APP_ENV."""
    resolved_env = env or os.getenv("APP_ENV", "dev").lower()
    if resolved_env == "dev":
        return LMStudioClient()
    return GeminiBackend()
