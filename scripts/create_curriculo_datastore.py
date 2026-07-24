"""Crea (idempotente) el data store + engine de Discovery Engine para el currículo
oficial EBI/ANEP.

Uso:
    uv run python scripts/create_curriculo_datastore.py

Requiere en el entorno:
    GOOGLE_CLOUD_PROJECT            (default: facilitador-docente)
    DISCOVERY_ENGINE_DATA_STORE_ID   id deseado del data store (ej: "curriculo-ebi-anep")
    DISCOVERY_ENGINE_ENGINE_ID       id deseado del engine (default: "{data_store_id}-engine")

Data store: unstructured search (SOLUTION_TYPE_SEARCH, CONTENT_REQUIRED), location
"global", parser digital (los PDFs tienen capa de texto — sin OCR). SIN chunking: las
extractive answers (que devuelven pageNumber) son incompatibles con el modo chunking.

Engine: tier ENTERPRISE + add-on LLM — requerido para extractive answers y para el
summary generado con citas.

Ambos recursos son idempotentes: si ya existen, el script no los recrea.
"""

import os
import sys

from google.api_core.exceptions import AlreadyExists, GoogleAPICallError, NotFound
from google.cloud import discoveryengine_v1 as discoveryengine

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "facilitador-docente")
LOCATION = "global"
DATA_STORE_ID = os.getenv("DISCOVERY_ENGINE_DATA_STORE_ID", "")
ENGINE_ID = os.getenv("DISCOVERY_ENGINE_ENGINE_ID", "") or f"{DATA_STORE_ID}-engine"
DISPLAY_NAME = "Curriculo EBI/ANEP"


def _create_data_store(parent: str) -> None:
    client = discoveryengine.DataStoreServiceClient()
    data_store_name = f"{parent}/dataStores/{DATA_STORE_ID}"
    try:
        existing = client.get_data_store(name=data_store_name)
        print(f"Data store ya existe: {existing.name}")
        return
    except NotFound:
        pass

    data_store = discoveryengine.DataStore(
        display_name=DISPLAY_NAME,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_types=[discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH],
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
        document_processing_config=discoveryengine.DocumentProcessingConfig(
            default_parsing_config=discoveryengine.DocumentProcessingConfig.ParsingConfig(
                digital_parsing_config=discoveryengine.DocumentProcessingConfig.ParsingConfig.DigitalParsingConfig(),
            ),
        ),
    )
    request = discoveryengine.CreateDataStoreRequest(
        parent=parent,
        data_store_id=DATA_STORE_ID,
        data_store=data_store,
        create_advanced_site_search=False,
    )
    try:
        print("Creando data store, esperando operación...")
        result = client.create_data_store(request=request).result()
        print(f"Data store creado: {result.name}")
    except AlreadyExists:
        print(f"Data store ya existe (AlreadyExists): {data_store_name}")


def _create_engine(parent: str) -> None:
    client = discoveryengine.EngineServiceClient()
    engine_name = f"{parent}/engines/{ENGINE_ID}"
    try:
        existing = client.get_engine(name=engine_name)
        print(f"Engine ya existe: {existing.name}")
        return
    except NotFound:
        pass

    engine = discoveryengine.Engine(
        display_name=f"{DISPLAY_NAME} Engine",
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=[DATA_STORE_ID],
        # ENTERPRISE + LLM: requerido para extractive answers y summary con citas.
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier=discoveryengine.SearchTier.SEARCH_TIER_ENTERPRISE,
            search_add_ons=[discoveryengine.SearchAddOn.SEARCH_ADD_ON_LLM],
        ),
    )
    request = discoveryengine.CreateEngineRequest(
        parent=parent, engine=engine, engine_id=ENGINE_ID
    )
    try:
        print("Creando engine (enterprise + LLM), esperando operación...")
        result = client.create_engine(request=request).result()
        print(f"Engine creado: {result.name}")
    except AlreadyExists:
        print(f"Engine ya existe (AlreadyExists): {engine_name}")


def main() -> None:
    if not DATA_STORE_ID:
        print("ERROR: definí DISCOVERY_ENGINE_DATA_STORE_ID en el entorno.", file=sys.stderr)
        sys.exit(1)

    parent = f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{LOCATION}/collections/default_collection"
    _create_data_store(parent)
    _create_engine(parent)
    print(f"\nEngine id para DISCOVERY_ENGINE_ENGINE_ID: {ENGINE_ID}")


if __name__ == "__main__":
    main()
