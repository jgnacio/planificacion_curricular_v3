"""Ingesta (idempotente) de los PDFs del currículo oficial EBI/ANEP al Discovery Engine
data store. Requiere que el data store ya exista (ver scripts/create_curriculo_datastore.py).

Uso:
    uv run python scripts/ingest_curriculo.py

Requiere en el entorno:
    GOOGLE_CLOUD_PROJECT             (default: facilitador-docente)
    GCS_BUCKET_NAME                  bucket existente reusado del resto del proyecto
    DISCOVERY_ENGINE_DATA_STORE_ID   id del data store creado previamente

Sube los 2 PDFs de pdfs/ al bucket (prefijo curriculo/) y dispara un
import_documents con reconciliation_mode=INCREMENTAL, que es seguro de
re-ejecutar: reemplaza documentos con el mismo id en vez de duplicarlos.
"""

import os
import sys
from pathlib import Path

from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import storage

GOOGLE_CLOUD_PROJECT = os.getenv("GOOGLE_CLOUD_PROJECT", "facilitador-docente")
LOCATION = "global"
DATA_STORE_ID = os.getenv("DISCOVERY_ENGINE_DATA_STORE_ID", "")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "")
GCS_PREFIX = "curriculo/"

PDFS_DIR = Path(__file__).resolve().parent.parent / "pdfs"


def _upload_pdfs() -> list[str]:
    client = storage.Client(project=GOOGLE_CLOUD_PROJECT)
    bucket = client.bucket(GCS_BUCKET_NAME)

    uris = []
    for pdf_path in sorted(PDFS_DIR.glob("*.pdf")):
        blob_name = f"{GCS_PREFIX}{pdf_path.name}"
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(pdf_path), content_type="application/pdf")
        uris.append(f"gs://{GCS_BUCKET_NAME}/{blob_name}")
        print(f"Subido: {pdf_path.name} -> {uris[-1]}")
    return uris


def _import_documents(gcs_uris: list[str]) -> None:
    client = discoveryengine.DocumentServiceClient()
    parent = (
        f"projects/{GOOGLE_CLOUD_PROJECT}/locations/{LOCATION}/collections/default_collection"
        f"/dataStores/{DATA_STORE_ID}/branches/default_branch"
    )
    request = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=discoveryengine.GcsSource(
            input_uris=gcs_uris,
            data_schema="content",
        ),
        # INCREMENTAL: re-ejecutar el script no duplica documentos, reconcilia por id.
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    operation = client.import_documents(request=request)
    print("Importando documentos, esperando operación...")
    result = operation.result()
    print(f"Importación completa: {result}")


def main() -> None:
    if not GCS_BUCKET_NAME:
        print("ERROR: definí GCS_BUCKET_NAME en el entorno.", file=sys.stderr)
        sys.exit(1)
    if not DATA_STORE_ID:
        print("ERROR: definí DISCOVERY_ENGINE_DATA_STORE_ID en el entorno.", file=sys.stderr)
        sys.exit(1)
    if not PDFS_DIR.exists() or not any(PDFS_DIR.glob("*.pdf")):
        print(f"ERROR: no se encontraron PDFs en {PDFS_DIR}", file=sys.stderr)
        sys.exit(1)

    gcs_uris = _upload_pdfs()
    _import_documents(gcs_uris)


if __name__ == "__main__":
    main()
