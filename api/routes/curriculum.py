import json
import os

from fastapi import APIRouter

router = APIRouter(tags=["curriculum"])

_curriculum_cache: dict | None = None


@router.get("/curriculum/estructura")
def get_curriculum_estructura():
    """Returns the full structured curriculum from the parsed JSON."""
    global _curriculum_cache
    if _curriculum_cache is None:
        json_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "data",
            "curriculum_structure.json",
        )
        with open(json_path, encoding="utf-8") as f:
            _curriculum_cache = json.load(f)
    return _curriculum_cache
