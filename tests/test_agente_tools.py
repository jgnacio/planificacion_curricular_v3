# Mockea httpx.AsyncClient — no pega a la API interna real.
# Convención: unittest.mock + asyncio.run manual (ver tests/test_auth.py); no pytest-asyncio.

import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

from teacher_agent.agent import consultar_curriculo_oficial


def _run(coro):
    return asyncio.run(coro)


def _tool_context(user_id: str = "user-1") -> SimpleNamespace:
    return SimpleNamespace(state={"user_id": user_id})


def _mock_response(status_code: int, payload: dict):
    # httpx.Response methods (json, raise_for_status) are sync — MagicMock, not AsyncMock.
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = payload
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    else:
        resp.raise_for_status.return_value = None
    return resp


def test_consultar_curriculo_oficial_success():
    payload = {
        "answer": "El programa sugiere trabajo por proyectos [pág. 42].",
        "sources": [
            {"title": "Compilación 1er Ciclo", "pageNumber": 42, "excerpt": "texto", "uri": "gs://bucket/1.pdf"}
        ],
    }
    with patch("teacher_agent.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(200, payload)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = _run(consultar_curriculo_oficial(_tool_context(), "¿cómo se trabaja por proyectos?"))

    assert result["status"] == "success"
    assert result["respuesta"]
    assert result["fuentes"][0]["pagina"] == 42

    called_url = mock_client.post.call_args.args[0]
    assert called_url.endswith("/internal/curriculo/search")
    called_headers = mock_client.post.call_args.kwargs["headers"]
    assert "X-Internal-Key" in called_headers


def test_consultar_curriculo_oficial_not_found():
    payload = {"answer": "No se encontraron resultados.", "sources": []}
    with patch("teacher_agent.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(200, payload)
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = _run(consultar_curriculo_oficial(_tool_context(), "pregunta sin relación"))

    assert result["status"] == "not_found"
    assert "fuentes" not in result


def test_consultar_curriculo_oficial_error_on_http_failure():
    with patch("teacher_agent.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client.post.return_value = _mock_response(500, {"detail": "internal error"})
        mock_client_cls.return_value.__aenter__.return_value = mock_client

        result = _run(consultar_curriculo_oficial(_tool_context(), "cualquier pregunta"))

    assert result["status"] == "error"
    assert result["error_message"]


def test_consultar_curriculo_oficial_error_on_exception():
    with patch("teacher_agent.agent.httpx.AsyncClient") as mock_client_cls:
        mock_client_cls.return_value.__aenter__.side_effect = RuntimeError("connection refused")

        result = _run(consultar_curriculo_oficial(_tool_context(), "cualquier pregunta"))

    assert result["status"] == "error"
    assert "connection refused" in result["error_message"]


def test_agent_prompt_has_no_unresolvable_state_placeholders():
    """ADK trata `{identificador}` en la instrucción como variable de session state.

    Un placeholder que el estado no provee revienta el turno entero con KeyError
    (`inject_session_state`), y el usuario sólo ve "El agente no respondió".
    """
    import re

    from teacher_agent.agent import AGENT_PROMPT

    # Misma regex que google/adk/utils/instructions_utils.py
    identifier = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\??$")
    offenders = [
        m.group()
        for m in re.finditer(r"{+[^{}]*}+", AGENT_PROMPT)
        if identifier.fullmatch(m.group().strip("{} "))
    ]

    assert offenders == [], (
        f"El prompt tiene placeholders que ADK intentará resolver contra el session "
        f"state: {offenders}. Reescribilos sin llaves."
    )
