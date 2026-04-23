"""
tools.py — ADK tools for the curriculum extractor agent.
"""

import httpx
from google.adk.tools import ToolContext


def search_open_notebook(query: str, tool_context: ToolContext) -> dict:
    """Search the Open Notebook knowledge base for curriculum context.

    Use this tool when you need additional context about curriculum structure,
    competency descriptions, or domain-specific information.

    Args:
        query (str): The search query describing what information is needed.
        tool_context (ToolContext): ADK tool context (injected automatically).

    Returns:
        dict: Search results.
            On success: {'status': 'success', 'results': list[str], 'count': int}
            On error: {'status': 'error', 'error_type': str, 'error_message': str}
    """
    url = tool_context.state.get("app:open_notebook_url", "http://localhost:5055")
    notebook_id = tool_context.state.get(
        "app:open_notebook_notebook_id", "notebook:plf3f24qx6nui9zmn3vl"
    )
    model_id = tool_context.state.get(
        "app:open_notebook_model_id", "model:fi2x3hf9fvjdxl25ljwt"
    )

    try:
        response = httpx.post(
            f"{url}/api/query",
            json={"query": query, "notebook": notebook_id, "model": model_id},
            timeout=30.0,
        )
        response.raise_for_status()
        data = response.json()
        results = data.get("results", [data.get("answer", str(data))])
        if not isinstance(results, list):
            results = [str(results)]
        return {"status": "success", "results": results, "count": len(results)}
    except httpx.TimeoutException:
        return {
            "status": "error",
            "error_type": "timeout",
            "error_message": "Open Notebook request timed out",
        }
    except Exception as e:
        return {
            "status": "error",
            "error_type": "request_error",
            "error_message": str(e),
        }
